from backend.app.config import settings


def test_login_success(client):
    login_payload = {
        "username": settings.default_user_username,
        "password": settings.default_user_password,
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200

    response_data = response.json()
    assert "accessToken" in response_data
    assert isinstance(response_data["accessToken"], str)
    assert len(response_data["accessToken"]) >= 32
    assert response_data["tokenType"] == "Bearer"
    assert response_data["expiresIn"] == settings.token_expiration_seconds


def test_login_invalid_password(client):
    login_payload = {
        "username": settings.default_user_username,
        "password": f"{settings.default_user_password}_invalid",
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.headers.get("content-type").startswith("application/problem+json")

    response_data = response.json()
    assert response_data["status"] == 401
    assert response_data["title"] == "Unauthorized"


def test_login_non_existent_user(client):
    login_payload = {
        "username": "non_existent_random_user_12345",
        "password": settings.default_user_password,
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.headers.get("content-type").startswith("application/problem+json")


def test_logout_invalidates_token(client):
    # 1. Zaloguj się danymi z konfiguracji
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": settings.default_user_username,
            "password": settings.default_user_password,
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["accessToken"]
    access_token_type = login_response.json()["tokenType"]
    authorization_header = {"Authorization": f"{access_token_type} {access_token}"}

    # 2. Wyloguj się
    logout_response = client.post("/api/auth/logout", headers=authorization_header)
    assert logout_response.status_code == 204

    # 3. Ponowna próba wylogowania tym samym tokenem zwraca 401
    second_logout_response = client.post("/api/auth/logout", headers=authorization_header)
    assert second_logout_response.status_code == 401


def test_logout_without_token(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 401
    assert response.headers.get("content-type").startswith("application/problem+json")


def test_change_password_flow(client):
    # 1. Zaloguj się danymi z konfiguracji
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": settings.default_user_username,
            "password": settings.default_user_password,
        },
    )
    access_token = login_response.json()["accessToken"]
    authorization_header = {"Authorization": f"Bearer {access_token}"}

    # 2. Błędne bieżące hasło -> 403 Forbidden
    wrong_current_response = client.put(
        "/api/auth/password",
        json={
            "currentPassword": f"{settings.default_user_password}_wrong",
            "newPassword": "BrandNewSecurePassword123!",
        },
        headers=authorization_header,
    )
    assert wrong_current_response.status_code == 403
    assert wrong_current_response.headers.get("content-type").startswith("application/problem+json")

    # 3. Zbyt krótkie nowe hasło (< 8 znaków) -> 422 Unprocessable Entity
    short_password_response = client.put(
        "/api/auth/password",
        json={
            "currentPassword": settings.default_user_password,
            "newPassword": "short",
        },
        headers=authorization_header,
    )
    assert short_password_response.status_code == 422

    # 4. Poprawna zmiana hasła -> 204 No Content
    valid_change_response = client.put(
        "/api/auth/password",
        json={
            "currentPassword": settings.default_user_password,
            "newPassword": "BrandNewSecurePassword123!",
        },
        headers=authorization_header,
    )
    assert valid_change_response.status_code == 204

    # 5. Stare hasło z konfiguracji już nie działa
    old_login = client.post(
        "/api/auth/login",
        json={
            "username": settings.default_user_username,
            "password": settings.default_user_password,
        },
    )
    assert old_login.status_code == 401

    # 6. Nowe hasło działa poprawnie
    new_login = client.post(
        "/api/auth/login",
        json={
            "username": settings.default_user_username,
            "password": "BrandNewSecurePassword123!",
        },
    )
    assert new_login.status_code == 200

