# 🏰 Waterdeep Watchtower – Rejestr Postępów Realizacji (Etap E2)

> **Zasada pracy:** Małe, czytelne kroki (do ~100–300 linii kodu na krok), dokładny review każdego etapu przed przejściem dalej.
> **Zasada czystego kodu i nazewnictwa:** Bezwzględny zakaz stosowania jednoliterowych skrótów i niejasnych akronimów w nazwach zmiennych. Czytelność i pełne, samoopisujące się nazwy są priorytetem.
> **Język:** Komunikaty API i błędy po angielsku. Interfejs użytkownika z klimatem Forgotten Realms / Waterdeep.
> **Status bazowy:** Etap E1 zakończony w 100% (10/10 pkt). Przechodzimy do Etapu E2 (Frontend React SPA, Dostępność WCAG 2.2 AA, Bezpieczeństwo i Funkcje Bonusowe).

---

## 🗺️ Plan Małych Kroków (Etap E2)

| Krok | Zakres | Cel | Status | Opis |
|:---:|---|:---:|:---:|---|
| **Krok E2.1** | **Backend Bezpieczeństwo & CSP:** Nagłówek CSP, endpoint `GET /` i obsługa HTTPS | A4 (3 pkt) | ✅ **ZATWIERDZONY** | Dodanie nagłówka `Content-Security-Policy`, endpointu `GET /` serwującego HTML, obsługa lokalnego/produkcyjnego HTTPS (100% testów A4 zdanych!) |
| **Krok E2.2** | **Inicjalizacja Frontendu:** React + Vite + TypeScript | Fundament | ✅ **ZATWIERDZONY** | Projekt SPA w `frontend/`, typy domenowe, moduł `api.ts`, integracja serwowania w FastAPI |
| **Krok E2.3** | **Dostępność i Układ:** WCAG 2.2 AA & RWD (~360px) | A5 (3 pkt), B2 | ✅ **ZATWIERDZONY** | Semantyczny HTML, etykiety formularzy, kontrast >= 4.5:1, responsywność do 360px |
| **Krok E2.4** | **Wizualizacja Danych:** Wykres i Tabela z Synchronizacją | F2, F6 | ✅ **ZATWIERDZONY** | Minimalistyczny wykres SVG z kształtami i kolorami, dwukierunkowa synchronizacja wykres <-> tabela |
| **Krok E2.5** | **Filtrowanie Danych:** Filtry Serii i Zakresów Czasu | F5 | ✅ **ZATWIERDZONY** | Wybór serii (checkboxy), zakres `from`/`to`, szybkie filtry czasowe (1h, 24h, wszystko) |
| **Krok E2.6** | **Panel Administratora:** CRUD Serii i Czujników | F3, F8, F12 | ✅ **ZATWIERDZONY** | Logowanie Bearer, tworzenie/usuwanie serii (min < max), rejestracja z jednorazowym kluczem API, unregister |
| **Krok E2.7** | **Wydruk Raportu:** Stylizacja `@media print` | F7, B2 | ✅ **ZATWIERDZONY** | Czysty wydruk raportu z ukrytymi kontrolkami i formularzami |
| **Krok E2.8** | **Bonusy:** WebSockets (+3 pkt), CI GitHub Actions (+2 pkt) & Pogoda (+2 pkt) | Bonus (+7 pkt) | 🔄 W TRAKCIE | Zrealizowano WebSocket na żywo (+3 pkt) oraz GitHub Actions CI (+2 pkt). W trakcie: tryb Open-Meteo (+2 pkt). |
| **Krok E2.9** | **Weryfikacja Końcowa:** Pełny audyt testów i dokumentacja | E2 (40 pkt + bonus) | ⏹️ Oczekuje | Uruchomienie `node docs/zai-tests.mjs --stage E2 --lighthouse`, nagranie demonstracyjne, dokumentacja PDF |

---

## 🔍 Szczegółowe Wymagania Etapu E2 (Specyfikacja ZAI 26Z)

