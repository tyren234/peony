#!/usr/bin/env bash
# 🏰 Waterdeep Watchtower – Skrypt startowy dla środowiska Azure App Service

set -e

application_port="${PORT:-8000}"

echo "Starting Waterdeep Watchtower on port ${application_port}..."
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port "${application_port}"
