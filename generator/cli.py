"""CLI telemetry emulator for IoT sensors in Waterdeep Watchtower (Requirements F13, F4, T11)."""

import argparse
import math
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import httpx


def calculate_measurement_value(
    generation_mode: str,
    step_index: int,
    total_steps: int,
    minimum_value: float,
    maximum_value: float,
    constant_value: float = 50.0,
) -> float:
    """Calculate measurement value according to selected generation mode."""
    if generation_mode == "sine":
        midpoint_value = (minimum_value + maximum_value) / 2.0
        amplitude_value = (maximum_value - minimum_value) / 2.0
        wave_frequency_divisor = max(1.0, float(total_steps if total_steps > 0 else 20))
        angle_radians = 2.0 * math.pi * (float(step_index) / wave_frequency_divisor)
        calculated_value = midpoint_value + (amplitude_value * math.sin(angle_radians))
        return round(calculated_value, 2)

    if generation_mode == "random":
        random_value = random.uniform(minimum_value, maximum_value)
        return round(random_value, 2)

    if generation_mode == "linear":
        progress_ratio = float(step_index) / float(max(1, total_steps - 1))
        linear_value = minimum_value + ((maximum_value - minimum_value) * progress_ratio)
        return round(linear_value, 2)

    if generation_mode == "constant":
        return round(constant_value, 2)

    if generation_mode == "out-of-range":
        # Celowe wykroczenie poza zakres dla demonstracji wymogu F4
        out_of_range_value = maximum_value + 15.0
        return round(out_of_range_value, 2)

    raise ValueError(f"Unsupported generation mode: {generation_mode}")


