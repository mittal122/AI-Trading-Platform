#!/usr/bin/env bash
# Expose the locally-running backend to the internet for the Vercel frontend.
#
# Usage:
#   ./scripts/serve_public.sh                 # tunnel an already-running backend (:8000)
#   NGROK_DOMAIN=my-app.ngrok-free.app ./scripts/serve_public.sh   # stable ngrok domain
#
# Prefers ngrok (free account gives ONE permanent static domain — set it via
# NGROK_DOMAIN so the Vercel rewrite never needs updating). Falls back to
# cloudflared quick tunnel (no account, but the URL changes every run).
set -euo pipefail

PORT="${BACKEND_PORT:-8000}"

if ! curl -sf -o /dev/null "http://localhost:${PORT}/docs"; then
  echo "✗ No backend answering on :${PORT}."
  echo "  Start it first:  ./run.sh   (or: docker compose up -d)"
  exit 1
fi
echo "✓ Backend is up on :${PORT}"

if command -v ngrok >/dev/null 2>&1; then
  if [ -n "${NGROK_DOMAIN:-}" ]; then
    echo "→ ngrok tunnel on stable domain: https://${NGROK_DOMAIN}"
    exec ngrok http --domain "${NGROK_DOMAIN}" "${PORT}"
  fi
  echo "→ ngrok tunnel (random URL — claim your free static domain at"
  echo "   https://dashboard.ngrok.com/domains and pass it as NGROK_DOMAIN)"
  exec ngrok http "${PORT}"
fi

if command -v cloudflared >/dev/null 2>&1; then
  echo "→ cloudflared quick tunnel (URL is random and changes every run —"
  echo "   update frontend/vercel.json or the Vercel env var when it does)"
  exec cloudflared tunnel --url "http://localhost:${PORT}"
fi

cat <<'EOF'
✗ No tunnel tool installed. Install ONE of:

  ngrok (recommended — free permanent subdomain):
    snap install ngrok        # or https://ngrok.com/download
    ngrok config add-authtoken <token from dashboard.ngrok.com>

  cloudflared (no account needed, random URL each run):
    sudo dpkg -i https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

Then re-run this script.
EOF
exit 1
