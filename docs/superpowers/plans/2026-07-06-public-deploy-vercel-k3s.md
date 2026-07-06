# Public Deploy (Vercel + k3s) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the platform reachable from anywhere — React frontend on Vercel, FastAPI backend running 24/7 on a home PC under k3s, exposed via Tailscale Funnel, locked behind one shared site password.

**Architecture:** A site-wide token gate (HTTP middleware + WS query-param check) protects the whole backend. The frontend reads its backend URL from `VITE_API_BASE_URL` and attaches the site token to every request/WS. The backend runs in k3s (single replica — trading engines are global singletons) with a Postgres StatefulSet; Kronos lazy-loads to save RAM on an 8GB box. Tailscale Funnel gives a stable public HTTPS/WSS URL with no domain or port-forward.

**Tech Stack:** FastAPI + Starlette middleware, React 19 + Vite, k3s (Kubernetes), Postgres 16, Tailscale Funnel, Vercel.

## Global Constraints

- Python 3.12, FastAPI, Pydantic v2. Black format, funcs 10–40 lines, classes 300–500 lines max.
- No hardcoded thresholds/secrets — all via `core/*_config.py` reading env vars.
- Every backend behavior change gets a `tests/test_*.py`. Run tests with: `PYTHONPATH=. .venv/bin/python -m pytest tests/<file> -v` (project also runs files directly with `.venv/bin/python tests/<file>`; pytest works for these).
- Frontend has no JS test runner — verify frontend tasks with `cd frontend && npx tsc --noEmit` (must be clean) and `npm run build`.
- **Backend replicas MUST stay 1** — paper/live engines, SMC scanner, Binance-cred store are process-wide singletons.
- Conventional commits: `feat(deploy):`, `feat(security):`, `fix(...)`, `test(...)`, `docs(deploy):`.
- Gates default OPEN when their env var is unset → local dev behavior unchanged.
- **GOTCHA:** uvicorn has no `--reload` here — after backend edits, restart the process before live-testing (`run_in_background` for a clean detach). Not relevant to unit tests.
- Never commit real secrets. k8s Secret is created via `kubectl`, never checked in.

---

### Task 1: Site-access token config

**Files:**
- Modify: `backend/app/core/security_config.py`
- Test: `tests/test_site_gate.py` (create)

**Interfaces:**
- Consumes: nothing new.
- Produces: `security_config.SITE_ACCESS_TOKEN: str`, `security_config.site_gate_enabled: bool`, `security_config.KRONOS_EAGER_LOAD: bool`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_site_gate.py`:

```python
"""Site-wide access gate — one shared token protects the whole backend."""
import importlib
import os

import backend.app.core.security_config as sc_mod


def _reload_config():
    return importlib.reload(sc_mod).security_config


def test_site_gate_disabled_when_unset(monkeypatch):
    monkeypatch.delenv("SITE_ACCESS_TOKEN", raising=False)
    cfg = _reload_config()
    assert cfg.SITE_ACCESS_TOKEN == ""
    assert cfg.site_gate_enabled is False


def test_site_gate_enabled_when_set(monkeypatch):
    monkeypatch.setenv("SITE_ACCESS_TOKEN", "hunter2")
    cfg = _reload_config()
    assert cfg.SITE_ACCESS_TOKEN == "hunter2"
    assert cfg.site_gate_enabled is True


def test_kronos_eager_default_off(monkeypatch):
    monkeypatch.delenv("KRONOS_EAGER_LOAD", raising=False)
    cfg = _reload_config()
    assert cfg.KRONOS_EAGER_LOAD is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/media/sun/drive/devops-project/trading app/AI-Trading-Platform" && PYTHONPATH=. .venv/bin/python -m pytest tests/test_site_gate.py -v`
Expected: FAIL — `AttributeError: 'SecurityConfig' object has no attribute 'SITE_ACCESS_TOKEN'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/core/security_config.py`, inside `class SecurityConfig`, after the `ADMIN_API_TOKEN` line add:

