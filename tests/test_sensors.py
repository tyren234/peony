import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import Measurement, Sensor, Series, utc_now


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


def create_sample_series(client: TestClient, auth_token: str) -> int:
    """Helper function to create a test series and return its identifier."""
    series_payload = {
        "name": "Seria Testowa Dla Czujnikow",
        "minValue": 0.0,
        "maxValue": 100.0,
        "color": "#1f77b4",
    }
    create_response = client.post(
        "/api/series",
        json=series_payload,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == 201
    return create_response.json()["id"]


@pytest.mark.parametrize(
    "http_method, endpoint_template, payload",
    [
        ("GET", "/api/sensors", None),
        ("POST", "/api/sensors", {"name": "Czujnik", "seriesId": 1}),
        ("GET", "/api/sensors/1", None),
        ("DELETE", "/api/sensors/1", None),
    ],
)
def test_sensor_operations_unauthorized(
    client: TestClient,
    http_method: str,
    endpoint_template: str,
    payload: dict,
):
    """Ensure all sensor endpoints strictly require Bearer authentication."""
    if http_method == "GET":
        response = client.get(endpoint_template)
    elif http_method == "POST":
        response = client.post(endpoint_template, json=payload)
    elif http_method == "DELETE":
        response = client.delete(endpoint_template)
    else:
        raise ValueError(f"Unsupported HTTP method: {http_method}")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


def test_get_sensors_empty_list(client: TestClient):
    auth_token = get_authenticated_bearer_token(client)
    response = client.get(
        "/api/sensors",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "sensor_payload_override, expected_status_code",
    [
        # 1. Poprawna rejestracja z prawidłowymi danymi -> 201
        (
            {"name": "Czujnik Poprawny"},
            201,
        ),
        # 2. Rejestracja z nieistniejącą serią -> 422 Unprocessable Entity
        (
            {"name": "Czujnik Nieistniejaca Seria", "seriesId": 999999},
            422,
        ),
        # 3. Pusta nazwa czujnika -> 422
        (
            {"name": ""},
            422,
        ),
        # 4. Zbyt długa nazwa czujnika (> 100 znaków) -> 422
        (
            {"name": "N" * 105},
            422,
        ),
        # 5. Brak wymaganego pola name -> 422
        (
            {"_exclude_name": True},
            422,
        ),
        # 6. Brak wymaganego pola seriesId -> 422
        (
            {"_exclude_series_id": True},
            422,
        ),
        # 7. Niepoprawny typ pola seriesId (string zamiast int) -> 422
        (
            {"seriesId": "nie-liczba"},
            422,
        ),
    ],
)
def test_register_sensor_validation_parametrized(
    client: TestClient,
    sensor_payload_override: dict,
    expected_status_code: int,
):
    """Parametrized testing of sensor registration input validation and foreign series check."""
    auth_token = get_authenticated_bearer_token(client)
    actual_series_id = create_sample_series(client, auth_token)

    sensor_payload = {
        "name": "Domyslna Nazwa Sensora",
        "seriesId": actual_series_id,
    }

    # Aplikacja nadpisań ze scenariusza testowego
    for override_key, override_value in sensor_payload_override.items():
        if override_key == "_exclude_name":
            sensor_payload.pop("name", None)
        elif override_key == "_exclude_series_id":
            sensor_payload.pop("seriesId", None)
        else:
            sensor_payload[override_key] = override_value

    create_response = client.post(
        "/api/sensors",
        json=sensor_payload,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == expected_status_code

    if expected_status_code == 201:
        created_sensor = create_response.json()
        assert isinstance(created_sensor["id"], int)
        assert created_sensor["name"] == sensor_payload["name"]
        assert created_sensor["seriesId"] == actual_series_id
        assert isinstance(created_sensor["apiKey"], str)
        assert len(created_sensor["apiKey"]) >= 32
        assert "createdAt" in created_sensor
        assert created_sensor["lastMeasurementAt"] is None

        # Weryfikacja nagłówka Location
        expected_location = f"/api/sensors/{created_sensor['id']}"
        assert create_response.headers.get("Location") == expected_location
    else:
        assert create_response.headers["content-type"].startswith("application/problem+json")
        problem_details = create_response.json()
        assert problem_details["status"] == expected_status_code
        assert problem_details["title"] in ("Unprocessable Entity", "Bad Request")


@pytest.mark.parametrize(
    "http_method",
    ["GET", "DELETE"],
)
def test_sensor_operations_on_non_existent_id_parametrized(
    client: TestClient,
    http_method: str,
):
    """Ensure GET and DELETE operations on non-existent sensor identifiers return 404."""
    auth_token = get_authenticated_bearer_token(client)
    non_existent_sensor_id = 999999999
    endpoint_path = f"/api/sensors/{non_existent_sensor_id}"

    if http_method == "GET":
        response = client.get(endpoint_path, headers={"Authorization": f"Bearer {auth_token}"})
    elif http_method == "DELETE":
        response = client.delete(endpoint_path, headers={"Authorization": f"Bearer {auth_token}"})
    else:
        raise ValueError(f"Unsupported HTTP method: {http_method}")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    problem_details = response.json()
    assert problem_details["status"] == 404
    assert problem_details["title"] == "Not Found"


def test_sensor_details_and_security_leak_check(client: TestClient):
    """Ensure sensor endpoints never leak apiKeyHash or secret API keys in subsequent reads."""
    auth_token = get_authenticated_bearer_token(client)
    sample_series_id = create_sample_series(client, auth_token)

    sensor_name = "Barometr Południowy"
    register_response = client.post(
        "/api/sensors",
        json={"name": sensor_name, "seriesId": sample_series_id},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert register_response.status_code == 201
    sensor_id = register_response.json()["id"]
    registered_api_key = register_response.json()["apiKey"]

    # 1. Pobranie pojedynczego czujnika
    single_sensor_response = client.get(
        f"/api/sensors/{sensor_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert single_sensor_response.status_code == 200
    sensor_data = single_sensor_response.json()
    assert sensor_data["id"] == sensor_id
    assert sensor_data["name"] == sensor_name
    assert sensor_data["seriesId"] == sample_series_id
    assert sensor_data["lastMeasurementAt"] is None

    # Bezpieczeństwo: brak klucza i skrótów w treści odpowiedzi
    response_text = single_sensor_response.text
    forbidden_security_substrings = [
        registered_api_key,
        "apikeyhash",
        "api_key_hash",
        "password",
        "hash",
    ]
    for forbidden_substring in forbidden_security_substrings:
        assert forbidden_substring.lower() not in response_text.lower()

    # 2. Pobranie listy czujników
    list_sensors_response = client.get(
        "/api/sensors",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert list_sensors_response.status_code == 200
    all_sensors = list_sensors_response.json()
    assert len(all_sensors) == 1
    assert all_sensors[0]["id"] == sensor_id
    assert "apiKey" not in all_sensors[0]
    assert "apiKeyHash" not in all_sensors[0]


def test_unregister_sensor_retains_measurements(client: TestClient):
    auth_token = get_authenticated_bearer_token(client)
    sample_series_id = create_sample_series(client, auth_token)
    sample_sensor_name = "Czujnik Do Wyrejestrowania"
    sample_measurement_value = 42.0

    # Rejestracja czujnika
    register_response = client.post(
        "/api/sensors",
        json={"name": sample_sensor_name, "seriesId": sample_series_id},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    sensor_id = register_response.json()["id"]

    # Symulacja istnienia pomiaru powiązanego z czujnikiem
    database_session_generator = client.app.dependency_overrides[get_db]()
    database_session = next(database_session_generator)
    try:
        sample_measurement = Measurement(
            series_id=sample_series_id,
            sensor_id=sensor_id,
            value=sample_measurement_value,
            timestamp=utc_now(),
        )
        database_session.add(sample_measurement)
        database_session.commit()
        database_session.refresh(sample_measurement)
        measurement_id = sample_measurement.id
    finally:
        database_session.close()

    # Wyrejestrowanie czujnika
    delete_response = client.delete(
        f"/api/sensors/{sensor_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert delete_response.status_code == 204

    # Weryfikacja że czujnik nie jest już dostępny
    get_after_delete = client.get(
        f"/api/sensors/{sensor_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert get_after_delete.status_code == 404

    # Kluczowy wymóg kontraktu: pomiar nadal istnieje, a sensor_id został ustawiony na None
    database_session = next(client.app.dependency_overrides[get_db]())
    try:
        retained_measurement = (
            database_session.query(Measurement)
            .filter(Measurement.id == measurement_id)
            .first()
        )
        assert retained_measurement is not None
        assert retained_measurement.sensor_id is None
        assert retained_measurement.value == sample_measurement_value
    finally:
        database_session.close()
