#!/usr/bin/env bash
# ONE command to put the site online after a reboot:
#
#   ./go_live.sh          start backend + ngrok tunnel → friends can use the Vercel URL
#   ./go_live.sh stop     take everything offline
#
# Backend runs detached (survives closing the terminal). Logs: logs/backend.log,
# logs/ngrok.log.
set -euo pipefail
cd "$(dirname "$0")"

DOMAIN="${NGROK_DOMAIN:-lumpiness-abdomen-slouching.ngrok-free.dev}"
PORT=8000

if [ "${1:-}" = "stop" ]; then
  pkill -f "uvicorn backend.app.main:app" 2>/dev/null && echo "✓ backend stopped" || echo "· backend was not running"
  pkill -f "ngrok http" 2>/dev/null && echo "✓ tunnel stopped" || echo "· tunnel was not running"
  exit 0
fi

mkdir -p logs

# ── 1. Backend ───────────────────────────────────────────────────────────────
if curl -sf -o /dev/null "http://localhost:${PORT}/docs"; then
  echo "✓ backend already running on :${PORT}"
else
  [ -f .env ] || { echo "✗ .env missing — copy .env.example and fill it in"; exit 1; }
  [ -x .venv/bin/uvicorn ] || { echo "✗ .venv missing — run ./run.sh once to set it up"; exit 1; }
  echo "→ starting backend…"
  setsid nohup env PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --port "${PORT}" \
      > logs/backend.log 2>&1 < /dev/null &
  for i in $(seq 1 60); do
    sleep 2
    curl -sf -o /dev/null "http://localhost:${PORT}/docs" && break
    [ "$i" = 60 ] && { echo "✗ backend didn't come up — check logs/backend.log"; exit 1; }
  done
  echo "✓ backend up on :${PORT}"
fi

# ── 2. Tunnel ────────────────────────────────────────────────────────────────
pkill -f "ngrok http" 2>/dev/null || true
sleep 1
echo "→ starting tunnel https://${DOMAIN} …"
setsid nohup ngrok http --domain "${DOMAIN}" "${PORT}" --log stdout \
    > logs/ngrok.log 2>&1 < /dev/null &

# ── 3. Prove it works from the internet side ────────────────────────────────
for i in $(seq 1 15); do
  sleep 2
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 8 \
      -H "ngrok-skip-browser-warning: true" \
      "https://${DOMAIN}/api/v1/market/live?symbol=BTCUSDT&interval=1m" || true)
  [ "$code" = "200" ] && break
  [ "$i" = 15 ] && { echo "✗ tunnel not answering — check logs/ngrok.log"; exit 1; }
done

echo
echo "──────────────────────────────────────────────────"
echo "  ONLINE — share your Vercel URL with friends."
echo "  Backend : http://localhost:${PORT}"
echo "  Tunnel  : https://${DOMAIN}  (verified: live market data)"
echo "  Stop    : ./go_live.sh stop"
echo "──────────────────────────────────────────────────"