```python
    # When SITE_ACCESS_TOKEN is set, EVERY request to the backend must carry a
    # matching X-Site-Token header (and the paper WS a ?site_token= query param).
    # Unset → open (local-dev default). This is the outer door for a public
    # deploy: nobody can even read dashboards without the shared password.
    SITE_ACCESS_TOKEN = os.getenv("SITE_ACCESS_TOKEN", "").strip()

    # Load the Kronos model eagerly at startup. Default OFF so an 8GB host boots
    # light — the /predict path lazy-loads on first use (prediction_service.py).
    KRONOS_EAGER_LOAD = _flag("KRONOS_EAGER_LOAD", default=False)
```

And add the property after `admin_gate_enabled`:

```python
    @property
    def site_gate_enabled(self) -> bool:
        return bool(self.SITE_ACCESS_TOKEN)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_site_gate.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security_config.py tests/test_site_gate.py
git commit -m "feat(security): site-access token + lazy-Kronos flag in config"
```

---

### Task 2: Site-access HTTP middleware

**Files:**
- Modify: `backend/app/main.py`
- Test: `tests/test_site_gate.py` (extend)

**Interfaces:**
- Consumes: `security_config.site_gate_enabled`, `security_config.SITE_ACCESS_TOKEN`.
- Produces: `SiteAccessMiddleware` registered so it runs INSIDE CORS (CORS stays outermost). Gate lets through: any request when disabled; `OPTIONS` (CORS preflight); `GET /` (health/probes); WebSocket scope (handled in Task 3). Everything else needs a valid `X-Site-Token`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_site_gate.py`:

```python
from fastapi.testclient import TestClient


