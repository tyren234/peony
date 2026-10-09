"""Demo data seeder for Waterdeep Watchtower (Requirements F11, T11)."""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from pathlib import Path
import httpx

# Ensure project root is in sys.path when script is executed directly
project_root_directory = str(Path(__file__).resolve().parent.parent)
if project_root_directory not in sys.path:
    sys.path.insert(0, project_root_directory)

try:
    from generator.cli import calculate_measurement_value, send_single_measurement
except ImportError:
    from cli import calculate_measurement_value, send_single_measurement


CANONICAL_WATERDEEP_SERIES: List[Dict[str, Any]] = [
    {
        "name": "Integralność Bariery Ahghairona",
        "minValue": 0.0,
        "maxValue": 100.0,
        "unit": "%",
        "color": "#2563eb",
        "icon": "shield",
        "sensor_name": "Czujnik Wieży Blackstaffa #1",
        "generation_mode": "sine",
        "typical_min": 75.0,
        "typical_max": 99.0,
    },
    {
        "name": "Poziom hałasu na Targowisku Głównym",
        "minValue": 30.0,
        "maxValue": 120.0,
        "unit": "dB",
        "color": "#d97706",
        "icon": "volume",
        "sensor_name": "Akustyk Dzielnicy Handlowej #1",
        "generation_mode": "random",
        "typical_min": 45.0,
        "typical_max": 95.0,
    },
    {
        "name": "Temperatura w piecach Świątyni Gonda",
        "minValue": 20.0,
        "maxValue": 1400.0,
        "unit": "°C",
        "color": "#dc2626",
        "icon": "flame",
        "sensor_name": "Pirometr Kuźni Cudów #1",
        "generation_mode": "sine",
        "typical_min": 850.0,
        "typical_max": 1280.0,
    },
    {
        "name": "Niewyjaśnione zdarzenia magiczne",
        "minValue": 0.0,
        "maxValue": 50.0,
        "unit": "anomalii/h",
        "color": "#8a2be2",
        "icon": "sparkles",
        "sensor_name": "Wykrywacz Splotu Doki #1",
        "generation_mode": "random",
        "typical_min": 2.0,
        "typical_max": 24.0,
    },
    {
        "name": "Goście w The Yawning Portal",
        "minValue": 5.0,
        "maxValue": 250.0,
        "unit": "osób",
        "color": "#059669",
        "icon": "users",
        "sensor_name": "Licznik Tawerny Durnana #1",
        "generation_mode": "sine",
        "typical_min": 35.0,
        "typical_max": 210.0,
    },
    {
        "name": "Otwarte bramy miejskie",
        "minValue": 0.0,
        "maxValue": 8.0,
        "unit": "bram",
        "color": "#0284c7",
        "icon": "door-open",
        "sensor_name": "Monitor Wrót Straży Miejskiej #1",
        "generation_mode": "constant",
        "typical_min": 6.0,
        "typical_max": 8.0,
    },
]


def authenticate_administrator(
    http_client: httpx.Client,
    api_base_url: str,
    admin_username: str,
    admin_password: str,
) -> str:
    """Log in as administrator and return Bearer access token."""
    login_endpoint_url = f"{api_base_url.rstrip('/')}/api/auth/login"
    login_response = http_client.post(
        login_endpoint_url,
        json={"username": admin_username, "password": admin_password},
    )
    if login_response.status_code != 200:
        raise RuntimeError(
            f"Błąd logowania administratora ({login_response.status_code}): {login_response.text}"
        )
    access_token_value = login_response.json().get("accessToken", "")
    if not access_token_value:
        raise RuntimeError("Brak pola accessToken w odpowiedzi serwera logowania.")
    return access_token_value