### 1. Część Automatyczna (A1–A5: 16 pkt)
* **A1/A2 (6 pkt) – Kontrakt API:**
  * Już zrealizowany w 100% w etapie E1.
* **A3 (4 pkt) – Walidacja i Autoryzacja:**
  * Już zrealizowany w 100% (blokady 422, 401, 404/405, RFC 9457).
* **A4 (3 pkt) – Bezpieczeństwo:**
  * Działanie przez HTTPS i przekierowanie z HTTP (lub port 80 zamknięty).
  * Nagłówek `Content-Security-Policy` dla strony głównej `GET /`.
  * `X-Content-Type-Options: nosniff` (zrealizowany).
  * Flagi ciasteczek `HttpOnly`, `Secure`, `SameSite` (zrealizowany).
  * Brak wycieku haseł i kluczy API (zrealizowany).
  * Ograniczenie CORS (zrealizowany).
  * Brak stack trace w odpowiedziach błędów (zrealizowany).
* **A5 (3 pkt) – Dostępność (Lighthouse Accessibility):**
  * Wynik Lighthouse Accessibility dla strony głównej >= 90 pkt (3 pkt), 80–89 pkt (2 pkt), 70–79 pkt (1 pkt).

### 2. Część B (24 pkt – ocena funkcjonalności przez nagranie i listę kontrolną)
* **B1 (13 pkt) – Wymagania F1–F13 w interfejsie:**
  * F1: Wynik pomiaru jako float, timestamp i seria.
  * F2: Serie na wykresie i w tabeli (osobna kolumna, osobna krzywa).
  * F3: Role czytelnik (przeglądanie) vs administrator (zarządzanie).
  * F4: Walidacja zakresu w formularzach i czytelne komunikaty błędów.
  * F5: Filtry serii i czasu.
  * F6: Synchronizacja interakcji wykres <-> tabela.
  * F7: Wydruk `@media print`.
  * F8: Zarządzanie seriami (CRUD).
  * F9: Widok mobilny (~360px).
  * F10: Prezentacja danych telemetrycznych w czasie rzeczywistym.
  * F11: Dane przykładowe (min. 3 serie x 15 wyników).
  * F12: Zarządzanie czujnikami (rejestracja z jednorazowym kluczem, lista, usuwanie).
  * F13: Generator danych CLI.
* **B2 (4 pkt) – Widok mobilny (~360px) oraz wydruk bez kontrolek.**
* **B3 (3 pkt) – Dwa elementy bezpieczeństwa (Argon2id, SHA-256 kluczy API, CSP, Bearer).**
* **B4 (2 pkt) – Diagram ERD i skrypt bazy danych.**
* **B5 (2 pkt) – Dokumentacja PDF (do 8 stron).**

### 3. Punkty Dodatkowe (do 10 pkt)
* Aktualizacja wykresu w czasie rzeczywistym (WebSocket / SSE): **+3 pkt**
* Generator pobierający dane z publicznego API pogodowego: **+2 pkt**
* Testy automatyczne w GitHub Actions CI: **+2 pkt**
* Baza szeregów czasowych: **+3 pkt**

---

## 🔍 Krok E2.1 – Szczegóły Zrealizowanego Kodu (Bezpieczeństwo & CSP)

Pliki w repozytorium zmodyfikowane w ramach Kroku E2.1:

1. **`backend/app/main.py`**:
   * Dodano globalny nagłówek `Content-Security-Policy` w middleware bezpieczeństwa (`api_headers_and_security_middleware`).
   * Zaimplementowano endpoint `GET /` zwracający semantyczny dokument HTML (kod 200) przygotowany jako punkt wejścia pod aplikację React SPA.
2. **`tests/test_health.py`**:
   * Dodano test `test_home_page_endpoint` weryfikujący kod 200, nagłówek `Content-Security-Policy`, `X-Content-Type-Options: nosniff` oraz poprawność struktury HTML.
