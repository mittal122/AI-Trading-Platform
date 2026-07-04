"""Deployment-hardening switches — all opt-in via env so the default
single-operator localhost experience is unchanged, but a real deployment
can lock the money-touching endpoints and stop leaking internals."""

import os


def _flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class SecurityConfig:
    # When ADMIN_API_TOKEN is set, the money-critical endpoints (exchange-key
    # management, live-trading start/stop, mass-delete) require a matching
    # X-Admin-Token header. Unset → those endpoints stay open (dev default).
    # This is a deliberate stopgap for single-operator deployments until a
    # full per-user auth UI exists (documented Phase 10 gap) — it lets you
    # put the app on a public host without exposing "start real trading" and
    # "overwrite my Binance keys" to anonymous callers.
    ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "").strip()

    # Return real exception text in HTTP error bodies. OFF in production —
    # exception strings leak DB constraints, dependency internals, upstream
    # (Binance/LLM/Stripe) error detail. Server logs always keep the full
    # error regardless.
    DEBUG_ERRORS = _flag("DEBUG_ERRORS", default=False)

    @property
    def admin_gate_enabled(self) -> bool:
        return bool(self.ADMIN_API_TOKEN)


security_config = SecurityConfig()
