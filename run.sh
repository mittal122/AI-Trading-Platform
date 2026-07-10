#!/usr/bin/env bash
# ============================================================================
#  AI Trading Platform — one-click launcher
# ----------------------------------------------------------------------------
#  Just run:  ./run.sh
#
#  On first run it bootstraps everything automatically:
#    - creates the Python venv (.venv) and installs backend requirements
#    - seeds .env from .env.example if you don't have one yet
#    - installs frontend dependencies (npm install)
#  On every run it starts backend (:8000) + frontend (:5173) together,
#  health-checks the backend, streams logs to logs/, and stops both on Ctrl+C.
# ============================================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# ---- pretty output ---------------------------------------------------------
info()  { echo -e "\033[1;36m▸\033[0m $*"; }
ok()    { echo -e "\033[1;32m✓\033[0m $*"; }
warn()  { echo -e "\033[1;33m!\033[0m $*"; }
die()   { echo -e "\033[1;31m✗\033[0m $*" >&2; exit 1; }

# ---- pick a python ---------------------------------------------------------
PYTHON="$(command -v python3.12 || command -v python3 || true)"
[ -n "$PYTHON" ] || die "Python 3.12 not found. Install it, then re-run ./run.sh"

# ---- 1. .env ---------------------------------------------------------------
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    warn ".env created from .env.example — add your API keys (NVIDIA/Binance) to enable AI + live trading."
  else
    die "No .env and no .env.example to copy from."
  fi
fi

# ---- 2. python venv + backend deps -----------------------------------------
if [ ! -x .venv/bin/uvicorn ]; then
  info "Setting up Python venv (first-run, one time)…"
  [ -d .venv ] || "$PYTHON" -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements.txt
  ok "Backend dependencies installed."
fi

# ---- 3. frontend deps ------------------------------------------------------
if [ ! -d frontend/node_modules ]; then
  command -v npm >/dev/null 2>&1 || die "npm not found. Install Node.js, then re-run ./run.sh"
  info "Installing frontend dependencies (first-run, one time)…"
  (cd frontend && npm install --silent)
  ok "Frontend dependencies installed."
fi

mkdir -p logs

# ---- 4. stop any previous instance -----------------------------------------
info "Stopping any previous instance…"
pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true
pkill -f "vite" --full 2>/dev/null || true
sleep 1

# ---- 5. start backend + frontend -------------------------------------------
info "Starting backend on :8000 (log: logs/backend.log)…"
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!

info "Starting frontend on :5173 (log: logs/frontend.log)…"
(cd frontend && npm run dev > ../logs/frontend.log 2>&1) &
FRONTEND_PID=$!

cleanup() {
  echo ""
  info "Stopping backend + frontend…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  ok "Stopped."
}
trap cleanup EXIT INT TERM

# ---- 6. wait for backend health -------------------------------------------
echo -n "Waiting for backend"
for _ in $(seq 1 30); do
  if curl -s -m 1 http://localhost:8000/ > /dev/null 2>&1; then
    echo " — up."
    break
  fi
  # bail early if the backend process already died
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    die "Backend failed to start — see logs/backend.log"
  fi
  echo -n "."
  sleep 1
done

echo ""
ok "Backend:  http://localhost:8000"
ok "Frontend: http://localhost:5173  (check logs/frontend.log if this port was busy)"
echo "  Logs:   tail -f logs/backend.log logs/frontend.log"
echo "  Press Ctrl+C to stop both."
echo ""

wait