def send_single_measurement(
    api_base_url: str,
    sensor_api_key: str,
    measurement_value: float,
    measurement_timestamp: Optional[datetime] = None,
    http_client: Optional[httpx.Client] = None,
) -> Tuple[bool, int, Dict[str, Any]]:
    """Send a single telemetry measurement to the API via POST /api/measurements.
    
    Returns (success_flag, status_code, response_json_or_error_dict).
    """
    clean_base_url = api_base_url.rstrip("/")
    endpoint_url = f"{clean_base_url}/api/measurements"
    request_headers = {
        "X-API-Key": sensor_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    request_payload: Dict[str, Any] = {"value": measurement_value}
    if measurement_timestamp is not None:
        if measurement_timestamp.tzinfo is None:
            measurement_timestamp = measurement_timestamp.replace(tzinfo=timezone.utc)
        request_payload["timestamp"] = measurement_timestamp.isoformat()

    internal_client = http_client if http_client is not None else httpx.Client(timeout=10.0)
    should_close_client = http_client is None

    try:
        http_response = internal_client.post(
            endpoint_url,
            json=request_payload,
            headers=request_headers,
        )
        response_status_code = http_response.status_code
        try:
            response_json_content = http_response.json()
        except Exception:
            response_json_content = {"raw_text": http_response.text}

        is_success = response_status_code == 201
        return is_success, response_status_code, response_json_content
    except Exception as connection_exception:
        return False, 0, {"error": str(connection_exception)}
    finally:
        if should_close_client:
            internal_client.close()


def run_generator(
    api_base_url: str,
    sensor_api_key: str,
    generation_mode: str = "sine",
    minimum_value: float = 0.0,
    maximum_value: float = 100.0,
    constant_value: float = 50.0,
    measurement_count: Optional[int] = 20,
    live_interval_seconds: float = 2.0,
    is_history_mode: bool = False,
    history_step_minutes: float = 15.0,
    initial_timestamp: Optional[datetime] = None,
    http_client: Optional[httpx.Client] = None,
) -> int:
    """Execute generator loop sending measurements either in historical batch or live cadence."""
    print("=" * 70)
    print("🏰 Waterdeep Watchtower – Emulator Czujnika Telemetrycznego (F13)")
    print(f"📡 Adres API:        {api_base_url}")
    masked_key = f"{sensor_api_key[:6]}...{sensor_api_key[-4:]}" if len(sensor_api_key) > 10 else "***"
    print(f"🔑 Klucz sensora:    {masked_key}")
    print(f"⚙️  Tryb generowania: {generation_mode} (zakres: [{minimum_value}, {maximum_value}])")
    print(f"⏱️  Tryb pracy:       {'Historyczny (wstecz)' if is_history_mode else 'Na żywo (interwał)'}")
    print("=" * 70)

    total_measurements_target = measurement_count if measurement_count and measurement_count > 0 else 0
    successful_measurements_count = 0
    rejected_measurements_count = 0

    now_utc_moment = datetime.now(timezone.utc)
    if initial_timestamp is not None:
        reference_start_timestamp = initial_timestamp
    elif is_history_mode:
        total_minutes_offset = (total_measurements_target - 1) * history_step_minutes
        reference_start_timestamp = now_utc_moment - timedelta(minutes=total_minutes_offset)
    else:
        reference_start_timestamp = now_utc_moment

    current_step_index = 0
    while True:
        if total_measurements_target > 0 and current_step_index >= total_measurements_target:
            break

        calculated_value = calculate_measurement_value(
            generation_mode=generation_mode,
            step_index=current_step_index,
            total_steps=total_measurements_target if total_measurements_target > 0 else 20,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            constant_value=constant_value,
        )

        if is_history_mode:
            current_measurement_time = reference_start_timestamp + timedelta(
                minutes=current_step_index * history_step_minutes
            )
        else:
            current_measurement_time = datetime.now(timezone.utc)

        is_success, status_code, response_data = send_single_measurement(
            api_base_url=api_base_url,
            sensor_api_key=sensor_api_key,
            measurement_value=calculated_value,
            measurement_timestamp=current_measurement_time,
            http_client=http_client,
        )

        iso_timestamp_display = current_measurement_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        if is_success:
            successful_measurements_count += 1
            measurement_resource_id = response_data.get("id", "brak")
            print(
                f"[{current_step_index + 1}] ✅ [201 Created] Wartość: {calculated_value:8.2f} | "
                f"Czas: {iso_timestamp_display} | ID: {measurement_resource_id}"
            )
        else:
            rejected_measurements_count += 1
            # Obsługa wymogu F4: czytelny komunikat o odrzuceniu wartości przez serwer
            error_detail = response_data.get("detail", response_data.get("title", response_data.get("error", "Nieznany błąd")))
            print(
                f"[{current_step_index + 1}] ❌ [ODRZUCONO PRZEZ SERWER - Kod {status_code}] "
                f"Wartość: {calculated_value:8.2f} | Szczegóły: {error_detail}"
            )

        current_step_index += 1

        if not is_history_mode and (total_measurements_target == 0 or current_step_index < total_measurements_target):
            try:
                time.sleep(live_interval_seconds)
            except KeyboardInterrupt:
                print("\n⏹️ Zatrzymano emulator na żywo sygnałem przerwania.")
                break

    print("-" * 70)
    print(
        f"📊 Podsumowanie: Wysłano poprawnie: {successful_measurements_count}, "
        f"Odrzucono: {rejected_measurements_count}, Łącznie: {current_step_index}"
    )
    print("-" * 70)
    return successful_measurements_count


def create_cli_argument_parser() -> argparse.ArgumentParser:
    """Create and configure command-line argument parser."""
    argument_parser = argparse.ArgumentParser(
        description="Emulator czujników IoT dla systemu Waterdeep Watchtower (Wymogi F13, F4, T11)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    argument_parser.add_argument(
        "--api",
        dest="api_url",
        default=os.environ.get("API_URL", "http://127.0.0.1:8000"),
        help="Bazowy adres URL interfejsu API",
    )
    argument_parser.add_argument(
        "--key",
        dest="api_key",
        default=os.environ.get("SENSOR_API_KEY", ""),
        help="Klucz API czujnika (nagłówek X-API-Key)",
    )
    argument_parser.add_argument(
        "--mode",
        dest="generation_mode",
        choices=["sine", "random", "linear", "constant", "out-of-range"],
        default="sine",
        help="Sposób generowania wartości pomiarów",
    )
    argument_parser.add_argument(
        "--min-value",
        dest="minimum_value",
        type=float,
        default=0.0,
        help="Minimalna wartość zakresu generowania",
    )
    argument_parser.add_argument(
        "--max-value",
        dest="maximum_value",
        type=float,
        default=100.0,
        help="Maksymalna wartość zakresu generowania",
    )
    argument_parser.add_argument(
        "--constant-value",
        dest="constant_value",
        type=float,
        default=50.0,
        help="Stała wartość dla trybu 'constant'",
    )
    argument_parser.add_argument(
        "--count",
        dest="measurement_count",
        type=int,
        default=20,
        help="Liczba pomiarów do wygenerowania (0 dla pętli nieskończonej)",
    )
    argument_parser.add_argument(
        "--interval",
        dest="interval_seconds",
        type=float,
        default=2.0,
        help="Odstęp czasu między pomiarami na żywo (w sekundach)",
    )
    argument_parser.add_argument(
        "--history",
        dest="is_history_mode",
        action="store_true",
        help="Wysyłanie pomiarów ze znacznikami czasu z przeszłości",
    )
    argument_parser.add_argument(
        "--step-minutes",
        dest="history_step_minutes",
        type=float,
        default=15.0,
        help="Krok czasowy w minutach między pomiarami historycznymi",
    )
    return argument_parser


def main() -> None:
    """Entry point for sensor emulator CLI."""
    argument_parser = create_cli_argument_parser()
    parsed_arguments = argument_parser.parse_args()

    sensor_api_key = parsed_arguments.api_key.strip()
    if not sensor_api_key:
        print("❌ Błąd: Nie podano klucza API czujnika. Podaj parametr --key lub zmienną SENSOR_API_KEY.", file=sys.stderr)
        sys.exit(1)

    run_generator(
        api_base_url=parsed_arguments.api_url,
        sensor_api_key=sensor_api_key,
        generation_mode=parsed_arguments.generation_mode,
        minimum_value=parsed_arguments.minimum_value,
        maximum_value=parsed_arguments.maximum_value,
        constant_value=parsed_arguments.constant_value,
        measurement_count=parsed_arguments.measurement_count,
        live_interval_seconds=parsed_arguments.interval_seconds,
        is_history_mode=parsed_arguments.is_history_mode,
        history_step_minutes=parsed_arguments.history_step_minutes,
    )


if __name__ == "__main__":
    main()
