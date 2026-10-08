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


def test_get_series_empty_list(client: TestClient):
    response = client.get("/api/series")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "http_method, endpoint_template, payload",
    [
        (
            "POST",
            "/api/series",
            {
                "name": "Temperatura",
                "minValue": -20.0,
                "maxValue": 50.0,
                "color": "#1f77b4",
            },
        ),
        (
            "PUT",
            "/api/series/1",
            {
                "name": "Temperatura",
                "minValue": -20.0,
                "maxValue": 50.0,
                "color": "#1f77b4",
            },
        ),
        (
            "DELETE",
            "/api/series/1",
            None,
        ),
    ],
)
def test_series_operations_unauthorized(
    client: TestClient,
    http_method: str,
    endpoint_template: str,
    payload: dict,
):
    """Ensure mutating series endpoints reject requests without authorization."""
    if http_method == "POST":
        response = client.post(endpoint_template, json=payload)
    elif http_method == "PUT":
        response = client.put(endpoint_template, json=payload)
    elif http_method == "DELETE":
        response = client.delete(endpoint_template)
    else:
        raise ValueError(f"Unsupported HTTP method: {http_method}")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


@pytest.mark.parametrize(
    "series_payload, expected_status_code",
    [
        # 1. Poprawna pełna seria
        (
            {
                "name": "Temperatura Powietrza",
                "minValue": -40.0,
                "maxValue": 60.0,
                "color": "#1f77b4",
                "icon": "thermometer",
                "unit": "°C",
            },
            201,
        ),
        # 2. Poprawna minimalna seria (bez icon i unit)
        (
            {
                "name": "Ciśnienie",
                "minValue": 900.0,
                "maxValue": 1100.0,
                "color": "#ff7f0e",
            },
            201,
        ),
        # 3. Błąd walidacji: minValue == maxValue (naruszenie reguły minValue < maxValue)
        (
            {
                "name": "Zakres Równy",
                "minValue": 10.0,
                "maxValue": 10.0,
                "color": "#1f77b4",
            },
            422,
        ),
        # 4. Błąd walidacji: minValue > maxValue
        (
            {
                "name": "Zakres Odwrócony",
                "minValue": 50.0,
                "maxValue": 10.0,
                "color": "#1f77b4",
            },
            422,
        ),
        # 5. Błąd walidacji: niepoprawny format koloru (brak znaku #)
        (
            {
                "name": "Zły Kolor Bez Hasza",
                "minValue": 0.0,
                "maxValue": 100.0,
                "color": "1f77b4",
            },
            422,
        ),
        # 6. Błąd walidacji: zbyt krótki kod koloru HEX
        (
            {
                "name": "Zły Kolor Trzycyfrowy",
                "minValue": 0.0,
                "maxValue": 100.0,
                "color": "#123",
            },
            422,
        ),
        # 7. Błąd walidacji: pusta nazwa serii
        (
            {
                "name": "",
                "minValue": 0.0,
                "maxValue": 100.0,
                "color": "#1f77b4",
            },
            422,
        ),
        # 8. Błąd walidacji: brak wymaganego pola name
        (
            {
                "minValue": 0.0,
                "maxValue": 100.0,
                "color": "#1f77b4",
            },
            422,
        ),
    ],
)
def test_create_series_parametrized_validation_and_creation(
    client: TestClient,
    series_payload: dict,
    expected_status_code: int,
):
    """Test creating series with both valid and invalid payloads."""
    auth_token = get_authenticated_bearer_token(client)
    create_response = client.post(
        "/api/series",
        json=series_payload,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == expected_status_code

    if expected_status_code == 201:
        created_series = create_response.json()
        assert isinstance(created_series["id"], int)
        assert created_series["name"] == series_payload["name"]
        assert created_series["minValue"] == series_payload["minValue"]
        assert created_series["maxValue"] == series_payload["maxValue"]
        assert created_series["color"] == series_payload["color"]
        assert created_series.get("icon") == series_payload.get("icon")
        assert created_series.get("unit") == series_payload.get("unit")

        # Sprawdzenie nagłówka Location
        expected_location = f"/api/series/{created_series['id']}"
        assert create_response.headers.get("Location") == expected_location

        # Sprawdzenie obecności na liście
        list_response = client.get("/api/series")
        assert list_response.status_code == 200
        matching_series = [
            series_item for series_item in list_response.json()
            if series_item["id"] == created_series["id"]
        ]
        assert len(matching_series) == 1
    else:
        assert create_response.headers["content-type"].startswith("application/problem+json")
        problem_details = create_response.json()
        assert problem_details["status"] == expected_status_code
        assert problem_details["title"] == "Unprocessable Entity"


def test_get_series_by_id(client: TestClient):
    auth_token = get_authenticated_bearer_token(client)
    series_name = "Ciśnienie Atmosferyczne"
    series_min_value = 900.0
    series_max_value = 1100.0
    series_color = "#ff7f0e"
    series_unit = "hPa"

    create_response = client.post(
        "/api/series",
        json={
            "name": series_name,
            "minValue": series_min_value,
            "maxValue": series_max_value,
            "color": series_color,
            "unit": series_unit,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == 201
    series_id = create_response.json()["id"]

    # Poprawne pobranie po ID
    get_response = client.get(f"/api/series/{series_id}")
    assert get_response.status_code == 200
    retrieved_series = get_response.json()
    assert retrieved_series["id"] == series_id
    assert retrieved_series["name"] == series_name
    assert retrieved_series["minValue"] == series_min_value
    assert retrieved_series["maxValue"] == series_max_value
    assert retrieved_series["color"] == series_color
    assert retrieved_series["unit"] == series_unit

    # Pobranie nieistniejącej serii
    not_found_response = client.get("/api/series/999999999")
    assert not_found_response.status_code == 404
    assert not_found_response.headers["content-type"].startswith("application/problem+json")


def test_update_series_success(client: TestClient):
    auth_token = get_authenticated_bearer_token(client)
    initial_name = "Wilgotność"
    initial_min_value = 0.0
    initial_max_value = 100.0
    initial_color = "#2ca02c"
    initial_unit = "%"

    create_response = client.post(
        "/api/series",
        json={
            "name": initial_name,
            "minValue": initial_min_value,
            "maxValue": initial_max_value,
            "color": initial_color,
            "unit": initial_unit,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    series_id = create_response.json()["id"]

    updated_name = "Wilgotność Względna"
    updated_min_value = 5.0
    updated_max_value = 95.0
    updated_color = "#17becf"
    updated_icon = "water-percent"
    updated_unit = "%RH"

    update_response = client.put(
        f"/api/series/{series_id}",
        json={
            "name": updated_name,
            "minValue": updated_min_value,
            "maxValue": updated_max_value,
            "color": updated_color,
            "icon": updated_icon,
            "unit": updated_unit,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert update_response.status_code == 200
    updated_series = update_response.json()
    assert updated_series["id"] == series_id
    assert updated_series["name"] == updated_name
    assert updated_series["minValue"] == updated_min_value
    assert updated_series["maxValue"] == updated_max_value
    assert updated_series["color"] == updated_color
    assert updated_series["icon"] == updated_icon
    assert updated_series["unit"] == updated_unit


@pytest.mark.parametrize(
    "new_min_value, new_max_value, expected_status_code",
    [
        # Istniejący pomiar to 22.5:
        # 1. Zakres [25.0, 35.0] wyklucza 22.5 (22.5 < 25.0) -> konflikt 409
        (25.0, 35.0, 409),
        # 2. Zakres [10.0, 20.0] wyklucza 22.5 (22.5 > 20.0) -> konflikt 409
        (10.0, 20.0, 409),
        # 3. Zakres [20.0, 30.0] obejmuje 22.5 (20.0 <= 22.5 <= 30.0) -> sukces 200
        (20.0, 30.0, 200),
        # 4. Zakres brzegowy [22.5, 30.0] obejmuje 22.5 -> sukces 200
        (22.5, 30.0, 200),
        # 5. Zakres brzegowy [15.0, 22.5] obejmuje 22.5 -> sukces 200
        (15.0, 22.5, 200),
    ],
)
def test_update_series_range_boundary_parametrized(
    client: TestClient,
    new_min_value: float,
    new_max_value: float,
    expected_status_code: int,
):
    """Ensure updating series range enforces existing measurements constraint (409 vs 200)."""
    auth_token = get_authenticated_bearer_token(client)
    series_name = "Temperatura Pokoju"
    create_response = client.post(
        "/api/series",
        json={
            "name": series_name,
            "minValue": 0.0,
            "maxValue": 40.0,
            "color": "#d62728",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    series_id = create_response.json()["id"]

    # Symulacja istnienia pomiaru o wartości 22.5 w bazie danych
    database_session_generator = client.app.dependency_overrides[get_db]()
    database_session = next(database_session_generator)
    try:
        sample_sensor = Sensor(
            name="Sensor Pokojowy",
            series_id=series_id,
            api_key_hash="dummy_hash_for_sensor",
        )
        database_session.add(sample_sensor)
        database_session.commit()
        database_session.refresh(sample_sensor)

        sample_measurement = Measurement(
            series_id=series_id,
            sensor_id=sample_sensor.id,
            value=22.5,
            timestamp=utc_now(),
        )
        database_session.add(sample_measurement)
        database_session.commit()
    finally:
        database_session.close()

    # Wykonanie żądania aktualizacji zakresu
    update_response = client.put(
        f"/api/series/{series_id}",
        json={
            "name": series_name,
            "minValue": new_min_value,
            "maxValue": new_max_value,
            "color": "#d62728",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert update_response.status_code == expected_status_code

    if expected_status_code == 200:
        updated_data = update_response.json()
        assert updated_data["minValue"] == new_min_value
        assert updated_data["maxValue"] == new_max_value
    elif expected_status_code == 409:
        assert update_response.headers["content-type"].startswith("application/problem+json")
        problem_details = update_response.json()
        assert problem_details["title"] == "Conflict"
        assert "excludes existing measurements" in problem_details["detail"]


def test_delete_series_cascade(client: TestClient):
    auth_token = get_authenticated_bearer_token(client)
    create_response = client.post(
        "/api/series",
        json={
            "name": "Seria Do Usuniecia",
            "minValue": -10.0,
            "maxValue": 50.0,
            "color": "#bcbd22",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    series_id = create_response.json()["id"]

    # Poprawne usunięcie z autoryzacją
    delete_response = client.delete(
        f"/api/series/{series_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert delete_response.status_code == 204

    # Weryfikacja że seria już nie istnieje
    get_after_delete = client.get(f"/api/series/{series_id}")
    assert get_after_delete.status_code == 404

    # Próba ponownego usunięcia
    delete_again_response = client.delete(
        f"/api/series/{series_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert delete_again_response.status_code == 404