def get_or_create_series(
    http_client: httpx.Client,
    api_base_url: str,
    bearer_token: str,
    series_definition: Dict[str, Any],
) -> int:
    """Find existing series by name or create a new one, returning series identifier."""
    series_endpoint_url = f"{api_base_url.rstrip('/')}/api/series"
    get_series_response = http_client.get(series_endpoint_url)
    if get_series_response.status_code == 200:
        existing_series_list = get_series_response.json()
        for candidate_series in existing_series_list:
            if candidate_series.get("name") == series_definition["name"]:
                return candidate_series["id"]

    series_creation_payload = {
        "name": series_definition["name"],
        "minValue": series_definition["minValue"],
        "maxValue": series_definition["maxValue"],
        "color": series_definition["color"],
        "icon": series_definition.get("icon"),
        "unit": series_definition.get("unit"),
    }
    create_series_response = http_client.post(
        series_endpoint_url,
        json=series_creation_payload,
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    if create_series_response.status_code != 201:
        raise RuntimeError(
            f"Nie udało się utworzyć serii '{series_definition['name']}': "
            f"Kod {create_series_response.status_code}, Treść: {create_series_response.text}"
        )
    created_series_id = create_series_response.json()["id"]
    return created_series_id


def register_sensor_for_series(
    http_client: httpx.Client,
    api_base_url: str,
    bearer_token: str,
    sensor_name: str,
    series_id: int,
) -> Tuple[int, str]:
    """Register a new sensor for given series, returning (sensor_id, api_key)."""
    sensors_endpoint_url = f"{api_base_url.rstrip('/')}/api/sensors"
    registration_payload = {
        "name": sensor_name,
        "seriesId": series_id,
    }
    registration_response = http_client.post(
        sensors_endpoint_url,
        json=registration_payload,
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    if registration_response.status_code != 201:
        raise RuntimeError(
            f"Nie udało się zarejestrować czujnika '{sensor_name}': "
            f"Kod {registration_response.status_code}, Treść: {registration_response.text}"
        )
    registration_data = registration_response.json()
    return registration_data["id"], registration_data["apiKey"]


def seed_series_measurements(
    http_client: httpx.Client,
    api_base_url: str,
    sensor_api_key: str,
    series_definition: Dict[str, Any],
    measurements_count: int = 20,
    interval_minutes: float = 15.0,
) -> int:
    """Send batch of historical measurements for single series via POST /api/measurements."""
    now_utc_moment = datetime.now(timezone.utc)
    total_minutes_span = (measurements_count - 1) * interval_minutes
    start_timestamp = now_utc_moment - timedelta(minutes=total_minutes_span)

    successful_count = 0
    for measurement_step_index in range(measurements_count):
        measurement_timestamp = start_timestamp + timedelta(
            minutes=measurement_step_index * interval_minutes
        )
        calculated_value = calculate_measurement_value(
            generation_mode=series_definition["generation_mode"],
            step_index=measurement_step_index,
            total_steps=measurements_count,
            minimum_value=series_definition["typical_min"],
            maximum_value=series_definition["typical_max"],
            constant_value=series_definition["typical_max"],
        )
        is_success, status_code, response_info = send_single_measurement(
            api_base_url=api_base_url,
            sensor_api_key=sensor_api_key,
            measurement_value=calculated_value,
            measurement_timestamp=measurement_timestamp,
            http_client=http_client,
        )
        if is_success:
            successful_count += 1
        else:
            print(
                f"   ⚠️ Odrzucono pomiar {measurement_step_index + 1}: "
                f"Kod {status_code}, {response_info}"
            )
    return successful_count


def seed_waterdeep_demo_data(
    api_base_url: str = "http://127.0.0.1:8000",
    admin_username: str = "admin",
    admin_password: str = "HasloAdministratora123!",
    measurements_per_series: int = 20,
    http_client: Optional[httpx.Client] = None,
) -> Dict[str, Any]:
    """Execute complete Waterdeep demo data seeding via HTTP API exclusively."""
    clean_base_url = api_base_url.rstrip("/")
    internal_client = http_client if http_client is not None else httpx.Client(timeout=15.0)
    should_close_client = http_client is None

    print("=" * 75)
    print("🏰 Waterdeep Watchtower – Zasilenie Bazy Danymi Przykładowymi (F11)")
    print(f"📡 Adres API:        {clean_base_url}")
    print(f"👤 Administrator:    {admin_username}")
    print(f"📈 Liczba pomiarów:  {measurements_per_series} na serię")
    print("=" * 75)

    try:
        print("🔐 Logowanie administratora...")
        bearer_token = authenticate_administrator(
            http_client=internal_client,
            api_base_url=clean_base_url,
            admin_username=admin_username,
            admin_password=admin_password,
        )
        print("✅ Zalogowano pomyślnie. Pobrano Bearer token.")

        seeding_summary: List[Dict[str, Any]] = []
        total_seeded_measurements = 0

        for series_index, series_definition in enumerate(CANONICAL_WATERDEEP_SERIES, start=1):
            series_name = series_definition["name"]
            print(f"\n[{series_index}/{len(CANONICAL_WATERDEEP_SERIES)}] Przetwarzanie: {series_name}")

            series_id = get_or_create_series(
                http_client=internal_client,
                api_base_url=clean_base_url,
                bearer_token=bearer_token,
                series_definition=series_definition,
            )
            print(f"   📊 Identyfikator serii: {series_id}")

            sensor_name = series_definition["sensor_name"]
            sensor_id, sensor_api_key = register_sensor_for_series(
                http_client=internal_client,
                api_base_url=clean_base_url,
                bearer_token=bearer_token,
                sensor_name=sensor_name,
                series_id=series_id,
            )
            masked_key = f"{sensor_api_key[:6]}...{sensor_api_key[-4:]}"
            print(f"   📡 Zarejestrowano czujnik: {sensor_name} (ID: {sensor_id}, Klucz: {masked_key})")

            print(f"   🚀 Wysyłanie {measurements_per_series} historycznych pomiarów przez API...")
            successful_measurements = seed_series_measurements(
                http_client=internal_client,
                api_base_url=clean_base_url,
                sensor_api_key=sensor_api_key,
                series_definition=series_definition,
                measurements_count=measurements_per_series,
            )
            total_seeded_measurements += successful_measurements
            print(f"   ✅ Zapisano pomyślnie {successful_measurements}/{measurements_per_series} pomiarów.")

            seeding_summary.append(
                {
                    "series_id": series_id,
                    "series_name": series_name,
                    "sensor_id": sensor_id,
                    "measurements_count": successful_measurements,
                }
            )

        print("\n" + "=" * 75)
        print("🎉 Zakończono zasilanie danymi przykładowymi!")
        print(f"📊 Utworzonych/zasilonych serii: {len(seeding_summary)}")
        print(f"📈 Łącznie wysłanych pomiarów:   {total_seeded_measurements}")
        print("=" * 75)

        return {
            "status": "success",
            "series_count": len(seeding_summary),
            "total_measurements": total_seeded_measurements,
            "details": seeding_summary,
        }
    finally:
        if should_close_client:
            internal_client.close()


def main() -> None:
    """Command-line entry point supporting both positional and named arguments."""
    argument_parser = argparse.ArgumentParser(
        description="Skrypt zasilania danymi przykładowymi Waterdeep Watchtower (Wymóg F11)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Obsługa zarówno argumentów pozycyjnych (z README.md) jak i opcjonalnych flag
    argument_parser.add_argument(
        "positional_api_url",
        nargs="?",
        default=None,
        help="Adres bazowy API (opcjonalny argument pozycyjny)",
    )
    argument_parser.add_argument(
        "positional_username",
        nargs="?",
        default=None,
        help="Login administratora (opcjonalny argument pozycyjny)",
    )
    argument_parser.add_argument(
        "positional_password",
        nargs="?",
        default=None,
        help="Hasło administratora (opcjonalny argument pozycyjny)",
    )
    argument_parser.add_argument(
        "--api",
        dest="flag_api_url",
        default=os.environ.get("API_URL", "http://127.0.0.1:8000"),
        help="Adres bazowy API",
    )
    argument_parser.add_argument(
        "--user",
        dest="flag_username",
        default="admin",
        help="Login administratora",
    )
    argument_parser.add_argument(
        "--pass",
        dest="flag_password",
        default="HasloAdministratora123!",
        help="Hasło administratora",
    )
    argument_parser.add_argument(
        "--count",
        dest="measurements_count",
        type=int,
        default=20,
        help="Liczba pomiarów per seria",
    )

    parsed_arguments = argument_parser.parse_args()

    effective_api_url = parsed_arguments.positional_api_url or parsed_arguments.flag_api_url
    effective_username = parsed_arguments.positional_username or parsed_arguments.flag_username
    effective_password = parsed_arguments.positional_password or parsed_arguments.flag_password

    try:
        seed_waterdeep_demo_data(
            api_base_url=effective_api_url,
            admin_username=effective_username,
            admin_password=effective_password,
            measurements_per_series=parsed_arguments.measurements_count,
        )
    except Exception as execution_error:
        print(f"\n❌ Błąd podczas zasilania danymi: {execution_error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
