#!/usr/bin/env bash
# 🏰 Waterdeep Watchtower – Główny skrypt uruchomieniowy całej aplikacji
# Umożliwia uruchomienie aplikacji, zasilenie bazy oraz testowanie na żywo.

set -e

project_root_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${project_root_directory}"

launch_mode="standard"
server_host="127.0.0.1"
server_port=8000
force_reseed=false

# Parsowanie parametrów
for command_argument in "$@"; do
    case "${command_argument}" in
        --https)
            launch_mode="https"
            server_port=8443
            ;;
        --dev)
            launch_mode="dev"
            ;;
        --seed)
            force_reseed=true
            ;;
        --seed-only)
            launch_mode="seed_only"
            ;;
        --generator)
            launch_mode="generator_only"
            ;;
        --live)
            launch_mode="live"
            ;;
        --help|-h)
            echo "==========================================================================="
            echo "🏰 Waterdeep Watchtower – Instrukcja Uruchomienia"
            echo "==========================================================================="
            echo "Użycie:"
            echo "  ./run.sh             - Główny start: buduje frontend, sprawdza dane w bazie i"
            echo "                         uruchamia aplikację pod http://localhost:8000"
            echo "  ./run.sh --live      - Uruchamia serwer oraz w tle emulator przesyłający nowe"
            echo "                         pomiary na żywo co 2 sekundy"
            echo "  ./run.sh --generator - Uruchamia w osobnym terminalu emulator czujnika na żywo"
            echo "  ./run.sh --seed      - Uruchamia serwer z wymuszonym ponownym zasileniem danymi"
            echo "  ./run.sh --https     - Uruchamia serwer z szyfrowaniem SSL (port 8443 pod testy E2)"
            echo "  ./run.sh --dev       - Tryb developerski (backend FastAPI + frontend Vite dev server)"
            echo "  ./run.sh --seed-only - Tylko zasila bazę danymi demonstracyjnymi i kończy pracę"
            echo "==========================================================================="
            exit 0
            ;;
        *)
            echo "Nieznana opcja: ${command_argument}. Użyj ./run.sh --help."
            exit 1
            ;;
    esac
done

# Sprawdzenie interpretera Pythona
if [ -d ".venv" ]; then
    python_binary=".venv/bin/python"
    uvicorn_binary=".venv/bin/uvicorn"
elif command -v python3 &>/dev/null; then
    python_binary="python3"
    uvicorn_binary="uvicorn"
else
    echo "❌ Błąd: Nie znaleziono interpretera Pythona."
    exit 1
fi

# Tryb samego generatora (w osobnym oknie terminala)
if [ "${launch_mode}" = "generator_only" ]; then
    "${python_binary}" generator/live_demo.py "http://${server_host}:${server_port}"
    exit 0
fi

# Sprawdzenie i kompilacja frontendu w razie potrzeby
frontend_rebuild_needed=false
if [ ! -f "frontend/dist/index.html" ]; then
    frontend_rebuild_needed=true
elif [ -n "$(find frontend/src -type f -newer frontend/dist/index.html 2>/dev/null)" ]; then
    frontend_rebuild_needed=true
fi

if [ "${frontend_rebuild_needed}" = "true" ] && [ "${launch_mode}" != "dev" ]; then
    echo "📦 Kompilacja minimalistycznego frontendu React SPA..."
    if [ ! -d "frontend/node_modules" ]; then
        (cd frontend && npm install)
    fi
    (cd frontend && npm run build)
    echo "✅ Frontend zbudowany pomyślnie."
fi

# Funkcja weryfikująca, czy baza danych posiada dane demonstracyjne (min. 3 serie, min. 45 wyników)
check_database_needs_seed() {
    "${python_binary}" -c '
from backend.app.database import SessionLocal
from backend.app.models import Measurement, Series
database_session = SessionLocal()
series_count = database_session.query(Series).count()
measurements_count = database_session.query(Measurement).count()
database_session.close()
if series_count < 3 or measurements_count < 45:
    exit(10)
exit(0)
' 2>/dev/null
}

# Obsługa trybu --seed-only
if [ "${launch_mode}" = "seed_only" ]; then
    echo "🌱 Zasilanie bazy danymi demonstracyjnymi..."
    server_already_running=false
    if curl -s -f "http://${server_host}:${server_port}/api/health" &>/dev/null; then
        server_already_running=true
    fi

    if [ "${server_already_running}" = "false" ]; then
        "${uvicorn_binary}" backend.app.main:app --host "${server_host}" --port "${server_port}" &
        temporary_server_process_id=$!
        cleanup_temp_server() {
            kill "${temporary_server_process_id}" 2>/dev/null || true
        }
        trap cleanup_temp_server EXIT INT TERM

        for wait_attempt in $(seq 1 20); do
            if curl -s -f "http://${server_host}:${server_port}/api/health" &>/dev/null; then
                break
            fi
            sleep 0.5
        done
    fi

    "${python_binary}" generator/seed_waterdeep.py "http://${server_host}:${server_port}" admin "HasloAdministratora123!"

    if [ "${server_already_running}" = "false" ]; then
        kill "${temporary_server_process_id}" 2>/dev/null || true
        trap - EXIT INT TERM
    fi
    echo "✅ Zasilenie bazy zakończone sukcesem!"
    exit 0
fi

# Tryb HTTPS – generowanie certyfikatu lokalnego w razie potrzeby
if [ "${launch_mode}" = "https" ]; then
    if [ ! -f "certs/cert.pem" ] || [ ! -f "certs/key.pem" ]; then
        echo "🔐 Generowanie lokalnego certyfikatu SSL..."
        mkdir -p certs
        openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj '/CN=localhost' &>/dev/null
        echo "✅ Certyfikat wygenerowany w katalogu certs/."
    fi
