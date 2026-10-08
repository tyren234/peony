# 🏰 Waterdeep Watchtower – Rejestr Postępów Realizacji (ZAI 26Z)

> **Zasada pracy:** Małe, czytelne kroki (do ~100–300 linii kodu na krok), dokładny review każdego etapu przed przejściem dalej.
> **Zasada czystego kodu i nazewnictwa:** Bezwzględny zakaz stosowania jednoliterowych skrótów i niejasnych akronimów w nazwach zmiennych (np. `retained_measurement` zamiast `retained_m`, `measurement_id` zamiast `m_id`, `media_type` zamiast `m`). Czytelność i pełne, samoopisujące się nazwy są priorytetem.
> **Język komunikatów API i błędów:** Wszystkie komunikaty błędów, szczegóły (`detail`), tytuły i opisy zwracane przez API (w tym wyjątki RFC 9457 Problem Details) muszą być bezwzględnie w języku angielskim.  
> **Aktualny stan:** Krok 4 zatwierdzony. Przechodzimy do Kroku 5 (Zarządzanie Seriami).

---

## 🗺️ Plan Małych Kroków (Etap E1)

| Krok | Zakres | Rozmiar | Status | Opis |
|:---:|---|:---:|:---:|---|
| **Krok 1** | **Fundament:** Konfiguracja, Połączenie SQLite i endpoint `/api/health` | ~97 linii | ✅ **ZATWIERDZONY** | Środowisko, pydantic-settings, silnik SQLite z obsługą kluczy obcych, aplikacja FastAPI, nagłówek nosniff |
| **Krok 2** | **Modele SQL:** Tabele bazy danych | ~80 linii | ✅ **ZATWIERDZONY** | Modele SQLAlchemy: `users`, `user_tokens`, `series`, `sensors`, `measurements` z indeksami |
| **Krok 3** | **Bezpieczeństwo & RFC 9457:** Haszowanie i obsługa błędów | ~140 linii | ✅ **ZATWIERDZONY** | Haszowanie haseł Argon2id, klucze API SHA-256, format błędów `application/problem+json` |
| **Krok 4** | **Autoryzacja (`/api/auth`):** Zarządzanie sesją | ~120 linii | ✅ **ZATWIERDZONY** | Endpointy `/login`, `/logout`, `/password`, Bearer tokeny, unieważnianie sesji |
| **Krok 5** | **Zarządzanie Seriami (`/api/series`):** CRUD serii | ~130 linii | ⏹️ Oczekuje | Tworzenie serii (201+Location), odczyt publiczny, walidacja i blokada 409 Conflict |
| **Krok 6** | **Zarządzanie Czujnikami (`/api/sensors`):** Rejestracja czujników | ~110 linii | ⏹️ Oczekuje | Rejestracja z jednorazowym kluczem API, wyrejestrowanie (204) bez usuwania pomiarów |
| **Krok 7** | **Pomiary (`/api/measurements`):** Telemetria | ~150 linii | ⏹️ Oczekuje | Zapis z nagłówkiem `X-API-Key`, odczyt z filtrami (`series`, `from`, `to`, `sort`, `limit`) |
| **Krok 8** | **Generator CLI & Zasilenie Danymi:** F13 & F11 | ~180 linii | ⏹️ Oczekuje | Emulator czujników CLI oraz skrypt zasilający 6 bogatych serii po min. 15 pomiarów |

---

## 🔍 Krok 1 – Szczegóły Zrealizowanego Kodu (~97 linii łącznie)

Pliki w repozytorium utworzone w ramach Kroku 1:

1. **`backend/app/config.py`** (14 linii):
   * Klasa `Settings` bazująca na `pydantic-settings`.
   * Definiuje nazwę aplikacji, wersję oraz ścieżkę do bazy SQLite (`sqlite:///./waterdeep.db`).
2. **`backend/app/database.py`** (26 linii):
   * Połączenie z plikiem SQLite (`create_engine`).
   * Zdarzenie SQLAlchemy włączające `PRAGMA foreign_keys=ON;` (domyślnie wyłączone w SQLite).
   * Fabryka sesji `SessionLocal`, klasa bazowa `Base = declarative_base()` oraz generator zależności `get_db()`.
3. **`backend/app/main.py`** (30 linii):
   * Aplikacja `FastAPI` z cyklem życia `lifespan` tworzącym tabele przy starcie.
   * Middleware HTTP dodający nagłówek bezpieczeństwa `X-Content-Type-Options: nosniff`.
   * Publiczny endpoint `GET /api/health` zwracający `{"status": "ok"}`.
4. **`tests/conftest.py`** (8 linii) & **`tests/test_health.py`** (5 linii):
   * Konfiguracja `TestClient` z FastAPI.
   * Test sprawdzający kod 200, odpowiedź `{"status": "ok"}` i obecność nagłówka `nosniff`.
5. **`requirements.txt`** (10 linii) & **`pytest.ini`** (4 linie):
   * Podstawowe zależności i konfiguracja ścieżek pytest.

---

## 🧪 Jak Przetestować Krok 1:

```bash
# Uruchomienie testu jednostkowego:
pytest -v
# Wynik: tests/test_health.py::test_health_endpoint PASSED [100%]

# Uruchomienie serwera lokalnie:
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Sprawdzenie endpointu:
curl -i http://127.0.0.1:8000/api/health
```

---

## 🔍 Krok 2 – Szczegóły Zrealizowanego Kodu (~80 linii modeli + testy)

Pliki w repozytorium utworzone w ramach Kroku 2:

