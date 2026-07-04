"""Password hashing + JWT encode/decode. No business logic — pure crypto helpers."""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet
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


def _fernet() -> Fernet:
    """Symmetric encryption for secrets that must be recoverable in plaintext
    (e.g. exchange API secrets, passed to a broker SDK) — unlike passwords or
    platform API keys above, a one-way hash won't work here.

    Keyed off ENCRYPTION_KEY if set, else derived from JWT_SECRET so no extra
    required env var — either way the key must stay stable across restarts or
    previously-encrypted secrets become unrecoverable."""
    raw_key = os.getenv("ENCRYPTION_KEY") or saas_config.JWT_SECRET
    if not raw_key:
        raise RuntimeError("ENCRYPTION_KEY or JWT_SECRET must be set to store exchange credentials")
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
