#!/usr/bin/env bash
# Starts backend (uvicorn, :8000) + frontend (vite, :5173) together.
# Ctrl+C stops both. Logs go to logs/backend.log and logs/frontend.log.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -f .env ]; then
  echo "No .env found — copy .env.example to .env and fill it in first."
  exit 1
fi

if [ ! -x .venv/bin/uvicorn ]; then
  echo "No .venv found — set up the Python venv first:"
  echo "  python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [ ! -d frontend/node_modules ]; then
  echo "frontend/node_modules missing — run 'cd frontend && npm install' first."
  exit 1
fi

mkdir -p logs

echo "Stopping any previous instance…"
pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true
pkill -f "vite" --full 2>/dev/null || true
sleep 1

echo "Starting backend on :8000 (log: logs/backend.log)…"
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!

echo "Starting frontend on :5173 (log: logs/frontend.log)…"
(cd frontend && npm run dev > ../logs/frontend.log 2>&1) &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "Stopping backend + frontend…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  echo "Stopped."
}
trap cleanup EXIT INT TERM

echo -n "Waiting for backend"
for _ in $(seq 1 30); do
  if curl -s -m 1 http://localhost:8000/ > /dev/null 2>&1; then
    echo " — up."
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173  (check logs/frontend.log if this port was busy)"
echo "Logs:     tail -f logs/backend.log logs/frontend.log"
echo "Press Ctrl+C to stop both."
echo ""

wait