1. **`backend/app/models.py`** (~80 linii):
   * `User`: administrator aplikacji (`id`, `username`, `password_hash`, `created_at`, relacja `tokens`).
   * `UserToken`: sesje i unieważnialne Bearer tokeny (`id`, `token`, `user_id`, `expires_at`, `created_at`).
   * `Series`: serie pomiarowe (`id`, `name`, `min_value`, `max_value`, `color`, `icon`, `unit`, `created_at`).
   * `Sensor`: czujniki IoT (`id`, `name`, `series_id`, `api_key_hash`, `created_at`, `last_measurement_at`).
   * `Measurement`: odczyty telemetrii (`id`, `series_id`, `sensor_id`, `value`, `timestamp`) z indeksem kompozytowym `(series_id, timestamp)` pod szybkie zapytania zakresowe.
   * Reguły kaskadowe:
     * Usunięcie serii usuwa kaskadowo jej czujniki i pomiary (`cascade="all, delete-orphan"`).
     * Wyrejestrowanie czujnika zachowuje zebrane pomiary (`sensor_id` ustawiane na `NULL` – wymóg kontraktu API).
2. **`backend/app/main.py`**:
   * Zaimportowano `backend.app.models`, aby tabele rejestrowały się w `Base.metadata` przed wywołaniem `create_all()`.
3. **`tests/test_models.py`** (~140 linii):
   * 4 testy weryfikujące: tworzenie użytkownika i sesji, tworzenie serii/czujnika/pomiaru, kaskadowe usuwanie serii, zachowanie pomiarów po wyrejestrowaniu czujnika.

---

## 🔍 Krok 3 – Szczegóły Zrealizowanego Kodu (~140 linii)

Pliki w repozytorium utworzone/zaktualizowane w ramach Kroku 3:

1. **`backend/app/security.py`** (35 linii):
   * `hash_password(password)`: Haszowanie Argon2id z automatyczną kryptograficzną solą.
   * `verify_password(plain, hashed)`: Bezpieczna weryfikacja haseł odporna na ataki czasowe.
   * `generate_api_key()`: Generowanie losowych kluczy API (min. 32 znaki, format url-safe).
   * `hash_api_key(api_key)`: Wyliczanie skrótu SHA-256 klucza API do zapisu w bazie.
   * `generate_access_token()`: Generowanie kryptograficznych Bearer tokenów sesji.
2. **`backend/app/errors.py`** (105 linii):
   * `ProblemException`: Dedykowany wyjątek aplikacyjny z polami zgodnymi z RFC 9457 (`title`, `status`, `detail`, `instance`, `errors`).
   * `create_problem_response(...)`: Generator odpowiedzi z nagłówkiem `Content-Type: application/problem+json`.
   * Handlery wyjątków: `problem_exception_handler`, `http_exception_handler`, `validation_exception_handler` (rozróżniający błędy składniowe 400 od semantycznych 422).
3. **`backend/app/main.py`**:
   * Podpięcie globalnych handlerów błędów.
   * Middleware walidujący nagłówek `Accept` (blokada niezgodnych formatów kodem 406 Not Acceptable) oraz `Content-Type` (wymuszenie JSON kodem 415 Unsupported Media Type).
4. **`tests/test_security.py`** & **`tests/test_errors.py`**:
   * 6 nowych testów weryfikujących poprawność Argon2id, SHA-256, format błędów RFC 9457, kody 404, 406 i 415. Łącznie w projekcie: 11/11 testów przechodzi.

---

## 🔍 Krok 4 – Szczegóły Zrealizowanego Kodu (~120 linii)

Pliki w repozytorium utworzone/zaktualizowane w ramach Kroku 4:

1. **`backend/app/schemas/auth.py`** (18 linii):
   * `LoginRequest`: Walidacja pól `username` i `password`.
   * `LoginResponse`: Zwracanie pól `accessToken`, `tokenType: "Bearer"` oraz `expiresIn: 86400`.
   * `PasswordChangeRequest`: Wymóg `currentPassword` oraz `newPassword` o długości minimum 8 znaków.
2. **`backend/app/dependencies.py`** (38 linii):
   * Zależność `get_current_user`: Walidacja nagłówka `Authorization: Bearer <token>`, sprawdzanie istnienia tokenu w tabeli `user_tokens` oraz weryfikacja daty ważności (`expires_at > utc_now()`). Obsługa stref czasowych UTC (`ensure_utc`).
3. **`backend/app/routers/auth.py`** (95 linii):
   * `POST /api/auth/login`: Weryfikacja hasła Argon2id, generowanie tokenu sesji i zapis do bazy z czasem wygaśnięcia 24h.
   * `POST /api/auth/logout`: Usunięcie tokenu z bazy danych (kod `204 No Content`), unieważniające sesję.
   * `PUT /api/auth/password`: Sprawdzenie bieżącego hasła (kod `403 Forbidden` przy błędzie), zhaszowanie nowego hasła i aktualizacja profilu administratora.
4. **`backend/app/main.py`**:
   * Rejestracja routera `auth_router`.
   * Funkcja `init_default_user_account`: Automatyczne utworzenie konta administratora z konfiguracji (`settings.default_user_username` / `settings.default_user_password`) przy starcie aplikacji.
   * Mitygacja ataków czasowych (timing-attack) przez `verify_dummy_password` dla nieistniejących użytkowników.
   * Obsługa generycznych błędów 500 w standardzie RFC 9457 oraz egzekwowanie kluczy obcych `PRAGMA foreign_keys=ON;` w bazach SQLite.
5. **`tests/test_auth.py`** (120 linii):
   * 6 nowych testów pokrywających: poprawne logowanie, błędne hasło (401), nieistniejącego użytkownika (401), wylogowanie i unieważnienie tokenu (204 i 401), brak tokenu (401), cykl zmiany hasła wraz z kodem 403 i walidacją 422. Łącznie w projekcie: 17/17 testów przechodzi pomyślnie.
