#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID=""

on_error() {
  local status=$?
  echo "[cloud-studio] Command failed at line ${BASH_LINENO[0]} (exit ${status})." >&2
  exit "$status"
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

on_signal() {
  trap - ERR
  exit 0
}

trap on_error ERR
trap cleanup EXIT
trap on_signal INT TERM

cd "$PROJECT_ROOT"
echo "[cloud-studio] Project root: $PROJECT_ROOT"
echo "[cloud-studio] Python: $(python --version 2>&1)"
echo "[cloud-studio] Node: $(node --version 2>&1)"

if command -v uv >/dev/null 2>&1; then
  UV_BIN="$(command -v uv)"
else
  echo "[cloud-studio] Installing uv..."
  python -m pip install --user uv
  UV_BIN="$(python -c 'import site; print(site.USER_BASE)')/bin/uv"
fi

echo "[cloud-studio] Installing Python dependencies..."
"$UV_BIN" sync --frozen

echo "[cloud-studio] Installing frontend dependencies..."
npm --prefix frontend ci

echo "[cloud-studio] Starting backend on port 8000..."
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

backend_ready=false
for _ in {1..60}; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    wait "$BACKEND_PID"
  fi

  if .venv/bin/python -c \
    'from urllib.request import urlopen; urlopen("http://127.0.0.1:8000/health", timeout=1)' \
    >/dev/null 2>&1; then
    backend_ready=true
    break
  fi
  sleep 1
done

if [[ "$backend_ready" != true ]]; then
  echo "[cloud-studio] Backend did not become healthy within 60 seconds." >&2
  exit 1
fi

echo "[cloud-studio] Backend is healthy. Starting frontend on port ${PORT:-3000}..."
npm --prefix frontend run dev -- --host 0.0.0.0 --port "${PORT:-3000}"
