from datetime import datetime, timedelta, timezone
from typing import Optional
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.models import utc_now


def get_authenticated_bearer_token(client: TestClient) -> str:
    """Helper function to log in and retrieve the Bearer access token."""
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": settings.default_user_username,
            "password": settings.default_user_password,
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["accessToken"]
    return access_token


def setup_series_and_sensor(
    client: TestClient,
    min_value: float = 0.0,
    max_value: float = 100.0,
) -> tuple[int, int, str]:
    """Helper creating a series and sensor, returning (series_id, sensor_id, api_key)."""
    auth_token = get_authenticated_bearer_token(client)
    series_response = client.post(
        "/api/series",
        json={
            "name": "Seria Pomiary Testowe",
            "minValue": min_value,
            "maxValue": max_value,
            "color": "#1f77b4",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert series_response.status_code == 201
    series_id = series_response.json()["id"]

    sensor_response = client.post(
        "/api/sensors",
        json={
            "name": "Czujnik Telemetrii",
            "seriesId": series_id,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert sensor_response.status_code == 201
    sensor_id = sensor_response.json()["id"]
    api_key = sensor_response.json()["apiKey"]

    return series_id, sensor_id, api_key


@pytest.mark.parametrize(
    "header_configuration, expected_status_code",
    [
        # 1. Brak jakichkolwiek nagłówków uwierzytelniających
        ({}, 401),
        # 2. Pusty klucz X-API-Key
        ({"X-API-Key": ""}, 401),
        # 3. Nieprawidłowy/sfałszowany klucz API
        ({"X-API-Key": "x" * 40}, 401),
        # 4. Token Bearer administratora zamiast klucza czujnika (wymóg kontraktu)
        ({"Authorization": "Bearer test_dummy_bearer_token"}, 401),
    ],
)
def test_measurement_post_authentication_parametrized(
    client: TestClient,
    header_configuration: dict,
    expected_status_code: int,
):
    """Ensure POST /api/measurements rejects invalid authentication formats with 401."""
    response = client.post(
        "/api/measurements",
        json={"value": 25.0},
        headers=header_configuration,
    )
    assert response.status_code == expected_status_code
    assert response.headers["content-type"].startswith("application/problem+json")


@pytest.mark.parametrize(
    "measurement_value, timestamp_delta, expected_status_code",
    [
        # 1. Poprawny wynik w przedziale bez timestampu -> 201
        (25.0, None, 201),
        # 2. Poprawny wynik na dolnej granicy -> 201
        (0.0, None, 201),
        # 3. Poprawny wynik na górnej granicy -> 201
        (100.0, None, 201),
        # 4. Poprawny wynik ze znacznikiem z przeszłości (-1 godzina) -> 201
        (50.0, timedelta(hours=-1), 201),
        # 5. Wynik poniżej min_value (-0.1) -> 422
        (-0.1, None, 422),
        # 6. Wynik powyżej max_value (100.1) -> 422
        (100.1, None, 422),
        # 7. Znacznik czasu zbyt daleko w przyszłości (+10 minut > +5 minut) -> 422
        (50.0, timedelta(minutes=10), 422),
    ],
)
def test_create_measurement_validation_parametrized(
    client: TestClient,
    measurement_value: float,
    timestamp_delta: Optional[timedelta],
    expected_status_code: int,
):
    """Parametrized testing of measurement range validation, timestamp limits, and Location header."""
    series_id, sensor_id, api_key = setup_series_and_sensor(client, min_value=0.0, max_value=100.0)

    measurement_payload: dict = {"value": measurement_value}
    if timestamp_delta is not None:
        target_timestamp = utc_now() + timestamp_delta
        measurement_payload["timestamp"] = target_timestamp.isoformat()

    create_response = client.post(
        "/api/measurements",
        json=measurement_payload,
        headers={"X-API-Key": api_key},
    )
    assert create_response.status_code == expected_status_code

    if expected_status_code == 201:
        created_measurement = create_response.json()
        assert isinstance(created_measurement["id"], int)
        assert created_measurement["seriesId"] == series_id
        assert created_measurement["sensorId"] == sensor_id
        assert created_measurement["value"] == measurement_value
        assert "timestamp" in created_measurement

        # Weryfikacja nagłówka Location
        expected_location = f"/api/measurements/{created_measurement['id']}"
        assert create_response.headers.get("Location") == expected_location

        # Odczyt utworzonego pomiaru pod adresem z nagłówka Location
        location_fetch_response = client.get(expected_location)
        assert location_fetch_response.status_code == 200
        fetched_data = location_fetch_response.json()
        assert fetched_data["id"] == created_measurement["id"]
        assert fetched_data["value"] == measurement_value
    else:
        assert create_response.headers["content-type"].startswith("application/problem+json")
        problem_details = create_response.json()
        assert problem_details["status"] == expected_status_code
        assert problem_details["title"] == "Unprocessable Entity"


@pytest.mark.parametrize(
    "malformed_payload, expected_status_code",
    [
        # 1. Nieliczbowa wartość pomiaru (string) -> 422
        ({"value": "abc"}, 422),
        # 2. Puste ciało żądania (brak wymaganego pola value) -> 422
        ({}, 422),
        # 3. Niepoprawny format daty w znaczniku czasu -> 422
        ({"value": 15.0, "timestamp": "wczoraj"}, 422),
    ],
)
def test_create_measurement_malformed_payloads_parametrized(
    client: TestClient,
    malformed_payload: dict,
    expected_status_code: int,
):
    """Ensure malformed JSON bodies are rejected according to contract."""
    unused_series_id, unused_sensor_id, api_key = setup_series_and_sensor(client)
    response = client.post(
        "/api/measurements",
        json=malformed_payload,
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == expected_status_code
    assert response.headers["content-type"].startswith("application/problem+json")


def test_get_measurements_filtering_and_sorting(client: TestClient):
    """Verify series query filtering, closed timestamp intervals, sorting orders, and limit."""
    first_series_id, unused_first_sensor_id, first_api_key = setup_series_and_sensor(client)
    second_series_id, unused_second_sensor_id, second_api_key = setup_series_and_sensor(client)

    reference_start_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    first_timestamp = reference_start_time + timedelta(minutes=10)
    second_timestamp = reference_start_time + timedelta(minutes=20)
    third_timestamp = reference_start_time + timedelta(minutes=30)

    # Wysłanie pomiaru 1 (seria 1, t = 10m)
    client.post(
        "/api/measurements",
        json={"value": 10.0, "timestamp": first_timestamp.isoformat()},
        headers={"X-API-Key": first_api_key},
    )
    # Wysłanie pomiaru 2 (seria 2, t = 20m)
    client.post(
        "/api/measurements",
        json={"value": 20.0, "timestamp": second_timestamp.isoformat()},
        headers={"X-API-Key": second_api_key},
    )
    # Wysłanie pomiaru 3 (seria 1, t = 30m)
    client.post(
        "/api/measurements",
        json={"value": 30.0, "timestamp": third_timestamp.isoformat()},
        headers={"X-API-Key": first_api_key},
    )

    # Test 1a: Pobranie wszystkich pomiarów (domyślnie sort=timestamp rosnąco)
    all_response = client.get("/api/measurements")
    assert all_response.status_code == 200
    all_items = all_response.json()
    assert len(all_items) == 3
    assert all_items[0]["value"] == 10.0
    assert all_items[1]["value"] == 20.0
    assert all_items[2]["value"] == 30.0

    # Test 1b: Jawne sortowanie rosnące sort=timestamp
    explicit_asc_response = client.get("/api/measurements?sort=timestamp")
    assert explicit_asc_response.status_code == 200
    explicit_asc_items = explicit_asc_response.json()
    assert len(explicit_asc_items) == 3
    assert explicit_asc_items[0]["value"] == 10.0
    assert explicit_asc_items[2]["value"] == 30.0

    # Test 2: Sortowanie malejące sort=-timestamp
    descending_response = client.get("/api/measurements?sort=-timestamp")
    assert descending_response.status_code == 200
    descending_items = descending_response.json()
    assert descending_items[0]["value"] == 30.0
    assert descending_items[2]["value"] == 10.0

    # Test 3: Filtrowanie po pojedynczej serii (?series=...)
    filter_first_series = client.get(f"/api/measurements?series={first_series_id}")
    assert filter_first_series.status_code == 200
    first_series_items = filter_first_series.json()
    assert len(first_series_items) == 2
    assert all(item["seriesId"] == first_series_id for item in first_series_items)

    # Test 4: Filtrowanie po wielu serii (?series=id1,id2)
    filter_both_series = client.get(f"/api/measurements?series={first_series_id},{second_series_id}")
    assert filter_both_series.status_code == 200
    assert len(filter_both_series.json()) == 3

    # Test 5: Filtrowanie zakresowe (from <= t <= to)
    time_filter_query = (
        f"/api/measurements?from={first_timestamp.isoformat()}&to={second_timestamp.isoformat()}"
    )
    range_response = client.get(time_filter_query)
    assert range_response.status_code == 200
    range_items = range_response.json()
    assert len(range_items) == 2
    assert range_items[0]["value"] == 10.0
    assert range_items[1]["value"] == 20.0

    # Test 6: Domkniętość przedziału w pojedynczym punkcie (from == to)
    exact_point_query = (
        f"/api/measurements?from={first_timestamp.isoformat()}&to={first_timestamp.isoformat()}"
    )
    exact_point_response = client.get(exact_point_query)
    assert exact_point_response.status_code == 200
    exact_items = exact_point_response.json()
    assert len(exact_items) == 1
    assert exact_items[0]["value"] == 10.0

    # Test 7: Ograniczenie liczby wyników parametrem limit
    limit_response = client.get("/api/measurements?limit=2")
    assert limit_response.status_code == 200
    assert len(limit_response.json()) == 2

    # Test 8: Pusty zakres czasu w odległej przyszłości
    empty_future_query = "/api/measurements?from=2030-01-01T00:00:00Z&to=2030-01-02T00:00:00Z"
    empty_response = client.get(empty_future_query)
    assert empty_response.status_code == 200
    assert empty_response.json() == []


@pytest.mark.parametrize(
    "invalid_query_parameter",
    [
        "from=nie-data",
        "to=nie-data",
        "series=abc",
        "sort=niepoprawne_sortowanie",
        "limit=0",
        "limit=999999",
        # Odwrócony przedział czasowy: from > to
        "from=2026-01-02T10:00:00Z&to=2026-01-01T10:00:00Z",
    ],
)
def test_get_measurements_invalid_query_parameters_return_400(
    client: TestClient,
    invalid_query_parameter: str,
):
    """Ensure malformed query parameters trigger strict RFC 9457 Bad Request (400)."""
    response = client.get(f"/api/measurements?{invalid_query_parameter}")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")


def test_sensor_last_measurement_at_retains_maximum_time(client: TestClient):
    """Ensure sensor lastMeasurementAt retains the newest timestamp and does not regress on historical data."""
    auth_token = get_authenticated_bearer_token(client)
    series_id, sensor_id, api_key = setup_series_and_sensor(client)

    newer_time = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    older_historical_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Zapis nowego pomiaru
    client.post(
        "/api/measurements",
        json={"value": 50.0, "timestamp": newer_time.isoformat()},
        headers={"X-API-Key": api_key},
    )
    sensor_response_after_newer = client.get(
        f"/api/sensors/{sensor_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert sensor_response_after_newer.status_code == 200
    assert "2026-05-01" in sensor_response_after_newer.json()["lastMeasurementAt"]

    # 2. Dosłanie pomiaru z przeszłości (starszego)
    client.post(
        "/api/measurements",
        json={"value": 40.0, "timestamp": older_historical_time.isoformat()},
        headers={"X-API-Key": api_key},
    )
    sensor_response_after_older = client.get(
        f"/api/sensors/{sensor_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert sensor_response_after_older.status_code == 200
    # Znacznik nie powinien się cofnąć do stycznia:
    assert "2026-05-01" in sensor_response_after_older.json()["lastMeasurementAt"]


def test_get_measurement_by_id(client: TestClient):
    unused_series_id, unused_sensor_id, api_key = setup_series_and_sensor(client)
    measurement_value = 77.5
    create_response = client.post(
        "/api/measurements",
        json={"value": measurement_value},
        headers={"X-API-Key": api_key},
    )
    measurement_id = create_response.json()["id"]

    # Poprawne pobranie po ID
    get_response = client.get(f"/api/measurements/{measurement_id}")
    assert get_response.status_code == 200
    measurement_data = get_response.json()
    assert measurement_data["id"] == measurement_id
    assert measurement_data["value"] == measurement_value

    # Pobranie nieistniejącego pomiaru
    not_found_response = client.get("/api/measurements/999999999")
    assert not_found_response.status_code == 404
    assert not_found_response.headers["content-type"].startswith("application/problem+json")


@pytest.mark.parametrize(
    "http_method",
    ["PUT", "PATCH", "DELETE"],
)
def test_measurements_immutable_cannot_modify_or_delete_parametrized(
    client: TestClient,
    http_method: str,
):
    """Contract rule: measurements cannot be modified or deleted (404 or 405)."""
    unused_series_id, unused_sensor_id, api_key = setup_series_and_sensor(client)
    auth_token = get_authenticated_bearer_token(client)

    create_response = client.post(
        "/api/measurements",
        json={"value": 15.0},
        headers={"X-API-Key": api_key},
    )
    measurement_id = create_response.json()["id"]

    endpoint_path = f"/api/measurements/{measurement_id}"
    request_headers = {"Authorization": f"Bearer {auth_token}"}
    dummy_payload = {"value": 20.0}

    if http_method == "PUT":
        response = client.put(endpoint_path, json=dummy_payload, headers=request_headers)
    elif http_method == "PATCH":
        response = client.patch(endpoint_path, json=dummy_payload, headers=request_headers)
    elif http_method == "DELETE":
        response = client.delete(endpoint_path, headers=request_headers)
    else:
        raise ValueError(f"Unsupported method: {http_method}")

    # Kontrakt akceptuje 404 lub 405
    assert response.status_code in (404, 405)

    # Weryfikacja że pomiar pozostał nienaruszony
    verify_response = client.get(endpoint_path)
    assert verify_response.status_code == 200
    assert verify_response.json()["value"] == 15.0
