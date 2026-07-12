# Deploy: frontend on Vercel, backend on your PC

Goal: anyone opens `https://<your-app>.vercel.app` and uses the platform,
while the backend (FastAPI + Postgres/SQLite) keeps running on your own PC.

```
friend's browser ──▶ Vercel (frontend, global CDN)
                        │ /api/* rewrite — same origin, no CORS
                        ▼
                 https://<you>.ngrok-free.app   (encrypted tunnel)
                        ▼
                 your PC → backend :8000
```

Your PC needs **no router changes, no port forwarding, no public IP** — the
tunnel makes an outbound connection and relays traffic back.

---

## Part 1 — Expose the backend (your PC, one-time ~10 min)

1. Create a free account at https://ngrok.com → dashboard → **Your Authtoken**.
2. Install + authenticate:
   ```bash
   snap install ngrok            # or download from ngrok.com/download
   ngrok config add-authtoken <YOUR_TOKEN>
   ```
3. Claim your **free permanent domain**: dashboard → *Domains* → *Create Domain*
   → you get something like `example-app.ngrok-free.app`. This URL never
   changes — Vercel is configured against it exactly once.
4. Start backend + tunnel (every time you want the site live):
   ```bash
   ./run.sh                                             # or: docker compose up -d
   NGROK_DOMAIN=example-app.ngrok-free.app ./scripts/serve_public.sh
   ```
5. Sanity check from a phone (not your wifi):
   `https://example-app.ngrok-free.app/docs` should show the API docs.

> No account at all? `cloudflared tunnel --url http://localhost:8000` works
> too, but the URL is random on every run — you'd re-edit the Vercel config
> each time. The free ngrok static domain avoids that.

## Part 2 — Point the frontend at your tunnel (one-time)

Edit `frontend/vercel.json` — replace the placeholder:

```json
"destination": "https://example-app.ngrok-free.app/api/:path*"
```

Commit + push. That's the only wiring: the browser calls `/api/...` on the
Vercel domain and Vercel's edge forwards it to your PC. Same-origin, so no
CORS config is needed and your tunnel URL isn't in the page's JavaScript.

## Part 3 — Deploy on Vercel (one-time ~5 min)

1. https://vercel.com → sign up with your GitHub account.
2. **Add New → Project** → import `mittal122/AI-Trading-Platform`.
3. Configure:
   - **Root Directory:** `frontend`   ← the important one
   - Framework preset: Vite (auto-detected)
   - Build command `npm run build`, output `dist` (defaults are right)
4. **Deploy.** You get `https://<project>.vercel.app` — that's the URL to share.

Every future `git push` to master redeploys the frontend automatically.

## Reality checklist

- **Backend must be running** — friends see the UI shell always (it's on
  Vercel), but data loads only while your PC has backend + tunnel up.
- **Paper-trading page shows "Polling" instead of "WebSocket live"** on
  Vercel — rewrites don't carry WebSockets; the page's built-in polling
  fallback covers it (15s refresh). Optional fix: set the Vercel env var
  `VITE_API_BASE_URL=https://example-app.ngrok-free.app` and add
  `CORS_ALLOWED_ORIGINS=https://<project>.vercel.app` to your PC's `.env` —
  direct mode, WebSocket works, at the cost of exposing the tunnel URL.
- **Set `ADMIN_API_TOKEN` in your PC's `.env`** before sharing the URL — it
  locks live-trading start/stop, exchange-key save, and delete-all behind a
  token only you enter (Settings page). Everything else is demo-safe (paper
  trading only).
- ngrok free tier: 1 static domain, generous request quota — fine for demos;
  it shows an interstitial page on the FIRST visit via browser (API calls
  through the Vercel rewrite are not affected).
