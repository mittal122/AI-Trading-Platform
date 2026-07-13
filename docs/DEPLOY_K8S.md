# Deploy to Kubernetes — manual step-by-step (kubectl, no Helm)

Deploys the full stack (postgres + backend + frontend) from the published
Docker Hub images using one manifest: `k8s/aitrading.yaml`. Works on any
cluster — kind, minikube, k3s, or a cloud one. ~10 minutes.

```
browser → port-forward/ingress → frontend (nginx :8080)
                                    └→ /api → backend (:8000) → postgres (:5432, PVC)
```

## Prerequisites

- `kubectl` pointing at a cluster (`kubectl get nodes` shows Ready).
- Internet on the nodes (they pull images from Docker Hub), OR pre-load
  images for kind (step 2).

## Step 1 — Namespace

```bash
kubectl create namespace aitrading
```

## Step 2 — (kind/minikube only) pre-load the images

Skip on a cloud cluster — nodes pull from Docker Hub themselves.

```bash
# kind (snap-docker users: keep the TMPDIR override)
docker pull mittal122/ai-trading-backend:v1.0.4
docker pull mittal122/ai-trading-frontend:v1.0.4
docker pull mittal122/ai-trading-postgres:17-alpine-r1
mkdir -p ~/kind-tmp
TMPDIR=~/kind-tmp kind load docker-image \
  mittal122/ai-trading-backend:v1.0.4 \
  mittal122/ai-trading-frontend:v1.0.4 \
  mittal122/ai-trading-postgres:17-alpine-r1 \
  --name <your-cluster-name>

# minikube instead:
# minikube image load mittal122/ai-trading-backend:v1.0.4   (etc.)
```

## Step 3 — Create the secrets (never commit these)

One password shared by the DB and the backend's connection URL:

```bash
PW=$(python3 -c "import secrets; print(secrets.token_hex(16))")
JWT=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

kubectl create secret generic aitrading-secrets -n aitrading \
  --from-literal=POSTGRES_PASSWORD="$PW" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://trading:${PW}@postgres:5432/trading" \
  --from-literal=JWT_SECRET="$JWT"
```

Why this shape matters:
- host is `postgres` — the Service name from the manifest, resolved by
  cluster DNS. Never `localhost`.
- the password appears in BOTH places (DB init + backend URL) and must be
  URL-safe (hex is), or SQLAlchemy fails to parse the URL.

## Step 4 — Apply the manifest

```bash
kubectl apply -f k8s/aitrading.yaml
```

What it creates, in order:
| Object | Purpose |
|---|---|
| PVC `pgdata` (1Gi) | permanent disk — trades survive pod restarts |
| Deployment+Service `postgres` | DB, runs as uid 70, `pg_isready` probe, fsGroup 70 for volume perms |
| Deployment+Service `backend` | FastAPI; runs `alembic upgrade head` on boot → creates the whole schema on the empty DB; probe on `/docs` |
| Deployment+Service `frontend` | nginx serving the SPA and proxying `/api` → `backend` (auto-resolves the namespace-qualified DNS name — that's the v1.0.4 image fix) |

## Step 5 — Wait for green

```bash
kubectl wait --for=condition=ready pod -l app=postgres -n aitrading --timeout=120s
kubectl wait --for=condition=ready pod -l app=backend  -n aitrading --timeout=180s
kubectl wait --for=condition=ready pod -l app=frontend -n aitrading --timeout=120s
kubectl get pods -n aitrading
```

Normal: the backend may restart 1-2 times while postgres initializes —
Kubernetes retries it into readiness. Worry only if it loops for minutes
(`kubectl logs -n aitrading deploy/backend` shows the real error).

## Step 6 — Verify like a user (not just "Running")

```bash
kubectl port-forward -n aitrading svc/frontend 8080:8080 &

curl -s -o /dev/null -w "SPA:      %{http_code}\n" http://localhost:8080/
curl -s -o /dev/null -w "API:      %{http_code}\n" http://localhost:8080/api/v1/market/overview
curl -s -o /dev/null -w "DB path:  %{http_code}\n" "http://localhost:8080/api/v1/trades/history?limit=1"
```

All three `200` → the whole chain works (browser → nginx → backend →
postgres + live Binance data). Open http://localhost:8080 for the UI.

Also confirm the schema built itself:
```bash
kubectl logs -n aitrading deploy/backend | grep alembic | head
```

## Step 7 — Expose it properly (optional)

Port-forward is for testing. For real access pick one:
- **NodePort**: `kubectl patch svc frontend -n aitrading -p '{"spec":{"type":"NodePort"}}'`
  then `kubectl get svc frontend -n aitrading` for the port.
- **Ingress**: create an Ingress routing your hostname → `frontend:8080`
  (needs an ingress controller installed).

## Troubleshooting map (each of these actually happened)

| Symptom | Cause → fix |
|---|---|
| `CreateContainerConfigError: non-numeric user` | image `USER` must be a numeric UID for runAsNonRoot (fixed in v1.0.2+) |
| postgres: "superuser password is not specified" | `POSTGRES_PASSWORD` secret missing — redo Step 3 |
| backend: "Could not parse SQLAlchemy URL" | malformed `DATABASE_URL` — regenerate exactly as in Step 3 |
| `/api` returns 502 | frontend older than v1.0.4 (nginx can't resolve bare `backend` under CoreDNS) — use v1.0.4 |
| postgres crash on volume perms | pod needs `fsGroup: 70` (already in the manifest) |

## Tear down

```bash
kubectl delete namespace aitrading   # removes everything incl. the DB volume
```

## Update to a new version

```bash
kubectl set image -n aitrading deployment/backend  backend=mittal122/ai-trading-backend:vX.Y.Z
kubectl set image -n aitrading deployment/frontend frontend=mittal122/ai-trading-frontend:vX.Y.Z
kubectl rollout status -n aitrading deployment/backend
# roll back if bad: kubectl rollout undo deployment/backend -n aitrading
```
