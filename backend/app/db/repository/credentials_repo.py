from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ExchangeCredentials


class CredentialsRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        exchange: str,
        api_key_encrypted: str,
        api_secret_encrypted: str,
        key_preview: str,
    ) -> ExchangeCredentials:
        existing = await self.get(exchange)
        if existing:
            existing.api_key_encrypted = api_key_encrypted
            existing.api_secret_encrypted = api_secret_encrypted
            existing.key_preview = key_preview
            existing.updated_at = datetime.now(timezone.utc)
        else:
            existing = ExchangeCredentials(
                exchange=exchange,
                api_key_encrypted=api_key_encrypted,
                api_secret_encrypted=api_secret_encrypted,
                key_preview=key_preview,
            )
            self._session.add(existing)
        await self._session.commit()
        await self._session.refresh(existing)
        return existing

    async def get(self, exchange: str) -> ExchangeCredentials | None:
        stmt = select(ExchangeCredentials).where(ExchangeCredentials.exchange == exchange)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def delete(self, exchange: str) -> bool:
        existing = await self.get(exchange)
        if existing is None:
            return False
        await self._session.delete(existing)
        await self._session.commit()
        return True
