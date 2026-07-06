# Public Deployment — Vercel frontend + k3s backend on home PC

**Date:** 2026-07-06
**Goal:** Access the AI Trading Platform from anywhere. Frontend on Vercel,
backend running 24/7 on a home PC (Linux, CPU-only, no dedicated GPU),
reachable over the public internet without port-forwarding or a domain.

---

## Decisions (locked with user)

| Topic | Decision |
|---|---|
| Connectivity home→internet | **Tailscale Funnel** — stable public `https://<host>.<tailnet>.ts.net`, no domain, no port-forward, hides home IP, supports WSS |
| Security posture | **Site-wide password gate** — one shared token protects the entire app (frontend login + backend rejects every request without it) |
| Backend orchestration | **k3s** (lightweight single-node Kubernetes), systemd-managed → auto-start on reboot, auto-restart on crash. Chosen over full kubeadm k8s because the target host is an old i3 / 8GB box — full k8s control-plane (~2GB) would starve Kronos/Postgres; k3s overhead is ~0.5GB. Manifests are standard k8s, portable to full k8s later unchanged. |
| Kronos compute | **CPU only** (host has no dedicated GPU), **lazy-loaded** (see §8) to keep boot RAM low on the 8GB box |
| Database | **PostgreSQL** as a k8s StatefulSet with a PersistentVolume |
| Frontend host | **Vercel** |

### Hard constraint — single replica only
The trading backend **must** run `replicas: 1`. The paper engine, live engine,
SMC scanner (60s background asyncio task in the FastAPI lifespan), and the
Binance-credential store are all process-wide global singletons. Two pods would
double-fire trade signals and run two scanners. k3s still delivers auto-restart,
auto-start-on-reboot, rolling redeploys, and clean secret/config management —
but NOT multi-replica horizontal scaling. True scale-out is a separate future
project (per-user refactor + externalized engines) and is explicitly out of scope.

---

## Architecture

```
   Browser (anywhere)
        │  https
        ▼
   Vercel  ─────────────────►  React build
        │                      VITE_API_BASE_URL → funnel URL
        │  https / wss  (site token on every request)
        ▼
   Tailscale Funnel  →  https://<host>.<tailnet>.ts.net  (public, TLS by Tailscale)
        ▼  forwards to host port
   Home PC ── k3s (single node, systemd, survives reboot)
        ├── Deployment: backend  (replicas: 1)   image ← docker/backend.Dockerfile
        │     ├── env from Secret + ConfigMap
        │     ├── hostPath mount: Kronos model repo (KRONOS_PATH)
        │     └── connects to Postgres Service via DATABASE_URL
        ├── Service: backend (NodePort/LoadBalancer, host port 8000)  ← funnel target
        ├── StatefulSet: postgres + PersistentVolumeClaim (data survives restarts)
        ├── Service: postgres (ClusterIP, internal only)
        ├── Secret: NVIDIA_API_KEY, SITE_ACCESS_TOKEN, ADMIN_API_TOKEN,
        │           BINANCE_API_KEY/SECRET, JWT_SECRET, POSTGRES_PASSWORD, DATABASE_URL
        └── ConfigMap: CORS_ALLOWED_ORIGINS, DEFAULT_SYMBOL/INTERVAL, non-secret config
```

Uptime bound: the app is only reachable while the home PC + its internet are up.
Accepted for a single-operator deployment.

---

## Components & changes

### 1. Site-wide password gate (NEW — security)

**Backend** — new `SiteAccessMiddleware` in `backend/app/main.py` (or
`core/security.py` helper), added ABOVE the existing CORS + admin-token layers:
- Reads `SITE_ACCESS_TOKEN` from env. **If unset → gate disabled** (local dev
  keeps working exactly as today).
- If set → every request must carry the token, else `401`.
  - HTTP: `X-Site-Token` header (attached by the frontend axios interceptor).
  - **WebSocket** (`/api/v1/paper/ws`): browsers can't set custom headers on a
    `new WebSocket()`, so the token rides as a query param `?site_token=...`,
    validated in the middleware/endpoint for the WS path.
  - `OPTIONS` (CORS preflight) always passes through (never gated) so CORS works.
  - Health root `GET /` stays open (liveness/readiness probes + funnel health).
- Constant-time compare (`hmac.compare_digest`), same pattern as the admin gate.
- Layering: this gate is the OUTER door (whole app). The existing
  `require_admin` `X-Admin-Token` gate stays as the INNER door on money
  endpoints — both required for live-trading / Binance-key routes.

**Frontend** — new lightweight auth:
- `SITE_TOKEN_KEY` in `client.ts` (mirrors existing `admin.apiToken` pattern):
  `getSiteToken()` / `setSiteToken()`, axios request interceptor attaches
  `X-Site-Token`.