fi

# Uruchomienie serwera
protocol_scheme="http"
if [ "${launch_mode}" = "https" ]; then
    protocol_scheme="https"
fi

echo "🚀 Uruchamianie serwera Waterdeep Watchtower..."
if [ "${launch_mode}" = "https" ]; then
    "${uvicorn_binary}" backend.app.main:app \
        --host "${server_host}" \
        --port "${server_port}" \
        --ssl-keyfile certs/key.pem \
        --ssl-certfile certs/cert.pem \
        --reload &
    server_process_identifier=$!
elif [ "${launch_mode}" = "dev" ]; then
    "${uvicorn_binary}" backend.app.main:app --host "${server_host}" --port "${server_port}" --reload &
    server_process_identifier=$!
    (cd frontend && npm run dev) &
    dev_frontend_process_identifier=$!
else
    "${uvicorn_binary}" backend.app.main:app \
        --host "${server_host}" \
        --port "${server_port}" \
        --reload &
    server_process_identifier=$!
fi

# Rejestracja czyszczenia procesów w tle
generator_process_identifier=""
cleanup_running_processes() {
    echo -e "\n🛑 Zatrzymywanie procesów aplikacji..."
    if [ -n "${generator_process_identifier}" ]; then
        kill "${generator_process_identifier}" 2>/dev/null || true
    fi
    if [ -n "${dev_frontend_process_identifier:-}" ]; then
        kill "${dev_frontend_process_identifier}" 2>/dev/null || true
    fi
    if [ -n "${server_process_identifier:-}" ]; then
        kill "${server_process_identifier}" 2>/dev/null || true
    fi
    echo "🏰 Dziękujemy za służbę w Straży Miejskiej Waterdeep. Serwer zatrzymany."
}
trap cleanup_running_processes EXIT INT TERM

# Oczekiwanie na gotowość serwera API (do 10 sekund)
server_ready=false
for wait_attempt in $(seq 1 20); do
    if curl -s -k -f "${protocol_scheme}://${server_host}:${server_port}/api/health" &>/dev/null; then
        server_ready=true
        break
    fi
    sleep 0.5
done

if [ "${server_ready}" = "false" ]; then
    echo "❌ Błąd: Nie udało się uruchomić serwera API."
    exit 1
fi

# Automatyczne zasilenie bazy danymi demonstracyjnymi, jeśli jest pusta lub wymuszono --seed
database_needs_seed=false
if [ "${force_reseed}" = "true" ]; then
    database_needs_seed=true
elif ! check_database_needs_seed; then
    database_needs_seed=true
fi

if [ "${database_needs_seed}" = "true" ]; then
    echo "🌱 Automatyczne zasilanie bazy danymi przykładowymi Waterdeep (F11)..."
    "${python_binary}" generator/seed_waterdeep.py "${protocol_scheme}://${server_host}:${server_port}" admin "HasloAdministratora123!"
fi

# Tryb pracy na żywo (--live): uruchomienie emulatora w tle
if [ "${launch_mode}" = "live" ]; then
    echo "📡 Uruchamianie emulatora pomiarów na żywo w tle (co 2 sekundy)..."
    "${python_binary}" generator/live_demo.py "${protocol_scheme}://${server_host}:${server_port}" &
    generator_process_identifier=$!
fi

# Baner informacyjny dla użytkownika
echo ""
echo "==========================================================================="
echo "🏰 Waterdeep Watchtower – Punkt Dowodzenia Straży Miejskiej Waterdeep"
echo "==========================================================================="
if [ "${launch_mode}" = "dev" ]; then
    echo "🌐 Interfejs graficzny SPA (Dev): http://localhost:5173"
    echo "📡 Backend API i Swagger:         http://${server_host}:${server_port}/docs"
elif [ "${launch_mode}" = "https" ]; then
    echo "🌐 Interfejs graficzny SPA (HTTPS): https://localhost:${server_port}"
    echo "📡 Dokumentacja API Swagger:       https://localhost:${server_port}/docs"
else
    echo "🌐 Interfejs graficzny SPA:   http://localhost:${server_port}"
    echo "📡 Dokumentacja API Swagger:  http://localhost:${server_port}/docs"
fi
echo "👤 Administrator:             admin / HasloAdministratora123!"
echo "---------------------------------------------------------------------------"
echo "💡 Co możesz teraz zrobić w przeglądarce:"
echo "   1. Otwórz adres powyżej i przeglądaj wykres oraz tabelę (F1, F2)"
echo "   2. Klikaj punkty na wykresie – wiersz w tabeli podświetli się (F6)"
echo "   3. Filtruj serie (checkboxy) oraz zakresy czasu (1h, 24h, własne) (F5)"
echo "   4. Zaloguj się jako administrator, dodaj serię lub zarejestruj czujnik (F3, F8, F12)"
echo "   5. Przetestuj wydruk raportu (Ctrl + P lub przycisk Drukuj) (F7)"
echo "---------------------------------------------------------------------------"
if [ "${launch_mode}" != "live" ]; then
    echo "🚀 Chcesz wysyłać pomiary na żywo? Otwórz drugi terminal i wpisz:"
    echo "   ./run.sh --generator"
    echo "   (albo uruchom aplikację jako: ./run.sh --live)"
fi
echo "🛑 Aby zatrzymać serwer, naciśnij Ctrl + C w tym oknie"
echo "==========================================================================="
echo ""

# Utrzymanie procesu serwera na pierwszym planie
wait "${server_process_identifier}"