3. **Konfiguracja środowiska HTTPS**:
   * Dodano ignorowanie certyfikatów SSL (`certs/`, `*.pem`) w `.gitignore`.
   * Skrypt weryfikacyjny z certyfikatami SSL i uvicorn na porcie 8443 pomyślnie zalicza wszystkie testy bezpieczeństwa grupy `[A4]` w `docs/zai-tests.mjs`.
4. **Wyniki testów**:
   * Pytest: **96/96 testów przechodzi pomyślnie** (0 warnings).
   * Skrypt prowadzącego `docs/zai-tests.mjs --stage E2`:
     * `[A1/A2] kontrakt`: **6 / 6 pkt** (100%)
     * `[A3] walidacja`: **4 / 4 pkt** (100%)
     * `[A4] bezpieczenstwo`: **3 / 3 pkt** (100%)
     * Łącznie: **13 / 13 pkt** (maksimum punktów przed wdrożeniem interfejsu dla Lighthouse A5).

---

## 🔍 Krok E2.2 – Szczegóły Zrealizowanego Kodu (Inicjalizacja Frontendu)

Pliki w repozytorium utworzone/zmodyfikowane w ramach Kroku E2.2:

1. **Struktura projektu `frontend/`**:
   * Utworzono aplikację React 19 + TypeScript + Vite.
   * Skonfigurowano proxy dev servera (`frontend/vite.config.ts`) przekierowujące ścieżki `/api` do lokalnego serwera FastAPI (`http://127.0.0.1:8000`).
   * Zaktualizowano metadane w `frontend/index.html` (język `pl`, semantyczny tytuł i opis punktu dowodzenia Waterdeep Watchtower).
2. **Definicje typów domenowych (`frontend/src/types.ts`)**:
   * Modele TypeScript: `SeriesItem`, `MeasurementItem`, `SensorItem`, `SensorCreatedResponse`, `LoginResponse`, `TelemetryFilterCriteria`, `ProblemDetailsError`.
3. **Moduł klienta API (`frontend/src/services/api.ts`)**:
   * Funkcje obsługujące komunikację REST API: `fetchAllSeries`, `fetchMeasurements` (z filtrowaniem serii, zakresów czasu i sortowania), `loginAdministrator`, `logoutAdministrator`, `fetchSensors`, CRUD serii (`createSeries`, `updateSeries`, `deleteSeries`) oraz czujników (`registerSensor`, `unregisterSensor`).
4. **Serwowanie aplikacji SPA w FastAPI (`backend/app/main.py`)**:
   * Podpięto automatyczne montowanie skompilowanych zasobów `/assets` z `frontend/dist`.
   * Endpoint `GET /` serwuje wygenerowany plik `dist/index.html` (lub awaryjny HTML) z nagłówkami `Content-Security-Policy` i `X-Content-Type-Options: nosniff`.
5. **Weryfikacja**:
   * `npm run build` kompiluje TypeScript i paczkę produkcyjną bez żadnych ostrzeżeń.
   * Wszystkie 96 testów pytest przechodzi w 100%.

---

## 🔍 Kroki E2.3–E2.7 – Szczegóły Zrealizowanego Kodu (Minimalistyczny Frontend SPA)

Pliki w repozytorium utworzone/zmodyfikowane:

1. **`frontend/src/components/TelemetryChart.tsx`** (~220 linii):
   * Czysty, lekki komponent SVG bez zewnętrznych ciężkich bibliotek wykresów.
   * **Dostępność WCAG 2.2 AA (F2, T6)**: Każda seria rozróżniana jest kolorem oraz unikalnym geometrycznym **kształtem punktu** (koło, kwadrat, trójkąt, romb).
   * Punkty posiadają etykiety `aria-label`, są w pełni dostępne z klawiatury (`tabIndex={0}`, Enter / Spacja) i posiadają widoczny stan zaznaczenia.
