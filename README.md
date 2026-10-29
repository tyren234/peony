# 🏰 Waterdeep Watchtower – System Telemetrii IoT

Aplikacja do zbierania, analizy i wizualizacji pomiarów telemetrycznych w czasie rzeczywistym z miejskich czujników (projekt ZAI 26Z, motyw Straży Miejskiej Waterdeep).

---

## 🌐 Wdrożenie i Dostęp

* **Aplikacja w chmurze (Azure):** [https://waterdeep-watchtower-dvhshwbba8dvg4en.swedencentral-01.azurewebsites.net](https://waterdeep-watchtower-dvhshwbba8dvg4en.swedencentral-01.azurewebsites.net)
* **Status CI (GitHub Actions):** [https://github.com/tyren234/peony/actions](https://github.com/tyren234/peony/actions)
* **Konto administratora:**
  * Login: `admin`
  * Hasło: `HasloAdministratora123!`
* **Schemat bazy danych:** [`docs/schema.sql`](docs/schema.sql)

---

## ⚡ Szybki Start Lokalny

Projekt posiada zintegrowany skrypt uruchomieniowy `./run.sh` (automatycznie konfiguruje środowisko, buduje frontend i sprawdza bazę danych):

```bash
# Główny start (kompletna aplikacja SPA + API pod http://localhost:8000):
./run.sh

# Tryb na żywo (aplikacja + emulator przesyłający nowe pomiary w tle co 30s):
./run.sh --live

# Tryb deweloperski (FastAPI backend :8000 + Vite dev server :5173):
./run.sh --dev
```

---

## 🛠️ Architektura i Technologie

* **Backend:** Python 3.14, **FastAPI**, **Pydantic v2** (pełna zgodność z OpenAPI 3.1 i RFC 9457 Problem Details).
* **Baza danych:** **SQLAlchemy 2.0** + **SQLite** / **PostgreSQL** (klucze obce, kaskady, indeksy czasowe).
* **Frontend:** **React 19**, **TypeScript**, **Vite** – dostępność WCAG 2.2 AA (rozróżnienie serii kolorem i kształtem punktu, Lighthouse 100/100, RWD ~360px, czysty wydruk `@media print`).
* **Real-time:** Transmisja na żywo przez **WebSocket** (`/ws/telemetry`) z możliwością włączania/wyłączania w interfejsie.
* **Bezpieczeństwo:**
  * Hasła haszowane **Argon2id** (`argon2-cffi`) z ochroną przed timing-attacks.
  * Klucze czujników (min. 32 znaki) zapisywane w bazie **wyłącznie jako skrót SHA-256**.
  * Sesja tokenami Bearer z unieważnianiem przy wylogowaniu.
  * Nagłówki `Content-Security-Policy` oraz `X-Content-Type-Options: nosniff`.

---

## 🧪 Testy i Weryfikacja

### 1. Testy jednostkowe i integracyjne (Backend)
```bash
pytest -v
```

### 2. Weryfikacja oficjalnym skryptem prowadzącego (`zai-tests.mjs`)

```bash
# Test Etapu E1 (Kontrakt & Walidacja):
node docs/zai-tests.mjs --app https://waterdeep-watchtower-dvhshwbba8dvg4en.swedencentral-01.azurewebsites.net --user admin --pass 'HasloAdministratora123!' --stage E1

# Test Etapu E2 (Bezpieczeństwo, Kontrakt, Dostępność):
node docs/zai-tests.mjs --app https://waterdeep-watchtower-dvhshwbba8dvg4en.swedencentral-01.azurewebsites.net --user admin --pass 'HasloAdministratora123!' --stage E2
```

---

## 📡 Emulator i Generator Czujników CLI (F13)

```bash
# Pomiary w czasie rzeczywistym co 2 sekundy (sinusoida):
python3 generator/cli.py --api http://localhost:8000 --key TWÓJ_KLUCZ_API --interval 2.0 --mode sine

# Zasilenie historii pomiarów z przeszłości:
python3 generator/cli.py --api http://localhost:8000 --key TWÓJ_KLUCZ_API --count 20 --history --step-minutes 15
```