- A login screen (`components/SiteGate.tsx` or in `App.tsx`): if no site token
  stored, render a password form; on submit, store token and mount the app.
  A `401` from the backend clears the token and returns to the login screen.
- `PaperTrade.tsx` WS URL gains `?site_token=<token>`.

### 2. Frontend → configurable backend URL (CHANGE)

- `client.ts`: `baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1'`.
  Local dev (no env var) → relative `/api/v1` → Vite proxy → unchanged behavior.
  Vercel (env var set) → absolute `https://<host>.<tailnet>.ts.net/api/v1`.
- `PaperTrade.tsx` WS host: derive from `VITE_API_BASE_URL` when present
  (parse origin, swap `https`→`wss`), else current `location.host` behavior.
  This fixes the existing latent bug where the WS points at `location.host`
  (which on Vercel would wrongly be the Vercel domain).

### 3. CORS (CONFIG only, no code change)

Backend already reads `CORS_ALLOWED_ORIGINS` (`core/saas_config.py`). Set it via
the k8s ConfigMap to the exact Vercel origin(s), e.g.
`https://your-app.vercel.app` (+ any custom domain). Documented in DEPLOY.md.

### 4. k3s manifests (NEW — `k8s/` directory)

```
k8s/
  namespace.yaml            trading namespace
  secret.example.yaml       template (real secrets NOT committed; kubectl create secret)
  configmap.yaml            non-secret env
  postgres-statefulset.yaml StatefulSet + headless Service + PVC
  backend-deployment.yaml   Deployment (replicas:1) + probes + volume mounts
  backend-service.yaml      Service exposing host port 8000 (funnel target)
  pvc-kronos.md             note: Kronos repo mounted via hostPath (host path in ConfigMap)
  kustomization.yaml        ties it together (kubectl apply -k k8s/)
```

Key points:
- Backend image built from the existing `docker/backend.Dockerfile`, imported
  into k3s containerd: `docker build … && docker save … | sudo k3s ctr images import -`
  (documented; avoids standing up a registry).
- `DATABASE_URL=postgresql+asyncpg://…@postgres:5432/trading` → app uses Postgres
  (its config already switches on this env var).
- Fresh DB: `create_tables()` runs on startup and `Base.metadata.create_all`
  creates every table (SMC scanner tables included) — no Alembic step needed for
  a clean deploy.
