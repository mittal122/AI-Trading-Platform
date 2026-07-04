"""
Per-tier rate limiting via slowapi.

slowapi's dynamic-limit callable only ever receives the *rate-limit key*
string (not the Request object) — it inspects the callable's parameter name
and only forwards data if that parameter is literally named `key`. So the
tier is encoded directly into the key by rate_limit_key(), and
tier_rate_limit() parses it back out. See slowapi/wrappers.py LimitGroup.__iter__.

Tier is read from the JWT access-token claim (no DB hit per request). Requests
without a valid token are keyed by IP and rate-limited at the free tier.
"""

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.core.saas_config import saas_config
from backend.app.core.security import decode_token

# Blanket per-key ceiling applied to EVERY route via SlowAPIMiddleware — a
# DoS/cost backstop for the expensive, otherwise-unlimited endpoints
# (pattern dashboard, market overview, Kronos predict, backtest). Generous
# enough that no real user hits it; a scraper or fan-out abuser does. The
# per-tier @limiter.limit decorators still layer stricter caps on specific
# routes on top of this. Env-overridable.
GLOBAL_RATE_LIMIT = os.getenv("GLOBAL_RATE_LIMIT", "240/minute")

_TIER_LIMITS = {
    "free": saas_config.RATE_LIMIT_FREE,
    "pro": saas_config.RATE_LIMIT_PRO,
    "enterprise": saas_config.RATE_LIMIT_ENTERPRISE,
}


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:]
    return None


def rate_limit_key(request: Request) -> str:
    """Rate-limit bucket key — per-user when authenticated, else per-IP.
    Tier is embedded as a trailing segment so tier_rate_limit() can read it
    back without needing the Request object."""
    token = _extract_bearer_token(request)
    if token:
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            tier = payload.get("tier", "free")
            return f"user:{payload['sub']}:{tier}"
    return f"ip:{get_remote_address(request)}:free"


def tier_rate_limit(key: str) -> str:
    """Dynamic limit string — slowapi passes the key from rate_limit_key()."""
    tier = key.rsplit(":", 1)[-1]
    return _TIER_LIMITS.get(tier, _TIER_LIMITS["free"])


limiter = Limiter(key_func=rate_limit_key, default_limits=[GLOBAL_RATE_LIMIT])
