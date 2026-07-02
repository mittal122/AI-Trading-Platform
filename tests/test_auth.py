"""
Phase 10 — SaaS auth, API keys, and rate-limit tests.

Uses SQLite in-memory-backed AsyncSessionLocal patch — no real DB required.
Requires JWT_SECRET env var (set below for the test run only).

Run: PYTHONPATH=. JWT_SECRET=test-secret .venv/bin/python tests/test_auth.py
"""

import asyncio
import os
import sys

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")

from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.core.security import (
    create_access_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from backend.app.db.database import Base
from backend.app.db import models  # noqa: F401

_engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def test_password_hashing():
    print("\n--- Password hashing ---")
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)
    print("PASS")


def test_jwt_roundtrip():
    print("\n--- JWT create + decode ---")
    token = create_access_token(user_id=42, email="test@example.com", tier="pro")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "test@example.com"
    assert payload["tier"] == "pro"
    assert payload["type"] == "access"
    print(f"  Claims: sub={payload['sub']} tier={payload['tier']}")
    print("PASS")


def test_jwt_invalid_token_rejected():
    print("\n--- JWT invalid token rejected ---")
    assert decode_token("not-a-real-token") is None
    print("PASS")


def test_api_key_generation():
    print("\n--- API key generation ---")
    key = generate_api_key()
    assert key.startswith("sk_live_")
    assert len(key) > 20

    h1 = hash_api_key(key)
    h2 = hash_api_key(key)
    assert h1 == h2  # deterministic
    assert h1 != key
    print(f"  Key prefix: {key[:16]}...")
    print("PASS")


async def test_auth_service_register_login():
    print("\n--- AuthService register + login (in-memory DB) ---")
    import backend.app.services.auth.auth_service as auth_module

    with patch.object(auth_module, "AsyncSessionLocal", _SessionLocal):
        svc = auth_module.AuthService()

        user = await svc.register("newuser@example.com", "supersecret123")
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.tier == "free"
        print(f"  Registered user id={user.id}")

        # duplicate registration should fail
        try:
            await svc.register("newuser@example.com", "anotherpass")
            assert False, "expected AuthError on duplicate email"
        except auth_module.AuthError:
            pass
        print("  Duplicate email correctly rejected")

        # login success
        tokens = await svc.login("newuser@example.com", "supersecret123")
        assert tokens.access_token
        assert tokens.refresh_token
        print("  Login succeeded, tokens issued")

        # login wrong password
        try:
            await svc.login("newuser@example.com", "wrongpass")
            assert False, "expected AuthError on wrong password"
        except auth_module.AuthError:
            pass
        print("  Wrong password correctly rejected")

        # refresh
        new_tokens = await svc.refresh(tokens.refresh_token)
        assert new_tokens.access_token
        print("  Refresh succeeded")

    print("PASS")


async def test_api_key_lifecycle():
    print("\n--- API key create/list/revoke (in-memory DB) ---")
    import backend.app.services.auth.auth_service as auth_module

    with patch.object(auth_module, "AsyncSessionLocal", _SessionLocal):
        svc = auth_module.AuthService()
        user = await svc.register("apikeyuser@example.com", "supersecret123")

        record, raw_key = await svc.create_api_key(user.id, "My CI Key")
        assert raw_key.startswith("sk_live_")
        assert record.key_prefix == raw_key[:16]
        print(f"  Created key id={record.id} prefix={record.key_prefix}")

        keys = await svc.list_api_keys(user.id)
        assert len(keys) == 1

        # authenticate via raw key
        authed_user = await svc.authenticate_api_key(raw_key)
        assert authed_user is not None
        assert authed_user.id == user.id
        print("  API key authentication succeeded")

        # wrong key fails
        bad_user = await svc.authenticate_api_key("sk_live_totally_bogus_key_value")
        assert bad_user is None
        print("  Bogus key correctly rejected")

        # revoke
        ok = await svc.revoke_api_key(user.id, record.id)
        assert ok
        revoked_auth = await svc.authenticate_api_key(raw_key)
        assert revoked_auth is None
        print("  Revoked key no longer authenticates")

    print("PASS")


def test_rate_limit_tier_resolution():
    print("\n--- Rate limit tier resolution ---")
    from starlette.requests import Request

    from backend.app.core.rate_limit import rate_limit_key, tier_rate_limit
    from backend.app.core.saas_config import saas_config

    # tier_rate_limit(key) — slowapi only ever passes it the key string produced
    # by rate_limit_key(request), never the Request itself (see rate_limit.py
    # docstring). Both stages are exercised here to match real usage.
    token = create_access_token(user_id=1, email="x@example.com", tier="enterprise")

    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "method": "GET",
        "path": "/",
    }
    req = Request(scope)
    key = rate_limit_key(req)
    assert key == "user:1:enterprise"
    limit = tier_rate_limit(key)
    assert limit == saas_config.RATE_LIMIT_ENTERPRISE
    print(f"  Enterprise tier → key={key} limit={limit}")

    # no auth header → free tier default, keyed by IP
    scope_anon = {"type": "http", "headers": [], "method": "GET", "path": "/", "client": ("127.0.0.1", 1234)}
    req_anon = Request(scope_anon)
    key_anon = rate_limit_key(req_anon)
    limit_anon = tier_rate_limit(key_anon)
    assert limit_anon == saas_config.RATE_LIMIT_FREE
    print(f"  Anonymous → key={key_anon} limit={limit_anon}")

    print("PASS")


async def main():
    await _setup()

    sync_tests = [
        test_password_hashing,
        test_jwt_roundtrip,
        test_jwt_invalid_token_rejected,
        test_api_key_generation,
        test_rate_limit_tier_resolution,
    ]
    async_tests = [
        test_auth_service_register_login,
        test_api_key_lifecycle,
    ]

    passed = 0
    failed = 0

    for t in sync_tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    for t in async_tests:
        try:
            await t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n========== RESULTS: {passed} passed, {failed} failed ==========")
    return failed


if __name__ == "__main__":
    failures = asyncio.run(main())
    sys.exit(0 if failures == 0 else 1)