2. **`frontend/src/components/TelemetryTable.tsx`** (~100 linii):
   * Tabela danych telemetrycznych z przewijanym widokiem i lepkimi nagłówkami (`sticky header`).
   * **Synchronizacja (F6)**: Kliknięcie wiersza zaznacza punkt na wykresie. Kliknięcie punktu na wykresie podświetla powiązany wiersz i automatycznie przewija go do widoku (`scrollIntoView`).
3. **`frontend/src/components/AdminPanel.tsx`** (~320 linii):
   * Minimalistyczny panel administracyjny (F3, F8, F12).
   * Bezpieczne logowanie Bearer tokenem (`POST /api/auth/login`) zapamiętywanym w `sessionStorage`.
   * Formularz nowej serii z walidacją `minValue < maxValue` (F4) oraz usuwanie serii kaskadowo z potwierdzeniem.
   * Rejestracja czujników z jednorazowym, bezpiecznym podglądem wygenerowanego klucza API w ramce ostrzegawczej.
   * Lista zarejestrowanych czujników z czasem ostatniego pomiaru oraz wyrejestrowaniem (204).
4. **`frontend/src/App.tsx`** (~190 linii):
   * Główny koordynator aplikacji integrujący filtry serii, dat `from`/`to`, przyciski szybkiego zakresu (1h, 24h, wszystko) oraz przycisk drukowania.
5. **`frontend/src/index.css`** (~380 linii):
   * Minimalistyczny, estetyczny arkusz stylów oparty na systemowych krojach pisma.
   * Wysoki kontrast tekstu spełniający normę WCAG 2.2 AA (kontrast > 4.5:1).
   * Responsywność mobilna dla ekranów o szerokości od 360 px (brak poziomego paska przewijania).
   * Reguły `@media print` ukrywające przyciski, formularze i kontrolki filtrowania dla czystego wydruku raportu pomiarów (F7, B2).
6. **Standardy jakości**:
   * **Zero jednoliterowych zmiennych** w całym kodzie źródłowym TypeScript/CSS/Python.
   * Wszystkie 96 testów pytest przechodzi w 100%.

---

## 🔍 Krok E2.8 – Transmisja Telemetrii na Żywo (WebSocket +3 pkt)

1. **`backend/app/websocket_manager.py`**:
   * Zaimplementowano moduł `TelemetryBroadcaster` zarządzający pulą aktywnych klientów WebSocket.
   * Każdy nowy pomiar zapisany w `POST /api/measurements` jest asynchronicznie rozsyłany do wszystkich połączonych klientów.
2. **`backend/app/main.py`**:
   * Dodano endpoint WebSocket `GET /ws/telemetry`.
   * Nagłówek CSP zezwala na bezpieczne połączenia `connect-src ws: wss:`.
3. **`frontend/src/App.tsx` & `frontend/src/index.css`**:
   * Frontend automatycznie nawiązuje połączenie WebSocket `ws://` / `wss://`.
   * Nowe pomiary z emulatora trafiają bezpośrednio na wykres i do tabeli bez konieczności odświeżania.
   * Naprawiono limit zapytań (zwiększono do 2000 z sortowaniem `-timestamp`), dzięki czemu przycisk "Odśwież" zawsze pobiera najświeższe odczyty.
   * Dodano wskaźnik `🟢 Na żywo (WebSocket)`, czas ostatniej aktualizacji oraz opcję awaryjnego auto-odpytywania (4s).

4. **`github/workflows/ci.yml` (Bonus +2 pkt)**:
   * Trzyetapowy pipeline CI uruchamiany przy pushu i pull requeście:
     * `backend-unit-and-integration-tests`: testy `pytest -v` na macierzy Python 3.11 i 3.12 (96/96 testów zdanych).
     * `frontend-build-and-typecheck`: kompilacja `tsc -b && vite build` na Node.js 20.
     * `contract-and-e2e-verification`: uruchomienie serwera API, zasilenie danymi i weryfikacja testami `zai-tests.mjs --stage E1`.
