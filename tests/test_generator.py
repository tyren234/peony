"""Comprehensive tests for telemetry sensor emulator and Waterdeep demo data seeder (Requirements F13, F4, F11, T11)."""

import math
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from generator.cli import (
    calculate_measurement_value,
    create_cli_argument_parser,
    run_generator,
    send_single_measurement,
)
from generator.seed_waterdeep import (
    CANONICAL_WATERDEEP_SERIES,
    authenticate_administrator,
    get_or_create_series,
    register_sensor_for_series,
    seed_waterdeep_demo_data,
)


@pytest.mark.parametrize(
    "generation_mode,expected_check",
    [
        ("sine", lambda calculated_value: 0.0 <= calculated_value <= 100.0),
        ("random", lambda calculated_value: 10.0 <= calculated_value <= 50.0),
        ("linear", lambda calculated_value: 0.0 <= calculated_value <= 100.0),
        ("constant", lambda calculated_value: calculated_value == 77.0),
        ("out-of-range", lambda calculated_value: calculated_value > 100.0),
    ],
)
def test_calculate_measurement_value_modes(generation_mode: str, expected_check):
    """Verify measurement value calculation across all supported modes."""
    calculated_value = calculate_measurement_value(
        generation_mode=generation_mode,
        step_index=5,
        total_steps=20,
        minimum_value=0.0 if generation_mode != "random" else 10.0,
        maximum_value=100.0 if generation_mode != "random" else 50.0,
        constant_value=77.0,
    )
    assert expected_check(calculated_value)


def test_calculate_measurement_value_linear_progression():
    """Verify linear mode starts at minimum value and terminates at maximum value."""
    minimum_bound = 20.0
    maximum_bound = 80.0
    total_step_count = 5

    first_step_value = calculate_measurement_value(
        generation_mode="linear",
        step_index=0,
        total_steps=total_step_count,
        minimum_value=minimum_bound,
        maximum_value=maximum_bound,
    )
    last_step_value = calculate_measurement_value(
        generation_mode="linear",
        step_index=total_step_count - 1,
        total_steps=total_step_count,
        minimum_value=minimum_bound,
        maximum_value=maximum_bound,
    )
    assert first_step_value == minimum_bound
    assert last_step_value == maximum_bound


def test_calculate_measurement_value_sine_wave_shape():
    """Verify sine wave completes a full period across total steps."""
    minimum_bound = 0.0
    maximum_bound = 100.0
    total_step_count = 20

    quarter_step_value = calculate_measurement_value(
        generation_mode="sine",
        step_index=5,
        total_steps=total_step_count,
        minimum_value=minimum_bound,
        maximum_value=maximum_bound,
    )
    half_step_value = calculate_measurement_value(
        generation_mode="sine",
        step_index=10,
        total_steps=total_step_count,
        minimum_value=minimum_bound,
        maximum_value=maximum_bound,
    )
    three_quarter_step_value = calculate_measurement_value(
        generation_mode="sine",
        step_index=15,
        total_steps=total_step_count,
        minimum_value=minimum_bound,
        maximum_value=maximum_bound,
    )

    # 1/4 okresu -> szczyt (100.0), 1/2 okresu -> środek (50.0), 3/4 okresu -> dołek (0.0)
    assert quarter_step_value == 100.0
    assert half_step_value == 50.0
    assert three_quarter_step_value == 0.0


def test_calculate_measurement_value_unsupported_mode():
    """Verify invalid mode triggers ValueError."""
    with pytest.raises(ValueError, match="Unsupported generation mode"):
        calculate_measurement_value(
            generation_mode="invalid_mode",
            step_index=0,
            total_steps=10,
            minimum_value=0.0,
            maximum_value=100.0,
        )


def test_cli_argument_parser_defaults():
    """Verify CLI parser configured default options."""
    argument_parser = create_cli_argument_parser()
    parsed_arguments = argument_parser.parse_args([])

    assert parsed_arguments.api_url == "http://127.0.0.1:8000"
    assert parsed_arguments.generation_mode == "sine"
    assert parsed_arguments.measurement_count == 20
    assert parsed_arguments.minimum_value == 0.0
    assert parsed_arguments.maximum_value == 100.0
    assert parsed_arguments.interval_seconds == 2.0
    assert parsed_arguments.is_history_mode is False
    assert parsed_arguments.history_step_minutes == 15.0


def test_cli_argument_parser_custom_values():
    """Verify CLI parser parses provided custom arguments."""
    argument_parser = create_cli_argument_parser()
    command_line_tokens = [
        "--api", "https://waterdeep.example.com",
        "--key", "secret_sensor_api_key_1234567890",
        "--mode", "linear",
        "--min-value", "10.5",
        "--max-value", "99.5",
        "--count", "50",
        "--interval", "0.5",
        "--history",
        "--step-minutes", "30.0",
    ]
    parsed_arguments = argument_parser.parse_args(command_line_tokens)

    assert parsed_arguments.api_url == "https://waterdeep.example.com"
    assert parsed_arguments.api_key == "secret_sensor_api_key_1234567890"
    assert parsed_arguments.generation_mode == "linear"
    assert parsed_arguments.minimum_value == 10.5
    assert parsed_arguments.maximum_value == 99.5
    assert parsed_arguments.measurement_count == 50
    assert parsed_arguments.interval_seconds == 0.5
    assert parsed_arguments.is_history_mode is True
    assert parsed_arguments.history_step_minutes == 30.0


