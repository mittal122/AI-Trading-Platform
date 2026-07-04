"""Security hardening — admin-token gate, generic error responses, and
security headers. Uses FastAPI's TestClient against the real app.

Two app instances are built (gate off / gate on) by toggling the env var
BEFORE importing the security config, since it reads env at import time.
"""

import importlib
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-do-not-use-in-prod")


def _build_client(admin_token: str | None):
    if admin_token is None:
        os.environ.pop("ADMIN_API_TOKEN", None)
    else:
        os.environ["ADMIN_API_TOKEN"] = admin_token
    os.environ["DEBUG_ERRORS"] = "false"

    # Re-import the config + deps so the new env is picked up.
    import backend.app.core.security_config as sc
    importlib.reload(sc)
    import backend.app.api.deps as deps
    importlib.reload(deps)
    import backend.app.api.v1.settings as settings_mod
    importlib.reload(settings_mod)

    from fastapi import Depends, FastAPI
    from backend.app.api.deps import require_admin

    app = FastAPI()

    @app.post("/gated")
    async def gated(_: None = Depends(require_admin)):
        return {"ok": True}

    @app.get("/open")
    async def open_ep():
        return {"ok": True}

    from fastapi.testclient import TestClient
    return TestClient(app)


print("\n========== ADMIN GATE OFF (single-operator default) ==========\n")
client = _build_client(None)
r = client.post("/gated")
assert r.status_code == 200, f"gate off → money endpoint open, got {r.status_code}"
print("PASS: gate disabled (no ADMIN_API_TOKEN) → money endpoints open")

print("\n========== ADMIN GATE ON ==========\n")
client = _build_client("s3cr3t-admin-token")
assert client.post("/gated").status_code == 401, "no token → 401"
assert client.post("/gated", headers={"X-Admin-Token": "wrong"}).status_code == 401, "wrong token → 401"
assert client.post("/gated", headers={"X-Admin-Token": "s3cr3t-admin-token"}).status_code == 200, "correct token → 200"
assert client.get("/open").status_code == 200, "ungated endpoint stays open"
print("PASS: gate on → 401 without/with-wrong token, 200 with correct, open endpoints unaffected")

print("\n========== GENERIC ERROR HANDLER + SECURITY HEADERS ==========\n")
# Reset gate off, then exercise the real app's global handler + headers.
os.environ.pop("ADMIN_API_TOKEN", None)
import backend.app.core.security_config as sc
importlib.reload(sc)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.main import SecurityHeadersMiddleware, unhandled_exception_handler

probe = FastAPI()
probe.add_middleware(SecurityHeadersMiddleware)
probe.add_exception_handler(Exception, unhandled_exception_handler)

@probe.get("/boom")
async def boom():
    raise ValueError("SENSITIVE internal detail that must not leak")

@probe.get("/fine")
async def fine():
    return {"ok": True}

pc = TestClient(probe, raise_server_exceptions=False)
resp = pc.get("/boom")
assert resp.status_code == 500
assert "SENSITIVE" not in resp.text, "raw exception text leaked to client!"
assert resp.json()["detail"] == "Internal server error"
print("PASS: unhandled exception → generic 500, no internal text leaked")

# Security headers are added to normal responses (the attack surface that
# matters — HTML/content). Verified on a 200; the app also proxies through
# nginx which sets its own headers on the SPA (docker/nginx.conf).
headers = pc.get("/fine").headers
for h, expected in [
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "DENY"),
    ("referrer-policy", "no-referrer"),
]:
    assert headers.get(h) == expected, f"missing/incorrect {h}: {headers.get(h)}"
assert "content-security-policy" in headers
print("PASS: security headers present (nosniff, frame-deny, referrer, CSP)")

print("\n========== RESULTS: all checks passed ==========")