- Kronos: `KRONOS_PATH` points at a hostPath-mounted copy of the Kronos repo
  (`model.py` must be present or the app won't boot). CPU-only — no GPU resources
  requested, no device-plugin.
- Liveness/readiness probe → `GET /`.
- SQLite is NOT used in this deploy; Postgres replaces it. Logs to stdout
  (`kubectl logs`), so no log PVC needed.

### 5. Tailscale Funnel (NEW — setup + supervision)

- Install Tailscale on the host, `tailscale up`, enable Funnel (HTTPS features
  in the tailnet admin console / ACL).
- Expose the k3s backend Service's host port publicly:
  `sudo tailscale funnel 8000` → `https://<host>.<tailnet>.ts.net` → backend.
- Persist it: a small systemd unit (or `tailscale funnel --bg`) so it survives
  reboot alongside k3s. Documented in DEPLOY.md.
- The resulting stable URL is what goes into Vercel's `VITE_API_BASE_URL` and the
  backend's `CORS_ALLOWED_ORIGINS`.

### 6. Vercel config (NEW)

- `frontend/vercel.json` — SPA rewrite (all routes → `/index.html`), build via
  Vite. Root directory = `frontend/`, build `npm run build`, output `dist/`.
- Env var in Vercel project: `VITE_API_BASE_URL=https://<host>.<tailnet>.ts.net/api/v1`.
- Note: the funnel URL must exist BEFORE the first Vercel build (build-time env).

### 8. Lazy-load Kronos (CHANGE — memory on the 8GB box)

The predict path **already** lazy-loads: `prediction_service.py` does
`if not kronos.is_loaded(): kronos.load()` before predicting. The ONLY eager
load is `backend/app/main.py:44` `kronos.load()` in the lifespan startup.

- Remove/guard that one line so the model loads on the **first `/predict` call**
  instead of at boot. Until then the box runs without PyTorch's model in RAM
  (~2–4GB freed at idle), which matters on 8GB.
- Optional env flag `KRONOS_EAGER_LOAD` (default false) to restore eager loading
  if ever wanted — keeps the behavior configurable, no hard removal.
- Trade-off (documented): the first `/predict` request after boot is slow (model
  loads then). Acceptable — prediction is not on the hot path for dashboards.
- No other change needed; `is_loaded()`/`load()`/`predict()` already exist.

### 7. Deploy guide (NEW — `docs/DEPLOY.md`)

Exact ordered commands, two halves:
- **Home PC:** install k3s + Tailscale → build & import backend image → create
  Secret from `.env` values → `kubectl apply -k k8s/` → `tailscale funnel 8000`
  → verify `https://…ts.net/` responds.
- **Vercel:** import repo, set root=`frontend/`, set `VITE_API_BASE_URL`, deploy
  → set that Vercel origin into the backend ConfigMap's `CORS_ALLOWED_ORIGINS`
  → set `SITE_ACCESS_TOKEN` in the Secret → redeploy backend → open the Vercel
  URL, enter the site password.

---

## Data flow (request lifecycle)

1. User opens Vercel URL → React app loads → no site token stored → login screen.
2. User enters password → stored in localStorage → app mounts.
3. Every API call: axios attaches `X-Site-Token` → request goes to
   `https://…ts.net/api/v1/…` → Tailscale Funnel → k3s Service → backend pod.
4. Backend `SiteAccessMiddleware` validates the token (401 → frontend logs out).
5. CORS middleware allows the Vercel origin.
6. Money endpoints additionally require `X-Admin-Token` (unchanged).
7. Paper-trade WS: `wss://…ts.net/api/v1/paper/ws?site_token=…` validated for the
   WS path.

---

## Error handling

- Missing/invalid site token → `401`; frontend clears token, shows login.
- Missing `VITE_API_BASE_URL` on Vercel → app would call same-origin `/api/v1`
  (no backend there) → calls fail; DEPLOY.md flags this as the #1 gotcha.
- Backend pod crash → k3s restarts it (Deployment); brief downtime, funnel
  reconnects automatically.
- Postgres pod restart → data persists on the PVC; backend reconnects (asyncpg
  pool re-establishes; a few failed requests during the gap are acceptable).
- Funnel/host offline → app unreachable (documented uptime bound).
- CORS origin mismatch → browser blocks calls; DEPLOY.md shows how to fix the
  ConfigMap value.

---

## Testing / verification

- **Backend unit:** `tests/test_site_gate.py` (NEW) — gate disabled when
  `SITE_ACCESS_TOKEN` unset; 401 without token when set; 200 with correct token;
  `OPTIONS` and `GET /` always pass; WS query-param path validated. Follows the
  existing `tests/test_security_hardening.py` style. Full backend suite must
  still pass (zero regressions).
- **Frontend:** `tsc --noEmit` clean; login screen gates the app; a wrong
  password never mounts the app; WS connects with the token appended.
- **k8s (local, before funnel):** `kubectl apply -k k8s/` on the host, pod
  Ready, `kubectl port-forward` → `GET /` responds, Postgres tables created.
- **End-to-end:** funnel URL responds publicly; Vercel build with the env var
  reaches the backend; login → dashboards load → a paper trade places → WS shows
  live. (Manual, documented — a headless run in CI isn't set up for k8s here.)

---

## Out of scope (stated, not silently dropped)

- Horizontal scaling / multi-replica (needs the per-user + externalized-engine
  refactor — big separate project).
- Per-user accounts / real JWT login UI (app is single-operator by design).
- GPU acceleration for Kronos (host has none; CPU is accepted).
- Custom domain / branded URL (Tailscale `ts.net` URL is used).
- CI/CD automation for the k8s deploy (manual `kubectl apply` documented).
- Alembic migration workflow (fresh deploy uses `create_all`; migrations remain
  a future concern for schema changes on an existing prod DB).

---

## File-change summary

**New**
- `backend/app/core/` site-gate helper + middleware wiring in `main.py`
- `frontend/src/components/SiteGate.tsx` (login screen)
- `frontend/vercel.json`
- `k8s/*` (manifests + kustomization)
- `docs/DEPLOY.md`
- `tests/test_site_gate.py`

**Changed**
- `backend/app/main.py` (register SiteAccessMiddleware; lazy-load Kronos — guard the eager `kronos.load()` behind `KRONOS_EAGER_LOAD`)
- `frontend/src/api/client.ts` (VITE_API_BASE_URL base + site-token interceptor)
- `frontend/src/pages/PaperTrade.tsx` (WS host + `?site_token=`)
- `frontend/src/App.tsx` (mount SiteGate before the app)
- `.env.example` (document `SITE_ACCESS_TOKEN`, `VITE_API_BASE_URL`)

**Config only (no code)**
- `CORS_ALLOWED_ORIGINS` → Vercel origin (via ConfigMap)
```
