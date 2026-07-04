"""Shared FastAPI dependencies — auth (JWT or API key) and tier gating."""

import hmac
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.security import decode_token
from backend.app.core.security_config import security_config
from backend.app.db.models import User
from backend.app.services.auth.auth_service import auth_service

_bearer = HTTPBearer(auto_error=False)

_TIER_RANK = {"free": 0, "pro": 1, "enterprise": 2}


async def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Gate money-critical endpoints (exchange keys, live trading, mass
    delete). If ADMIN_API_TOKEN is unset the gate is open — preserving the
    single-operator localhost default. If set, the request must carry a
    matching X-Admin-Token header (constant-time compared). This is the
    minimum lock that lets the app be deployed on a public host without
    exposing real-money actions to anonymous callers, until full per-user
    auth exists."""
    if not security_config.admin_gate_enabled:
        return
    if not x_admin_token or not hmac.compare_digest(x_admin_token, security_config.ADMIN_API_TOKEN):
        raise HTTPException(status_code=401, detail="Admin token required for this action")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    x_api_key: Optional[str] = Header(default=None),
) -> User:
    """Authenticate via JWT bearer token OR X-API-Key header — either is accepted."""

    if x_api_key:
        user = await auth_service.authenticate_api_key(x_api_key)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return user

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await auth_service.get_user_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return user


def require_tier(min_tier: str):
    """Dependency factory — gate an endpoint to a minimum subscription tier."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if _TIER_RANK.get(user.tier, 0) < _TIER_RANK.get(min_tier, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Requires '{min_tier}' tier or higher (current: '{user.tier}')",
            )
        return user

    return _check
