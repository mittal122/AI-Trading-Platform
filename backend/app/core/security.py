"""Password hashing + JWT encode/decode. No business logic — pure crypto helpers."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from backend.app.core.saas_config import saas_config

_BCRYPT_MAX_BYTES = 72  # bcrypt's own input limit


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    truncated = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(truncated, hashed_password.encode("utf-8"))


def _require_secret() -> str:
    if not saas_config.JWT_SECRET:
        raise RuntimeError("JWT_SECRET environment variable not set")
    return saas_config.JWT_SECRET


def create_access_token(user_id: int, email: str, tier: str = "free") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=saas_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "tier": tier, "type": "access", "exp": expire}
    return jwt.encode(payload, _require_secret(), algorithm=saas_config.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=saas_config.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, _require_secret(), algorithm=saas_config.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _require_secret(), algorithms=[saas_config.JWT_ALGORITHM])
    except JWTError:
        return None


def generate_api_key() -> str:
    return f"{saas_config.API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    """API keys are long random tokens, not user passwords — a fast, uniform
    hash (no per-call cost factor) keeps API-key auth latency low."""
    import hashlib

    return hashlib.sha256(raw_key.encode()).hexdigest()
