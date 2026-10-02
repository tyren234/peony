# 🏰 Waterdeep Watchtower – System Monitoringu Miasta Waterdeep

Aplikacja telemetryczna IoT do zbierania i wizualizacji danych pomiarowych z sensorów miejskich, realizowana w ramach przedmiotu **Zaawansowane Aplikacje Internetowe (ZAI 26Z)**.

Aplikacja wdraża ścisły kontrakt REST API ([OpenAPI 3.1](docs/zai-api-26z.yaml)) i jest weryfikowana zestawem testów automatycznych ([docs/zai-tests.mjs](docs/zai-tests.mjs)).

---

## 🧙‍♂️ Motyw przewodni: Straż Miejska Waterdeep (Forgotten Realms)

Zamiast standardowych odczytów temperatury, system stanowi punkt dowodzenia Straży Miejskiej Waterdeep i Wieży Blackstaffa, monitorujący stan Miasta Wspaniałości w czasie rzeczywistym.

### Główne serie pomiarowe:
1. **Niewyjaśnione zdarzenia magiczne** *(Zawirowania Splotu / Weave Surges)*
   * **Zakres:** `0.0` – `50.0` `anomalii/h`
   * **Kolor:** `#8a2be2` (magiczny fiolet)
   * **Opis:** Czujniki wykrywające nagłe wyładowania dzikiej magii w dzielnicach miasta.
2. **Goście w The Yawning Portal** *(Zaludnienie tawerny)*
   * **Zakres:** `5` – `250` `osób`
   * **Kolor:** `#d97706` (bursztynowy)
   * **Opis:** Liczba awanturników i gości przebywających wokół studni prowadzącej do Podgórza (Undermountain).
3. **Otwarte bramy miejskie** *(Stan wrót Waterdeep)*
   * **Zakres:** `0` – `8` `bram`
   * **Kolor:** `#0284c7` (błękit strażniczy)
   * **Opis:** Liczba aktualnie otwartych bram w murach miejskich (Brama Południowa, Rzeczna, Trollowa itp.).
4. *(Rezerwowa)* **Aktywność w Podgórzu** *(Drgania podziemi Halastera)*
   * **Zakres:** `0.0` – `10.0` `w skali Blackstaffa`
   * **Kolor:** `#dc2626` (czerwień alarmowa)

---

## 🛠️ Stos Technologiczny

* **Backend:** Python 3.11+, **FastAPI**, **Pydantic v2** (ścisła walidacja kontraktu i obsługa RFC 9457 Problem Details)
* **Baza Danych:** **SQLAlchemy 2.0** + **SQLite** (lokalnie/kontenery) / **PostgreSQL**
* **Bezpieczeństwo:**
  * Hasła haszowane **Argon2id** (`argon2-cffi`)
  * Klucze sensorów API: generowane kryptograficznie (min. 32 znaki), w bazie przechowywane **wyłącznie jako skrót SHA-256**
  * Uwierzytelnianie tokenami Bearer z unieważnianiem po wylogowaniu
  * Nagłówki: `X-Content-Type-Options: nosniff`, `Content-Security-Policy`
* **Generator Danych:** Narzędzie CLI w Pythonie (F13/T11) emulujące czujniki, przesyłające dane wyłącznie przez API z nagłówkiem `X-API-Key`.
* **Frontend (Etap E2):** **React** + **Vite** + **TypeScript**, wykresy dostępne (WCAG 2.2 AA – rozróżnienie kolorem i kształtem punktu/linii), zsynchronizowana tabela danych, styl wydruku `@media print`.

---

## 📋 Plan Działania i Kolejność Realizacji

### Etap E1: Wdrożone API (Termin: 7 listopada 2026 – 10 pkt)
1. **Struktura i baza danych:**
   * Inicjalizacja projektu, schemat tabel SQL (`users`, `series`, `sensors`, `measurements`) z indeksami po czasie.
   * Obsługa haszowania Argon2id oraz skrótów SHA-256 dla kluczy API.
2. **Implementacja kontraktu OpenAPI 3.1:**
   * `/api/health` – endpoint liveness/readiness (`{"status":"ok"}`).
   * `/api/auth/login`, `/api/auth/logout`, `/api/auth/password` – zarządzanie sesją administratora.
   * `/api/series` (CRUD) – tworzenie z nagłówkiem `Location`, blokada zawężenia przedziału wykluczającego dane (kod 409 Conflict), kaskadowe usuwanie powiązanych czujników i pomiarów.
   * `/api/sensors` – rejestracja sensora z jednorazowym kluczem API, unieważnianie klucza przy wyrejestrowaniu bez usuwania danych historycznych.
   * `/api/measurements` – przyjmowanie pomiarów z `X-API-Key` (walidacja min/max i czasu serwera), filtrowany i sortowany odczyt publiczny.
3. **Obsługa błędów RFC 9457:**
   * Wszystkie odpowiedzi błędów jako `application/problem+json` z polami `title`, `status`, `detail`, `errors`.
   * Kody: 400 (składnia), 401 (brak/zły token/klucz), 403 (błędne hasło bieżące), 404 (brak zasobu), 406 (nieobsługiwany Accept), 409 (konflikt przedziału), 415 (zły Content-Type), 422 (błąd semantyczny / poza zakresem).
4. **Generator danych i dane początkowe:**
   * Skrypt CLI w Pythonie (`generator/cli.py`) do generowania danych na żywo i historycznych.
   * Skrypt zasilający (`seed_waterdeep.py`) wprowadzający min. 3 serie po min. 15 pomiarów (wymóg F11).
5. **Weryfikacja lokalna i wdrożenie chmurowe:**
   * Testy skryptem `node docs/zai-tests.mjs --stage E1`.
   * Publiczne wdrożenie z HTTPS (Render / Fly.io / VPS).

### Etap E2: Aplikacja Końcowa (Termin: 21 listopada 2026 – 40 pkt + bonusy)
1. **Frontend React SPA:**
   * Interfejs responsywny (Flexbox/Grid, od 360 px wzwyż).
   * Interaktywny wykres + tabela powiązana z wykresem (kliknięcie rekordu podświetla punkt – F6).
   * Filtrowanie przedziału czasu i wybór widocznych serii (F5).
   * Panel administratora do konfiguracji serii i sensorów (F3, F8, F12).
2. **Dostępność i Wydruk:**
   * Spełnienie kryteriów WCAG 2.2 AA (Lighthouse Accessibility >= 90 pkt – T6/A5).
   * Czysty wydruk z zachowaniem wykresu i tabeli bez kontrolek (`@media print` – F7/T7).
3. **Punkty Dodatkowe (do 10 pkt):**
   * Wykres na żywo przez WebSockets / SSE (+3 pkt).
   * Automatyczne testy w CI (GitHub Actions) (+2 pkt).
   * Integracja z bazą szeregów czasowych (TimescaleDB) (+3 pkt).
4. **Oddanie projektu:**
   * Nagranie demonstracyjne MP4 (5-7 min) z prezentacją wymagań F1-F13.
   * Raport dokumentacyjny PDF (do 8 stron) z diagramem ERD.

---

## 🧪 Uruchomienie Testów Automatycznych

```bash
# Uruchomienie testów dla etapu E1 lokalnie:
node docs/zai-tests.mjs --app http://localhost:8000 --user admin --pass 'HasloAdministratora123!' --stage E1

# Uruchomienie pełnych testów etapu E2 z audytem Lighthouse:
node docs/zai-tests.mjs --app https://twoja-aplikacja.example.com --user admin --pass 'HasloAdministratora123!' --stage E2 --lighthouse
```