def _client(monkeypatch, token=None):
    if token is None:
        monkeypatch.delenv("SITE_ACCESS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("SITE_ACCESS_TOKEN", token)
    monkeypatch.setenv("KRONOS_EAGER_LOAD", "false")  # don't load model in tests
    # reload config + app so the middleware picks up the env
    import backend.app.core.security_config as sc
    importlib.reload(sc)
    import backend.app.main as main_mod
    importlib.reload(main_mod)
    return TestClient(main_mod.app)


def test_health_open_without_token(monkeypatch):
    c = _client(monkeypatch, token="hunter2")
    assert c.get("/").status_code == 200


def test_request_blocked_without_token(monkeypatch):
    c = _client(monkeypatch, token="hunter2")
    r = c.get("/api/v1/market/symbols")
    assert r.status_code == 401


def test_request_allowed_with_token(monkeypatch):
    c = _client(monkeypatch, token="hunter2")
    r = c.get("/api/v1/market/symbols", headers={"X-Site-Token": "hunter2"})
    assert r.status_code != 401


def test_gate_open_when_unset(monkeypatch):
    c = _client(monkeypatch, token=None)
    r = c.get("/api/v1/market/symbols")
    assert r.status_code != 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_site_gate.py -k "token or health" -v`
Expected: FAIL — `test_request_blocked_without_token` returns 200 (no gate yet).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/main.py`:

(a) add `hmac` to the imports at top (with the stdlib imports):

```python
import hmac
```

(b) after the `SecurityHeadersMiddleware` class definition (before `app.add_middleware(SecurityHeadersMiddleware)`), add:

```python
class SiteAccessMiddleware(BaseHTTPMiddleware):
    """Outer door for a public deploy: when SITE_ACCESS_TOKEN is set, every
    HTTP request must carry a matching X-Site-Token header. OPTIONS (CORS
    preflight) and the GET / health check always pass. WebSocket upgrades
    bypass BaseHTTPMiddleware entirely and are gated in the WS endpoint.
    Unset token → gate open (local-dev default)."""

    async def dispatch(self, request: Request, call_next):
        if security_config.site_gate_enabled and request.method != "OPTIONS" and request.url.path != "/":
            token = request.headers.get("X-Site-Token", "")
            if not token or not hmac.compare_digest(token, security_config.SITE_ACCESS_TOKEN):
                return JSONResponse(status_code=401, content={"detail": "Site access token required"})
        return await call_next(request)
```

(c) register it INSIDE CORS — insert this line immediately BEFORE the existing `app.add_middleware(CORSMiddleware, ...)` call (so CORS, added after, is outermost and still handles preflight + adds headers to the 401):

```python
app.add_middleware(SiteAccessMiddleware)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_site_gate.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py tests/test_site_gate.py
git commit -m "feat(security): site-wide access-token HTTP middleware"
```

---

### Task 3: Gate the paper-trading WebSocket + lazy-load Kronos

**Files:**
- Modify: `backend/app/api/v1/paper.py` (WS endpoint, around line 63-75)
- Modify: `backend/app/main.py` (lifespan `kronos.load()`, line ~44)
- Test: `tests/test_site_gate.py` (extend)

**Interfaces:**
- Consumes: `security_config.site_gate_enabled`, `security_config.SITE_ACCESS_TOKEN`, `security_config.KRONOS_EAGER_LOAD`.
- Produces: WS at `/api/v1/paper/ws` requires `?site_token=` when gate enabled (closes with code 1008 otherwise). Kronos loads at boot only if `KRONOS_EAGER_LOAD` true.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_site_gate.py`:

```python
import pytest
from starlette.websockets import WebSocketDisconnect


def test_ws_rejected_without_token(monkeypatch):
    c = _client(monkeypatch, token="hunter2")
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/api/v1/paper/ws"):
            pass


def test_ws_accepted_with_token(monkeypatch):
    c = _client(monkeypatch, token="hunter2")
    # Should connect and receive at least one status frame.
    with c.websocket_connect("/api/v1/paper/ws?site_token=hunter2") as ws:
        data = ws.receive_json()
        assert isinstance(data, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_site_gate.py -k ws -v`
Expected: FAIL — `test_ws_rejected_without_token` does not raise (WS accepts everyone).

- [ ] **Step 3: Write minimal implementation**

(a) In `backend/app/api/v1/paper.py`, add the import near the top:

```python
import hmac

from backend.app.core.security_config import security_config
```

Then change the WS endpoint. Current:

```python
@router.websocket("/ws")
async def paper_status_ws(websocket: WebSocket) -> None:
    ...
    await websocket.accept()
```

to:

```python
@router.websocket("/ws")
async def paper_status_ws(websocket: WebSocket) -> None:
    if security_config.site_gate_enabled:
        token = websocket.query_params.get("site_token", "")
        if not token or not hmac.compare_digest(token, security_config.SITE_ACCESS_TOKEN):
            await websocket.close(code=1008)  # policy violation
            return
    await websocket.accept()
```

(Keep the rest of the endpoint body unchanged.)

(b) In `backend/app/main.py` lifespan, change:

```python
    kronos.load()
```

to:

```python
    if security_config.KRONOS_EAGER_LOAD:
        kronos.load()
    # else: lazy — prediction_service.py loads the model on first /predict call
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_site_gate.py -v`
Expected: PASS (all, including WS + earlier tests).

- [ ] **Step 5: Full regression**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_security_hardening.py tests/test_site_gate.py -v`
Expected: PASS. (Confirms the new middleware didn't break the existing admin-gate/headers tests.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/paper.py backend/app/main.py tests/test_site_gate.py
git commit -m "feat(security): gate paper WS with site_token; lazy-load Kronos"
```

---

### Task 4: Frontend — configurable backend URL + site-token wiring

**Files:**
- Modify: `frontend/src/api/client.ts`
- Verify: `cd frontend && npx tsc --noEmit`

**Interfaces:**
- Consumes: `import.meta.env.VITE_API_BASE_URL` (optional).
- Produces (exported from `client.ts`): `getSiteToken(): string`, `setSiteToken(token: string): void`, `wsUrl(path: string): string` (builds an absolute ws/wss URL for a `/api/v1/...` path, appending `site_token` when set). Axios `baseURL` = `VITE_API_BASE_URL` or `/api/v1`; interceptor attaches `X-Site-Token`; a `401` response clears the stored site token and reloads.

- [ ] **Step 1: Edit `client.ts`**

Change the axios instance creation. Current:

```typescript
export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})
```

to:

```typescript
// On Vercel, VITE_API_BASE_URL points at the home-PC backend (Tailscale Funnel
// URL, e.g. https://pc.tailnet.ts.net/api/v1). In local dev it's unset, so we
// fall back to the relative path that the Vite proxy forwards to :8000.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})
```

- [ ] **Step 2: Add site-token helpers + interceptor**

Immediately after the existing admin-token block (after the `api.interceptors.request.use` that attaches `X-Admin-Token`), add:

```typescript
// Site-wide access token — the shared password gate for a public deploy. When
// the backend sets SITE_ACCESS_TOKEN, every request (and the paper WS) must
// carry this. Empty on a local/open instance. Stored locally like the admin token.
const SITE_TOKEN_KEY = 'site.accessToken'
export function getSiteToken(): string {
  try { return localStorage.getItem(SITE_TOKEN_KEY) ?? '' } catch { return '' }
}
export function setSiteToken(token: string) {
  try {
    if (token) localStorage.setItem(SITE_TOKEN_KEY, token)
    else localStorage.removeItem(SITE_TOKEN_KEY)
  } catch { /* storage unavailable */ }
}
api.interceptors.request.use(config => {
  const token = getSiteToken()
  if (token) config.headers['X-Site-Token'] = token
  return config
})
// A 401 means the site token is missing/wrong — drop it and bounce to the gate.
api.interceptors.response.use(
  r => r,
  err => {
    if (err?.response?.status === 401 && getSiteToken()) {
      setSiteToken('')
      location.reload()
    }
    return Promise.reject(err)
  },
)

// Build an absolute WebSocket URL for a backend path (e.g. '/api/v1/paper/ws').
// Derives host from API_BASE when it's absolute (Vercel), else same-origin (dev).
export function wsUrl(path: string): string {
  let origin: string
  try {
    origin = API_BASE.startsWith('http') ? new URL(API_BASE).origin : location.origin
  } catch {
    origin = location.origin
  }
  const proto = origin.startsWith('https') ? 'wss' : 'ws'
  const host = origin.replace(/^https?:/, '')
  const token = getSiteToken()
  const q = token ? `?site_token=${encodeURIComponent(token)}` : ''
  return `${proto}:${host}${path}${q}`
}
```

- [ ] **Step 3: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors. (If `import.meta.env.VITE_API_BASE_URL` errors, it's a plain optional string — allowed by Vite's default `ImportMetaEnv`; no extra typing needed.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(deploy): configurable API base URL + site-token wiring in client"
```

---

### Task 5: Frontend — site password login screen

**Files:**
- Create: `frontend/src/components/SiteGate.tsx`
- Modify: `frontend/src/App.tsx`
- Verify: `cd frontend && npx tsc --noEmit`

**Interfaces:**
- Consumes: `getSiteToken`, `setSiteToken` from `client.ts`; `api` for a probe request.
- Produces: `<SiteGate>` wrapper — renders a password form until a token is stored AND validates against the backend; on success renders `children`.

- [ ] **Step 1: Create `frontend/src/components/SiteGate.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { api, getSiteToken, setSiteToken } from '../api/client'

/**
 * Site-wide password gate. If the backend runs open (no SITE_ACCESS_TOKEN),
 * a stored token isn't required — but we can't know that until a probe
 * succeeds, so: probe GET / with whatever token we have. 200 → enter.
 * 401 → show the password form. This makes local/open instances pass through
 * with no password while a locked deploy demands one.
 */
export default function SiteGate({ children }: { children: React.ReactNode }) {
  const [ok, setOk] = useState(false)
  const [checking, setChecking] = useState(true)
  const [pwd, setPwd] = useState('')
  const [error, setError] = useState('')

  async function probe() {
    setChecking(true)
    setError('')
    try {
      // Root is always open; use a gated endpoint to actually test the token.
      await api.get('/market/symbols')
      setOk(true)
    } catch (e: any) {
      if (e?.response?.status === 401) setOk(false)
      else setOk(true) // backend up but some other error — let the app load
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => { probe() }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setSiteToken(pwd.trim())
    setError('')
    try {
      await api.get('/market/symbols')
      setOk(true)
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setSiteToken('')
        setError('Wrong password.')
      } else {
        setOk(true)
      }
    }
  }

  if (checking) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0f1117] text-slate-400">
        Loading…
      </div>
    )
  }
  if (ok) return <>{children}</>

  return (
    <div className="flex h-screen items-center justify-center bg-[#0f1117]">
      <form onSubmit={submit}
            className="w-80 rounded-xl border border-slate-700 bg-[#151823] p-6 shadow-xl">
        <h1 className="mb-1 text-lg font-semibold text-slate-100">AI Trading Platform</h1>
        <p className="mb-4 text-sm text-slate-400">Enter the site password to continue.</p>
        <input
          type="password"
          value={pwd}
          onChange={e => setPwd(e.target.value)}
          placeholder="Password"
          autoFocus
          className="mb-3 w-full rounded-lg border border-slate-600 bg-[#0f1117] px-3 py-2 text-slate-100 outline-none focus:border-indigo-500"
        />
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        <button type="submit"
                className="w-full rounded-lg bg-indigo-600 px-3 py-2 font-medium text-white hover:bg-indigo-500">
          Unlock
        </button>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Wrap the app in `App.tsx`**

Add the import at the top of `frontend/src/App.tsx`:

```tsx
import SiteGate from './components/SiteGate'
```

Wrap the returned tree — change `return ( <BrowserRouter> ... </BrowserRouter> )` so `BrowserRouter` is inside `SiteGate`:

```tsx
  return (
    <SiteGate>
      <BrowserRouter>
        <div className="flex h-screen overflow-hidden bg-[#0f1117]">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/"          element={<Dashboard />} />
              <Route path="/backtest"  element={<Backtest />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/paper"     element={<PaperTrade />} />
              <Route path="/patterns"           element={<PatternAnalysis />} />
              <Route path="/patterns/dashboard" element={<PatternDashboard />} />
              <Route path="/smc"       element={<SmcAnalyzer />} />
              <Route path="/settings"  element={<Settings />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </SiteGate>
  )
```

- [ ] **Step 3: Verify compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/SiteGate.tsx frontend/src/App.tsx
git commit -m "feat(deploy): site password login gate on the frontend"
```

---

### Task 6: Frontend — paper WS uses configurable URL + site token

**Files:**
- Modify: `frontend/src/pages/PaperTrade.tsx` (around line 150)
- Verify: `cd frontend && npx tsc --noEmit`

**Interfaces:**
- Consumes: `wsUrl` from `client.ts`.
- Produces: the paper-status WS connects via the absolute funnel URL with the site token appended.

- [ ] **Step 1: Import `wsUrl`**

At the top of `frontend/src/pages/PaperTrade.tsx`, add `wsUrl` to the existing import from the client (or add a new import line):

```tsx
import { wsUrl } from '../api/client'
```

- [ ] **Step 2: Replace the WS construction**

Current (around line 150-151):

```tsx
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/api/v1/paper/ws`)
```

Replace with:

```tsx
      const ws = new WebSocket(wsUrl('/api/v1/paper/ws'))
```

- [ ] **Step 3: Verify compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PaperTrade.tsx
git commit -m "fix(deploy): paper WS targets configurable backend URL with site token"
```

---

### Task 7: k8s manifests (k3s)

**Files:**
- Create: `k8s/namespace.yaml`
- Create: `k8s/configmap.yaml`
- Create: `k8s/secret.example.yaml`
- Create: `k8s/postgres.yaml`
- Create: `k8s/backend.yaml`
- Create: `k8s/kustomization.yaml`
- Create: `k8s/README.md`

**Interfaces:**
- Consumes: the `docker/backend.Dockerfile` image (built + imported as `trading-backend:local`), a hostPath Kronos repo, env from Secret + ConfigMap.
- Produces: `trading` namespace running Postgres (StatefulSet + PVC + headless Service) and the backend (Deployment replicas:1 + NodePort Service on 30080).

- [ ] **Step 1: Create `k8s/namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: trading
```

- [ ] **Step 2: Create `k8s/configmap.yaml`** (non-secret env; edit values for your deploy)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: trading
data:
  # Set to your Vercel origin(s) once known, comma-separated. No trailing slash.
  CORS_ALLOWED_ORIGINS: "https://your-app.vercel.app"
  KRONOS_PATH: "/kronos"
  KRONOS_EAGER_LOAD: "false"
  DEFAULT_SYMBOL: "BTCUSDT"
  DEFAULT_INTERVAL: "5m"
  DEFAULT_LOOKBACK: "400"
  DEFAULT_PRED_LEN: "60"
  DEBUG_ERRORS: "false"
```

- [ ] **Step 3: Create `k8s/secret.example.yaml`** (TEMPLATE — copy to a private file, fill real values, `kubectl apply`; never commit real secrets)

```yaml
# Copy to secret.local.yaml, fill in REAL values, then:
#   kubectl apply -f secret.local.yaml
# secret.local.yaml is gitignored (see k8s/README.md). Do NOT commit secrets.
apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
  namespace: trading
type: Opaque
stringData:
  # Shared site password (the login gate). Generate:
  #   python -c "import secrets; print(secrets.token_urlsafe(24))"
  SITE_ACCESS_TOKEN: "CHANGE_ME_site_password"
  # Admin token for money endpoints. Generate token_urlsafe(32).
  ADMIN_API_TOKEN: "CHANGE_ME_admin_token"
  # JWT secret. Generate token_urlsafe(48).
  JWT_SECRET: "CHANGE_ME_jwt_secret"
  # NVIDIA NIM key for the 9 AI services (optional; AI degrades to 503 if empty).
  NVIDIA_API_KEY: ""
  # Binance keys for LIVE trading only (optional; leave empty for paper/market).
  BINANCE_API_KEY: ""
  BINANCE_SECRET: ""
  # Postgres — must match k8s/postgres.yaml. Password: token_urlsafe(24).
  POSTGRES_PASSWORD: "CHANGE_ME_pg_password"
  DATABASE_URL: "postgresql+asyncpg://trading:CHANGE_ME_pg_password@postgres:5432/trading"
```

- [ ] **Step 4: Create `k8s/postgres.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: trading
spec:
  clusterIP: None          # headless — stable DNS "postgres" for the StatefulSet
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: trading
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          env:
            - name: POSTGRES_USER
              value: trading
            - name: POSTGRES_DB
              value: trading
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: backend-secret
                  key: POSTGRES_PASSWORD
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
  volumeClaimTemplates:
    - metadata:
        name: pgdata
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
```

- [ ] **Step 5: Create `k8s/backend.yaml`**

Replace `KRONOS_HOST_PATH` with the real Kronos repo path on the host (the dir containing `model.py`).

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: trading
spec:
  replicas: 1              # MUST stay 1 — trading engines/scanner are singletons
  strategy:
    type: Recreate         # single-writer DB + singletons: never run 2 pods at once
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: trading-backend:local
          imagePullPolicy: IfNotPresent   # image is imported into k3s, no registry
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secret
          ports:
            - containerPort: 8000
          volumeMounts:
            - name: kronos
              mountPath: /kronos
              readOnly: true
          readinessProbe:
            httpGet:
              path: /
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 20
          resources:
            requests:
              memory: "768Mi"
              cpu: "300m"
            limits:
              memory: "3Gi"     # headroom for Kronos when it lazy-loads
      volumes:
        - name: kronos
          hostPath:
            path: KRONOS_HOST_PATH     # <-- edit: absolute path to Kronos repo on the host
            type: Directory
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: trading
spec:
  type: NodePort
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
      nodePort: 30080      # Tailscale Funnel targets localhost:30080
```

- [ ] **Step 6: Create `k8s/kustomization.yaml`**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - configmap.yaml
  - postgres.yaml
  - backend.yaml
# secret is applied separately from your private secret.local.yaml (not listed here)
```

- [ ] **Step 7: Create `k8s/README.md`**

```markdown
# k8s (k3s) manifests

Single-node k3s deploy of the backend + Postgres. Backend is pinned to
**1 replica** (trading engines + SMC scanner are process-wide singletons).

## Secrets
Never commit real secrets. Copy the template and fill it in:

    cp secret.example.yaml secret.local.yaml   # secret.local.yaml is gitignored
    # edit secret.local.yaml with real values
    kubectl apply -f secret.local.yaml

## Apply everything else

    kubectl apply -k .

See ../docs/DEPLOY.md for the full ordered walkthrough (image build+import,
Tailscale Funnel, Vercel).
```

- [ ] **Step 8: Gitignore the private secret**

Append to the repo root `.gitignore`:

```
k8s/secret.local.yaml
```

- [ ] **Step 9: Validate manifests (no cluster needed)**

Run: `kubectl kustomize k8s/ > /dev/null && echo OK`
Expected: `OK` (kustomize renders without error). If `kubectl` isn't installed yet, skip — this is validated on the host during deploy.

- [ ] **Step 10: Commit**

```bash
git add k8s/ .gitignore
git commit -m "feat(deploy): k3s manifests (backend Deployment, Postgres StatefulSet, gate secrets)"
```

---

### Task 8: Vercel config, env docs, and DEPLOY.md

**Files:**
- Create: `frontend/vercel.json`
- Modify: `.env.example`
- Create: `docs/DEPLOY.md`

**Interfaces:**
- Consumes: everything above.
- Produces: Vercel SPA config + a single ordered deploy runbook.

- [ ] **Step 1: Create `frontend/vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

- [ ] **Step 2: Document the new env vars in `.env.example`**

Append:

```
# ── Public deploy (Vercel + k3s) ────────────────────────────────────────────
# Shared site password. When set, the WHOLE backend requires X-Site-Token
# (paper WS: ?site_token=). Leave empty for open local dev.
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(24))"
SITE_ACCESS_TOKEN=
# Load Kronos at startup. false → lazy-load on first /predict (saves RAM).
KRONOS_EAGER_LOAD=false
# Frontend only (set in the Vercel project, NOT here): absolute backend base URL
# VITE_API_BASE_URL=https://your-pc.your-tailnet.ts.net/api/v1
```

- [ ] **Step 3: Create `docs/DEPLOY.md`**

````markdown
# Deploy: Vercel frontend + k3s backend (home PC) + Tailscale Funnel

Single-operator public deploy. Backend on an always-on home PC (k3s), frontend
on Vercel, connected over a Tailscale Funnel HTTPS URL, locked by one shared
site password. Backend runs **1 replica** (trading engines are singletons).

## Prerequisites (home PC, Linux)
- Docker (to build the image), Tailscale account.
- The Kronos model repo on disk (dir containing `model.py`) — note its absolute path.

## 1. Install k3s
```bash
curl -sfL https://get.k3s.io | sh -
# k3s installs as a systemd service (auto-starts on boot).
sudo k3s kubectl get nodes         # node should be Ready
# convenience: use kubectl without sudo
mkdir -p ~/.kube && sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config \
  && sudo chown $USER ~/.kube/config
export KUBECONFIG=~/.kube/config
```

## 2. Build the backend image and import it into k3s
k3s uses containerd, not Docker, so build then import:
```bash
cd "/media/sun/drive/devops-project/trading app/AI-Trading-Platform"
docker build -f docker/backend.Dockerfile -t trading-backend:local .
docker save trading-backend:local | sudo k3s ctr images import -
```
Re-run these two lines whenever backend code changes, then
`kubectl -n trading rollout restart deploy/backend`.

## 3. Configure manifests
- Edit `k8s/backend.yaml`: set `hostPath.path` (`KRONOS_HOST_PATH`) to the Kronos repo path.
- Edit `k8s/configmap.yaml`: `CORS_ALLOWED_ORIGINS` (fill after step 6 with the real Vercel URL; a placeholder is fine for now).
- Create the secret:
```bash
cd k8s
cp secret.example.yaml secret.local.yaml
# generate values:
python -c "import secrets; print('SITE', secrets.token_urlsafe(24)); print('ADMIN', secrets.token_urlsafe(32)); print('JWT', secrets.token_urlsafe(48)); print('PG', secrets.token_urlsafe(24))"
# paste them into secret.local.yaml (keep DATABASE_URL's password == POSTGRES_PASSWORD)
```

## 4. Deploy
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.local.yaml
kubectl apply -k k8s/
kubectl -n trading get pods -w      # wait for postgres + backend = Running/Ready
```
Fresh DB tables are created automatically on first boot (`alembic upgrade head`
+ `create_tables()`).

Local smoke test before exposing:
```bash
kubectl -n trading port-forward svc/backend 8000:8000 &
curl -s localhost:8000/ ; echo          # {"status":"running",...}
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/market/symbols   # 401 (gate on)
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Site-Token: <SITE_ACCESS_TOKEN>" localhost:8000/api/v1/market/symbols  # 200
kill %1
```

## 5. Expose with Tailscale Funnel
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# enable HTTPS + Funnel for your tailnet in the admin console first (Settings → Funnel).
sudo tailscale funnel 30080          # publishes NodePort 30080 at https://<host>.<tailnet>.ts.net
tailscale funnel status              # shows the public URL
```
Keep it running across reboots — either `sudo tailscale funnel --bg 30080`, or a
systemd unit. Note the public URL, e.g. `https://oldpc.tailXXXX.ts.net`.

Verify publicly:
```bash
curl -s https://<host>.<tailnet>.ts.net/ ; echo     # {"status":"running",...}
```

## 6. Deploy the frontend on Vercel
- Import the GitHub repo in Vercel.
- **Root Directory:** `frontend`
- Framework preset: Vite (vercel.json already sets build/output/rewrites).
- **Environment Variable:** `VITE_API_BASE_URL = https://<host>.<tailnet>.ts.net/api/v1`
- Deploy. Note the assigned URL, e.g. `https://your-app.vercel.app`.

## 7. Close the loop (CORS)
Put the real Vercel origin into the backend and restart:
```bash
kubectl -n trading edit configmap backend-config   # set CORS_ALLOWED_ORIGINS: "https://your-app.vercel.app"
kubectl -n trading rollout restart deploy/backend
```
(Custom domain later? add it comma-separated.)

## 8. Use it
Open the Vercel URL → enter the site password (`SITE_ACCESS_TOKEN`) → dashboards
load. For live trading, also enter the admin token in Settings.

## Operations
- Logs: `kubectl -n trading logs deploy/backend -f`
- Restart: `kubectl -n trading rollout restart deploy/backend`
- Status: `kubectl -n trading get pods`
- Update backend: rebuild+import image (step 2) → rollout restart.
- After a power cut: k3s + pods auto-start; ensure the Tailscale funnel unit does too.

## Gotchas
- **#1: blank/broken frontend** = `VITE_API_BASE_URL` missing or wrong (must include `/api/v1`, no trailing slash) OR `CORS_ALLOWED_ORIGINS` doesn't match the Vercel origin exactly.
- Funnel URL must exist BEFORE the Vercel build (build-time env var).
- 8GB box: keep `KRONOS_EAGER_LOAD=false`; the first `/predict` after boot is slow (model loads then).
- Replicas stay at 1 — do not scale the backend Deployment.
- Home internet down = app down (single-operator uptime bound).
````

- [ ] **Step 4: Commit**

```bash
git add frontend/vercel.json .env.example docs/DEPLOY.md
git commit -m "docs(deploy): Vercel config, env docs, and full DEPLOY runbook"
```

---

### Task 9: Final regression + push

- [ ] **Step 1: Run the full backend test suite**

Run: `cd "/media/sun/drive/devops-project/trading app/AI-Trading-Platform" && PYTHONPATH=. .venv/bin/python -m pytest tests/ -q`
Expected: all pass (or same baseline as before this work — no NEW failures). If any pre-existing failures are unrelated (e.g. live-Binance network tests), note them.

- [ ] **Step 2: Frontend typecheck + build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: clean typecheck, successful build.

- [ ] **Step 3: Push**

```bash
git push
```

---

## Notes for the executor
- All gates default OPEN when their env var is unset, so `./run.sh` local dev is unchanged — you can develop/test without setting `SITE_ACCESS_TOKEN`.
- Tasks 1-3 are backend (TDD, pytest). Tasks 4-6 are frontend (verify via `tsc --noEmit`). Tasks 7-8 are infra/config (validate via `kubectl kustomize`, no live cluster needed to write them). Task 9 is the final gate.
- The k8s apply + Tailscale + Vercel steps in Task 8's DEPLOY.md run on the actual home PC — not in this dev environment. The plan's job is to produce correct, tested manifests + an exact runbook.
