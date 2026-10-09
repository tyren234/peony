#!/usr/bin/env bash
# 🏰 Waterdeep Watchtower – Skrypt uruchomieniowy całej aplikacji

set -e

project_root_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${project_root_directory}"

launch_mode="standard"
server_host="127.0.0.1"
server_port=8000

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
            launch_mode="seed_only"
            ;;
        --help|-h)
            echo "🏰 Waterdeep Watchtower – Pomoc"
            echo "Użycie:"
            echo "  ./run.sh          - Uruchamia serwer produkcyjny ze zintegrowanym frontendem (HTTP port 8000)"
            echo "  ./run.sh --https  - Uruchamia serwer z szyfrowaniem SSL (HTTPS port 8443 pod testy E2)"
            echo "  ./run.sh --dev    - Uruchamia backend (port 8000) oraz frontend Vite w trybie dev (port 5173)"
            echo "  ./run.sh --seed   - Zasila bazę danymi demonstracyjnymi Waterdeep (uruchamia tymczasowe API jeśli nieaktywne)"
            exit 0
            ;;
        *)
            echo "Nieznana opcja: ${command_argument}. Użyj ./run.sh --help."
            exit 1
            ;;
    esac
done

# Sprawdzenie wirtualnego środowiska Pythona
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

# Sprawdzenie zbudowanego frontendu
if [ ! -f "frontend/dist/index.html" ] && [ "${launch_mode}" != "dev" ]; then
    echo "📦 Wykryto brak skompilowanego frontendu. Budowanie aplikacji React..."
    (cd frontend && npm install && npm run build)
    echo "✅ Frontend zbudowany pomyślnie."
fi

# Wykonanie zasilenia bazy jeśli wybrano --seed
if [ "${launch_mode}" = "seed_only" ]; then
    echo "🌱 Zasilanie bazy danymi demonstracyjnymi..."

    server_already_running=false
    if curl -s -f "http://${server_host}:${server_port}/api/health" &>/dev/null; then
        server_already_running=true
    fi

    if [ "${server_already_running}" = "false" ]; then
        echo "🚀 Tymczasowe uruchomienie serwera API do przesłania danych przez HTTP..."
        "${uvicorn_binary}" backend.app.main:app --host "${server_host}" --port "${server_port}" &
        temporary_server_process_id=$!

        cleanup_temp_server() {
            kill "${temporary_server_process_id}" 2>/dev/null || true
        }
        trap cleanup_temp_server EXIT INT TERM

        # Oczekiwanie na gotowość serwera (do 10 sekund)
        server_ready=false
        for wait_attempt in $(seq 1 20); do
            if curl -s -f "http://${server_host}:${server_port}/api/health" &>/dev/null; then
                server_ready=true
                break
            fi
            sleep 0.5
        done

        if [ "${server_ready}" = "false" ]; then
            echo "❌ Nie udało się uruchomić serwera API."
            exit 1
        fi
    fi

    "${python_binary}" generator/seed_waterdeep.py "http://${server_host}:${server_port}" admin "HasloAdministratora123!"

    if [ "${server_already_running}" = "false" ]; then
        echo "🛑 Zatrzymano tymczasowy serwer API."
        kill "${temporary_server_process_id}" 2>/dev/null || true
        trap - EXIT INT TERM
    fi

    echo "✅ Zasilenie bazy zakończone sukcesem!"
    exit 0
fi

# Tryb HTTPS – generowanie certyfikatu deweloperskiego w razie potrzeby
if [ "${launch_mode}" = "https" ]; then
    if [ ! -f "certs/cert.pem" ] || [ ! -f "certs/key.pem" ]; then
        echo "🔐 Generowanie lokalnego certyfikatu SSL..."
        mkdir -p certs
        openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj '/CN=localhost' &>/dev/null
        echo "✅ Certyfikat wygenerowany w katalogu certs/."
    fi
fi

# Baner powitalny
echo "==========================================================================="
echo "🏰 Waterdeep Watchtower – Punkt Dowodzenia Straży Miejskiej Waterdeep"
echo "==========================================================================="
if [ "${launch_mode}" = "https" ]; then
    echo "🌐 Adres aplikacji (HTTPS): https://${server_host}:${server_port}"
    echo "📡 Dokumentacja Swagger UI: https://${server_host}:${server_port}/docs"
elif [ "${launch_mode}" = "dev" ]; then
    echo "🌐 Frontend Vite (Dev):    http://localhost:5173"
    echo "📡 Backend FastAPI (API):   http://${server_host}:${server_port}"
    echo "📡 Dokumentacja Swagger UI: http://${server_host}:${server_port}/docs"
else
    echo "🌐 Adres aplikacji:         http://${server_host}:${server_port}"
    echo "📡 Dokumentacja Swagger UI: http://${server_host}:${server_port}/docs"
fi
echo "👤 Domyślny administrator:  admin / HasloAdministratora123!"
echo "🛑 Aby zatrzymać serwer, naciśnij Ctrl + C"
echo "==========================================================================="

# Uruchomienie w zależności od trybu
if [ "${launch_mode}" = "https" ]; then
    exec "${uvicorn_binary}" backend.app.main:app \
        --host "${server_host}" \
        --port "${server_port}" \
        --ssl-keyfile certs/key.pem \
        --ssl-certfile certs/cert.pem \
        --reload
elif [ "${launch_mode}" = "dev" ]; then
    # Uruchomienie backendu w tle i frontendu na pierwszym planie
    "${uvicorn_binary}" backend.app.main:app --host "${server_host}" --port "${server_port}" --reload &
    backend_process_identifier=$!

    cleanup_dev_processes() {
        echo -e "\n🛑 Zatrzymywanie procesów deweloperskich..."
        kill "${backend_process_identifier}" 2>/dev/null || true
    }
    trap cleanup_dev_processes EXIT INT TERM

    (cd frontend && npm run dev)
else
    exec "${uvicorn_binary}" backend.app.main:app \
        --host "${server_host}" \
        --port "${server_port}" \
        --reload
fi
