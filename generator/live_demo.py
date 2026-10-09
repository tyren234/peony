"""Interactive live sensor emulator for live demonstration and testing."""

import argparse
import os
import sys
from typing import Any, Dict
import httpx

project_root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root_directory not in sys.path:
    sys.path.insert(0, project_root_directory)

from generator.cli import run_generator


def run_live_demonstration_emulator(
    api_base_url: str = "http://127.0.0.1:8000",
    admin_username: str = "admin",
    admin_password: str = "HasloAdministratora123!",
    interval_seconds: float = 30.0,
    generation_mode: str = "sine",
    measurement_count: int = 0,
) -> None:
    """Register temporary demonstration sensor and start streaming live telemetry."""
    print("=" * 70)
    print("🏰 Waterdeep Watchtower – Live Emulator Demonstracyjny")
    print(f"📡 Adres API:        {api_base_url}")
    print("=" * 70)

    clean_base_url = api_base_url.rstrip("/")

    # 1. Weryfikacja dostępności serwera
    try:
        health_response = httpx.get(f"{clean_base_url}/api/health", timeout=5.0)
        if health_response.status_code != 200:
            print("❌ Serwer API odpowiedział kodem innym niż 200.", file=sys.stderr)
            sys.exit(1)
    except Exception as connection_error:
        print(f"❌ Serwer API jest niedostępny ({connection_error}).", file=sys.stderr)
        print("💡 Wskazówka: Najpierw uruchom './run.sh' w osobnym terminalu.", file=sys.stderr)
        sys.exit(1)

    # 2. Logowanie administratora w celu rejestracji sensora
    print("🔐 Uwierzytelnianie kontem administratora...")
    login_response = httpx.post(
        f"{clean_base_url}/api/auth/login",
        json={"username": admin_username, "password": admin_password},
        timeout=10.0,
    )
    if login_response.status_code != 200:
        print("❌ Nie udało się zalogować administratora.", file=sys.stderr)
        sys.exit(1)

    bearer_token = login_response.json().get("accessToken")

    # 3. Pobranie dostępnych serii
    series_response = httpx.get(f"{clean_base_url}/api/series", timeout=10.0)
    series_list = series_response.json()
    if not series_list:
        print("❌ Brak serii pomiarowych w systemie. Uruchom './run.sh --seed'.", file=sys.stderr)
        sys.exit(1)

    chosen_series: Dict[str, Any] = series_list[0]
    for candidate_series in series_list:
        if "Bariery" in candidate_series.get("name", ""):
            chosen_series = candidate_series
            break

    series_identifier = chosen_series["id"]
    series_name = chosen_series["name"]
    minimum_value = float(chosen_series.get("minValue", 0.0))
    maximum_value = float(chosen_series.get("maxValue", 100.0))

    # 4. Rejestracja czujnika demonstracyjnego
    print(f"📡 Rejestracja czujnika na żywo dla serii: '{series_name}' (ID: {series_identifier})...")
    sensor_registration_response = httpx.post(
        f"{clean_base_url}/api/sensors",
        headers={"Authorization": f"Bearer {bearer_token}"},
        json={"name": "Czujnik Straży Miejskiej #Live", "seriesId": series_identifier},
        timeout=10.0,
    )
    if sensor_registration_response.status_code != 201:
        print("❌ Nie udało się zarejestrować czujnika.", file=sys.stderr)
        sys.exit(1)

    sensor_data = sensor_registration_response.json()
    sensor_api_key = sensor_data["apiKey"]
    sensor_identifier = sensor_data["id"]
    print(f"🔑 Pomyślnie zarejestrowano czujnik (ID: {sensor_identifier})!")
    print(f"🚀 Rozpoczynanie wysyłania pomiarów co {interval_seconds}s...")
    print("🛑 Aby zatrzymać emulator, naciśnij Ctrl + C.\n")

    # 5. Uruchomienie pętli generatora (0 = ciągłe wysyłanie)
    run_generator(
        api_base_url=clean_base_url,
        sensor_api_key=sensor_api_key,
        generation_mode=generation_mode,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        measurement_count=measurement_count,
        live_interval_seconds=interval_seconds,
        is_history_mode=False,
    )


def main() -> None:
    """Parse arguments and start live generator."""
    argument_parser = argparse.ArgumentParser(description="Live IoT telemetry emulator")
    argument_parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000", help="API URL")
    argument_parser.add_argument("--count", type=int, default=0, help="Number of measurements (0 for infinite)")
    argument_parser.add_argument("--interval", type=float, default=30.0, help="Interval in seconds")
    argument_parser.add_argument("--mode", default="sine", choices=["sine", "random", "linear"], help="Generation pattern")
    parsed_arguments = argument_parser.parse_args()

    run_live_demonstration_emulator(
        api_base_url=parsed_arguments.url,
        interval_seconds=parsed_arguments.interval,
        generation_mode=parsed_arguments.mode,
        measurement_count=parsed_arguments.count,
    )


if __name__ == "__main__":
    main()
