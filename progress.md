# 🏰 Waterdeep Watchtower – Rejestr Postępów Realizacji (ZAI 26Z)

> **Zasada pracy:** Małe, czytelne kroki (do ~100–300 linii kodu na krok), dokładny review każdego etapu przed przejściem dalej.  
> **Aktualny stan:** Krok 2 ukończony – oczekuje na review.

---

## 🗺️ Plan Małych Kroków (Etap E1)

| Krok | Zakres | Rozmiar | Status | Opis |
|:---:|---|:---:|:---:|---|
| **Krok 1** | **Fundament:** Konfiguracja, Połączenie SQLite i endpoint `/api/health` | ~97 linii | ✅ **ZATWIERDZONY** | Środowisko, pydantic-settings, silnik SQLite z obsługą kluczy obcych, aplikacja FastAPI, nagłówek nosniff |
| **Krok 2** | **Modele SQL:** Tabele bazy danych | ~80 linii | 🔍 **GOTOWE DO REVIEW** | Modele SQLAlchemy: `users`, `user_tokens`, `series`, `sensors`, `measurements` z indeksami |
| **Krok 3** | **Bezpieczeństwo & RFC 9457:** Haszowanie i obsługa błędów | ~140 linii | ⏹️ Oczekuje | Haszowanie haseł Argon2id, klucze API SHA-256, format błędów `application/problem+json` |
| **Krok 4** | **Autoryzacja (`/api/auth`):** Zarządzanie sesją | ~120 linii | ⏹️ Oczekuje | Endpointy `/login`, `/logout`, `/password`, Bearer tokeny, unieważnianie sesji |
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