def setup_test_series_and_sensor(test_client: TestClient):
    """Helper to register a sample series and sensor for generator tests."""
    login_response = test_client.post(
        "/api/auth/login",
        json={
            "username": settings.default_user_username,
            "password": settings.default_user_password,
        },
    )
    bearer_token = login_response.json()["accessToken"]

    series_response = test_client.post(
        "/api/series",
        json={
            "name": "Generator Testowa Seria",
            "minValue": 10.0,
            "maxValue": 50.0,
            "color": "#123456",
        },
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    series_id = series_response.json()["id"]

    sensor_response = test_client.post(
        "/api/sensors",
        json={
            "name": "Generator Testowy Czujnik",
            "seriesId": series_id,
        },
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    sensor_id = sensor_response.json()["id"]
    sensor_api_key = sensor_response.json()["apiKey"]
    return series_id, sensor_id, sensor_api_key


def test_send_single_measurement_success(client: TestClient):
    """Verify send_single_measurement sends measurement and receives 201 Created."""
    unused_series_id, unused_sensor_id, sensor_api_key = setup_test_series_and_sensor(client)

    is_success, status_code, response_data = send_single_measurement(
        api_base_url="http://testserver",
        sensor_api_key=sensor_api_key,
        measurement_value=35.5,
        measurement_timestamp=datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        http_client=client,
    )
    assert is_success is True
    assert status_code == 201
    assert response_data["value"] == 35.5
    assert "id" in response_data


def test_send_single_measurement_out_of_range_rejected_f4(client: TestClient):
    """Verify F4 requirement: server rejects out-of-range measurement and returns Problem Details."""
    unused_series_id, unused_sensor_id, sensor_api_key = setup_test_series_and_sensor(client)

    # Dozwolony zakres dla tej serii to [10.0, 50.0], przesyłamy 99.9
    is_success, status_code, response_data = send_single_measurement(
        api_base_url="http://testserver",
        sensor_api_key=sensor_api_key,
        measurement_value=99.9,
        http_client=client,
    )
    assert is_success is False
    assert status_code == 422
    assert "detail" in response_data
    assert "range" in response_data["detail"].lower() or "outside" in response_data["detail"].lower()


def test_send_single_measurement_invalid_api_key(client: TestClient):
    """Verify unauthorized rejection code 401 when API key is invalid."""
    is_success, status_code, response_data = send_single_measurement(
        api_base_url="http://testserver",
        sensor_api_key="niepoprawny_klucz_api_99999999999999999999",
        measurement_value=25.0,
        http_client=client,
    )
    assert is_success is False
    assert status_code == 401


def test_run_generator_history_mode_batches_data(client: TestClient):
    """Verify run_generator in history mode successfully transmits configured batch of measurements."""
    series_id, unused_sensor_id, sensor_api_key = setup_test_series_and_sensor(client)

    successful_count = run_generator(
        api_base_url="http://testserver",
        sensor_api_key=sensor_api_key,
        generation_mode="sine",
        minimum_value=15.0,
        maximum_value=45.0,
        measurement_count=6,
        is_history_mode=True,
        history_step_minutes=10.0,
        http_client=client,
    )
    assert successful_count == 6

    # Sprawdzenie w API odczytu zapisanych pomiarów
    get_measurements_response = client.get(f"/api/measurements?series={series_id}&limit=100")
    assert get_measurements_response.status_code == 200
    stored_measurements = get_measurements_response.json()
    assert len(stored_measurements) == 6


def test_seed_waterdeep_demo_data_integration(client: TestClient):
    """Verify F11 requirement: seeding script sets up canonical series and transmits >= 20 measurements each."""
    seeding_result = seed_waterdeep_demo_data(
        api_base_url="http://testserver",
        admin_username=settings.default_user_username,
        admin_password=settings.default_user_password,
        measurements_per_series=20,
        http_client=client,
    )

    assert seeding_result["status"] == "success"
    assert seeding_result["series_count"] == len(CANONICAL_WATERDEEP_SERIES)
    assert seeding_result["total_measurements"] == len(CANONICAL_WATERDEEP_SERIES) * 20

    # 1. Sprawdzenie czy w API znajduje się co najmniej 6 serii
    series_list_response = client.get("/api/series")
    assert series_list_response.status_code == 200
    all_series = series_list_response.json()
    assert len(all_series) >= 6

    # 2. Sprawdzenie czy każda z kanonicznych serii ma 20 pomiarów (wymóg F11: co najmniej 3 serie z min. 15 pomiarami)
    for series_item in all_series:
        series_measurements_response = client.get(f"/api/measurements?series={series_item['id']}&limit=1000")
        assert series_measurements_response.status_code == 200
        measurements_list = series_measurements_response.json()
        assert len(measurements_list) == 20

    # 3. Weryfikacja idempotencji: ponowne wywołanie nie dubluje serii
    second_seeding_result = seed_waterdeep_demo_data(
        api_base_url="http://testserver",
        admin_username=settings.default_user_username,
        admin_password=settings.default_user_password,
        measurements_per_series=5,
        http_client=client,
    )
    assert second_seeding_result["status"] == "success"
    assert second_seeding_result["series_count"] == len(CANONICAL_WATERDEEP_SERIES)

    # Liczba serii nadal wynosi 6
    after_second_series_response = client.get("/api/series")
    assert len(after_second_series_response.json()) == 6
