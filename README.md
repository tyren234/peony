# 🏰 Waterdeep Watchtower – System Monitoringu Miasta Waterdeep

Aplikacja telemetryczna IoT do zbierania i wizualizacji danych pomiarowych z sensorów miejskich, realizowana w ramach przedmiotu **Zaawansowane Aplikacje Internetowe (ZAI 26Z)**.

Aplikacja wdraża ścisły kontrakt REST API ([OpenAPI 3.1](docs/zai-api-26z.yaml)) i jest weryfikowana zestawem testów automatycznych ([docs/zai-tests.mjs](docs/zai-tests.mjs)).

---

## 🧙‍♂️ Motyw przewodni: Straż Miejska Waterdeep (Forgotten Realms)

Zamiast standardowych odczytów temperatury, system stanowi punkt dowodzenia Straży Miejskiej Waterdeep i Wieży Blackstaffa, monitorujący stan Miasta Wspaniałości w czasie rzeczywistym.

### Zdefiniowane serie pomiarowe:
1. **Integralność Bariery Ahghairona** *(Ahghairon's Dragonward Integrity)*
   * **Zakres:** `0.0` – `100.0` `%`
   * **Kolor:** `#2563eb` (królewski błękit)
   * **Jednostka:** `%`
   * **Opis:** Stan tarczy magicznej uniemożliwiającej wstęp wrogim smokom do miasta. Kluczowy wskaźnik obronny w skali 0–100%. Spadek poniżej 50% oznacza stan alarmowy dla Wieży Czarodzieja.
2. **Poziom hałasu na Targowisku Głównym** *(The Market Decibels)*
   * **Zakres:** `30.0` – `120.0` `dB`
   * **Kolor:** `#d97706` (bursztynowo-złoty)
   * **Jednostka:** `dB`
   * **Opis:** Akustyka Dzielnicy Handlowej (*Trades Ward*) – od cichego poranka (35 dB) po popołudniowy zgiełk kupców, wozów i bardów (90–110 dB).
3. **Temperatura w piecach Świątyni Gonda** *(Hall of Wonders Foundry)*
   * **Zakres:** `20.0` – `1400.0` `°C`
   * **Kolor:** `#dc2626` (ognista czerwień)
   * **Jednostka:** `°C`
   * **Opis:** Czujniki termiczne w kuźniach alchemicznych i odlewniach cudów techniki kapłanów Gonda.
4. **Niewyjaśnione zdarzenia magiczne** *(Zawirowania Splotu / Weave Surges)*
   * **Zakres:** `0.0` – `50.0` `anomalii/h`
   * **Kolor:** `#8a2be2` (magiczny fiolet)
   * **Jednostka:** `anomalii/h`
   * **Opis:** Czujniki wykrywające nagłe wyładowania dzikiej magii w dzielnicach miasta.
5. **Goście w The Yawning Portal** *(Zaludnienie tawerny)*
   * **Zakres:** `5` – `250` `osób`
   * **Kolor:** `#059669` (szmaragdowy)
   * **Jednostka:** `osób`
   * **Opis:** Liczba awanturników i gości przebywających wokół studni prowadzącej do Podgórza (*Undermountain*).
6. **Otwarte bramy miejskie** *(Stan wrót Waterdeep)*
   * **Zakres:** `0` – `8` `bram`
   * **Kolor:** `#0284c7` (błękit strażniczy)
   * **Jednostka:** `bram`
   * **Opis:** Liczba aktualnie otwartych bram w murach miejskich (Brama Południowa, Rzeczna, Trollowa itp.).

---

## 🛠️ Stos Technologiczny

* **Backend:** Python 3.11+, **FastAPI**, **Pydantic v2** (ścisła walidacja kontraktu i obsługa RFC 9457 Problem Details)
* **Baza Danych:** **SQLAlchemy 2.0** + **SQLite** (lokalnie/kontenery) / **PostgreSQL**
* **Bezpieczeństwo:**
  * Hasła administratora haszowane **Argon2id** (`argon2-cffi`)
  * Klucze sensorów API: generowane kryptograficznie (min. 32 znaki), w bazie przechowywane **wyłącznie jako skrót SHA-256**
  * Uwierzytelnianie tokenami Bearer z unieważnianiem po wylogowaniu
  * Nagłówki: `X-Content-Type-Options: nosniff`, `Content-Security-Policy`
* **Generator Danych:** Narzędzie CLI w Pythonie (F13/T11) emulujące czujniki, przesyłające dane wyłącznie przez API z nagłówkiem `X-API-Key`.
* **Frontend (Etap E2):** **React** + **Vite** + **TypeScript**, wykresy dostępne (WCAG 2.2 AA – rozróżnienie kolorem i kształtem punktu/linii), zsynchronizowana tabela danych, styl wydruku `@media print`.

---

## 🚀 Jak Uruchomić Aplikację

### ⚡ Szybki start jednym poleceniem (Rekomendowane)
Projekt posiada zintegrowany skrypt uruchomieniowy `./run.sh`, który automatycznie weryfikuje środowisko, w razie potrzeby buduje aplikację SPA i uruchamia serwer:
```bash
# Tryb standardowy (aplikacja SPA + API na porcie 8000):
./run.sh

# Tryb bezpieczny HTTPS (na porcie 8443 pod testy E2 z certyfikatem SSL):
./run.sh --https

# Tryb deweloperski (backend FastAPI 8000 + frontend Vite 5173 z hot-reloadem):
./run.sh --dev

# Zasilenie bazy danymi demonstracyjnymi:
./run.sh --seed
```

---

### 1. Przygotowanie środowiska (Virtualenv)
```bash
# Utworzenie i aktywacja wirtualnego środowiska:
python3 -m venv .venv
source .venv/bin/activate

# Instalacja wymaganych zależności:
pip install -r requirements.txt
```

### 2. Uruchomienie serwera backendowego (FastAPI / Uvicorn)

#### Tryb standardowy HTTP (dla Etapu E1 i developmentu):
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Tryb bezpieczny HTTPS (wymóg Etapu E2):
Aplikacja w grupie testów bezpieczeństwa E2 (`[A4]`) wymaga działania po protokole `https://`. Aby uruchomić bezpieczny serwer lokalnie:
```bash
# 1. Wygenerowanie lokalnego certyfikatu deweloperskiego (jeśli jeszcze nie istnieje):
mkdir -p certs && openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj '/CN=localhost'

# 2. Uruchomienie serwera z obsługą SSL na porcie 8443:
uvicorn backend.app.main:app --host 127.0.0.1 --port 8443 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem --reload
```

Aplikacja automatycznie utworzy tabele w bazie SQLite (`waterdeep.db`) i zainicjalizuje domyślne konto administratora:
* **Użytkownik:** `admin`
* **Hasło:** `HasloAdministratora123!`

Dokumentacja interaktywna Swagger UI dostępna jest pod adresem:
* HTTP: [http://localhost:8000/docs](http://localhost:8000/docs)
* HTTPS: [https://localhost:8443/docs](https://localhost:8443/docs)

### 3. Zasilenie bazy danymi przykładowymi (Wymóg F11)
Aby załadować 6 serii miejskich wraz z 20 historycznymi pomiarami dla każdej z nich (wyłącznie za pośrednictwem API):
```bash
python3 generator/seed_waterdeep.py http://127.0.0.1:8000 admin HasloAdministratora123!
```

### 4. Uruchomienie emulatora czujnika (Wymóg F13 / T11)
Generator CLI pozwala na przesyłanie danych na żywo lub wstecz:
```bash
# Przesyłanie pomiarów na żywo co 2 sekundy:
python3 generator/cli.py --api http://localhost:8000 --key TWÓJ_KLUCZ_API --interval 2.0 --mode sine

# Generowanie serii pomiarów z przeszłości:
python3 generator/cli.py --api http://localhost:8000 --key TWÓJ_KLUCZ_API --count 20 --history --step-minutes 15
```

---

## 📡 Opis Endpointów API Według Serwisów

Wszystkie ścieżki posiadają prefiks `/api`. Odpowiedzi błędów zwracane są zgodnie ze standardem **RFC 9457 Problem Details** (`application/problem+json`).

### 1. Serwis Systemowy (`/api/health`)
| Metoda | Ścieżka | Dostęp | Kody odpowiedzi | Opis |
|---|---|:---:|:---:|---|
| `GET` | `/api/health` | Publiczny | `200` | Liveness/Readiness probe. Zwraca `{"status": "ok"}`. Służy do wybudzania aplikacji w chmurze. |

---

### 2. Serwis Uwierzytelniania (`/api/auth`)
| Metoda | Ścieżka | Dostęp | Kody odpowiedzi | Opis |
|---|---|:---:|:---:|---|
| `POST` | `/api/auth/login` | Publiczny | `200`, `400`, `401` | Logowanie administratora. Zwraca token Bearer (`accessToken`), typ oraz czas ważności w sekundach (`expiresIn`). |
| `POST` | `/api/auth/logout` | `Bearer Token` | `204`, `401` | Wylogowanie. Unieważnia przekazany token (natychmiast przestaje działać w bazie). |
| `PUT` | `/api/auth/password` | `Bearer Token` | `204`, `400`, `401`, `403` | Zmiana hasła zalogowanego administratora. Wymaga podania poprawnego `currentPassword` oraz `newPassword` (min. 8 znaków). |

---

### 3. Serwis Serii Pomiarowych (`/api/series`)
| Metoda | Ścieżka | Dostęp | Kody odpowiedzi | Opis |
|---|---|:---:|:---:|---|
| `GET` | `/api/series` | Publiczny | `200`, `406` | Zwraca tablicę wszystkich zdefiniowanych serii (wraz z kolorem, zakresem min/max, ikoną i jednostką). |
| `POST` | `/api/series` | `Bearer Token` | `201`, `400`, `401`, `415`, `422` | Tworzy nową serię pomiarową. Zwraca nagłówek `Location: /api/series/{id}`. Wymaga `minValue < maxValue`. |
| `GET` | `/api/series/{seriesId}` | Publiczny | `200`, `404` | Odczyt metadanych konkretnej serii. |
| `PUT` | `/api/series/{seriesId}` | `Bearer Token` | `200`, `400`, `401`, `404`, `409`, `422` | Pełna aktualizacja serii. Jeśli nowy zakres `[minValue, maxValue]` wyklucza zapisane już wyniki, serwer zwraca **409 Conflict**. |
| `DELETE`| `/api/series/{seriesId}` | `Bearer Token` | `204`, `401`, `404` | Usuwa serię kaskadowo wraz ze wszystkimi przypisanymi czujnikami i zarejestrowanymi pomiarami. |

---

### 4. Serwis Czujników IoT (`/api/sensors`)
| Metoda | Ścieżka | Dostęp | Kody odpowiedzi | Opis |
|---|---|:---:|:---:|---|
| `GET` | `/api/sensors` | `Bearer Token` | `200`, `401` | Lista zarejestrowanych czujników (zwracana **bez** kluczy API ani ich skrótów). |
| `POST` | `/api/sensors` | `Bearer Token` | `201`, `400`, `401`, `415`, `422` | Rejestracja czujnika dla podanej `seriesId`. Zwraca jednorazowo wygenerowany klucz API (`apiKey`, min. 32 znaki) oraz nagłówek `Location`. |
| `GET` | `/api/sensors/{sensorId}` | `Bearer Token` | `200`, `401`, `404` | Odczyt danych czujnika (bez klucza API). |
| `DELETE`| `/api/sensors/{sensorId}` | `Bearer Token` | `204`, `401`, `404` | Wyrejestrowanie czujnika. Klucz API natychmiast przestaje działać, jednak zebrane dotąd wyniki pomiarowe **pozostają w bazie**. |

---

### 5. Serwis Wyników Pomiarów (`/api/measurements`)
| Metoda | Ścieżka | Dostęp | Kody odpowiedzi | Opis |
|---|---|:---:|:---:|---|
| `POST` | `/api/measurements` | `X-API-Key` | `201`, `400`, `401`, `415`, `422` | Przesłanie wyniku z czujnika. Seria wynika z klucza w nagłówku `X-API-Key`. Wartość poza `[minValue, maxValue]` lub czas z przyszłości (> 5 min) skutkuje kodem **422**. Zwraca `Location`. |
| `GET` | `/api/measurements` | Publiczny | `200`, `400` | Pobranie wyników z opcjonalnymi parametrami: `series` (np. `1,3`), `from`, `to`, `sort` (`timestamp` lub `-timestamp`), `limit` (1-10000). |
| `GET` | `/api/measurements/{id}` | Publiczny | `200`, `404` | Odczyt pojedynczego wyniku pomiaru. |
| `PUT / PATCH / DELETE` | `/api/measurements/{id}` | *Zablokowane* | `404` / `405` | Wyniki pomiarów są niezmiennicze (immutability) – nie można ich edytować ani usuwać pojedynczo. |

---

## 🧪 Testy i Weryfikacja

### Testy automatyczne Pytest
Projekt posiada pełny zestaw testów jednostkowych i integracyjnych pokrywających walidację, błędy RFC 9457 oraz bezpieczeństwo:
```bash
pytest -v
```

### Oficjalny skrypt sprawdzający kontrakt (ZAI 26Z)

#### Weryfikacja Etapu E1 (wymóg 10 pkt – serwer na porcie 8000):
```bash
node docs/zai-tests.mjs --app http://localhost:8000 --user admin --pass 'HasloAdministratora123!' --stage E1
```

#### Weryfikacja Etapu E2 (wymóg HTTPS & CSP – serwer na porcie 8443):
```bash
NODE_TLS_REJECT_UNAUTHORIZED=0 node docs/zai-tests.mjs --app https://localhost:8443 --user admin --pass 'HasloAdministratora123!' --stage E2
```

> **Dlaczego flaga `NODE_TLS_REJECT_UNAUTHORIZED=0` przy testach lokalnych?**  
> W środowisku lokalnym używamy certyfikatu podpisanego własnoręcznie (`self-signed`), więc Node.js domyślnie odrzuciłby go jako niezaufany. Flaga instruuje Node.js, aby zaufał lokalnemu certyfikatowi. Na serwerze produkcyjnym (np. Render / Fly.io / VPS z zaufanym Let's Encrypt) flaga ta nie jest potrzebna.

---

## 📋 Plan Działania

### Etap E1: Wdrożone API (Termin: 7 listopada 2026 – 10 pkt) – ✅ ZREALIZOWANE LOKALNIE
* Pełna implementacja kontraktu OpenAPI 3.1 w FastAPI.
* Baza danych SQLite z relacjami, indeksami po czasie i kaskadami.
* Bezpieczeństwo: Argon2id, SHA-256 dla kluczy API, Bearer tokeny, nagłówki `nosniff`, `CSP`.
* Generator danych CLI (F13/T11) oraz skrypt zasilający 6 serii po 20 pomiarów (F11).
* Zaliczenie 100% testów automatycznych etapu E1 (10/10 pkt).

### Etap E2: Aplikacja Końcowa (Termin: 21 listopada 2026 – 40 pkt + bonusy)
1. **Frontend React SPA:** Responsywny interfejs, interaktywny wykres + tabela powiązana z wykresem (F6), filtry czasu i serii (F5), panel administratora (F3, F8, F12).
2. **Dostępność i Wydruk:** WCAG 2.2 AA (Lighthouse Accessibility >= 90 pkt), czysty wydruk `@media print` (F7).
3. **Punkty dodatkowe:** WebSockets/SSE na żywo (+3 pkt), CI GitHub Actions (+2 pkt), TimescaleDB (+3 pkt).
