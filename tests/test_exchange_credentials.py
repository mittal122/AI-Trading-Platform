"""Exchange credentials — encryption roundtrip + DB CRUD.

Uses an isolated in-memory SQLite engine, not the project's default
trading.db, so this never touches real data.
"""

import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-do-not-use-in-prod")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.core.security import decrypt_secret, encrypt_secret
from backend.app.db.database import Base
from backend.app.db.repository.credentials_repo import CredentialsRepository


def test_encrypt_decrypt_roundtrip():
    secret = "super-secret-binance-value-123"
    ciphertext = encrypt_secret(secret)
    assert ciphertext != secret
    assert decrypt_secret(ciphertext) == secret
    print("PASS: encrypt/decrypt roundtrip")


async def _run_repo_checks():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    from backend.app.db import models  # noqa: F401 — registers models with Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        repo = CredentialsRepository(session)

        assert await repo.get("binance") is None

        record = await repo.upsert("binance", "enc-key-1", "enc-secret-1", "AKIA****1234")
        assert record.exchange == "binance"
        assert record.key_preview == "AKIA****1234"

        fetched = await repo.get("binance")
        assert fetched is not None
        assert fetched.api_key_encrypted == "enc-key-1"

        updated = await repo.upsert("binance", "enc-key-2", "enc-secret-2", "AKIA****5678")
        assert updated.api_key_encrypted == "enc-key-2"

        deleted = await repo.delete("binance")
        assert deleted is True
        assert await repo.get("binance") is None
        assert await repo.delete("binance") is False

    print("PASS: CredentialsRepository upsert/get/delete")


def test_repository_crud():
    asyncio.run(_run_repo_checks())


def test_provider_uses_configured_credentials():
    """Settings-page keys must reach every provider instance, old and new."""
    from backend.app.services.providers import binance_provider
    from backend.app.services.providers.binance_provider import BinanceProvider, configure_credentials

    provider = BinanceProvider()  # created BEFORE keys are saved
    configure_credentials("user-key", "user-secret")
    assert provider.client.API_KEY == "user-key", "existing instance must pick up new keys"
    assert BinanceProvider().client.API_KEY == "user-key"

    configure_credentials()  # delete path — env fallback or keyless
    import os
    expected = os.getenv("BINANCE_API_KEY") or None
    assert provider.client.API_KEY == expected
    binance_provider._shared_client = None  # don't leak test keys into other tests
    print("PASS: configure_credentials reaches shared client")


if __name__ == "__main__":
    test_encrypt_decrypt_roundtrip()
    test_repository_crud()
    test_provider_uses_configured_credentials()
    print("\nRESULTS: all checks passed")
