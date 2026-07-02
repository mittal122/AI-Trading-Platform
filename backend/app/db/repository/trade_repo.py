from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Trade


class TradeRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, trade: Trade) -> Trade:
        self._session.add(trade)
        await self._session.commit()
        await self._session.refresh(trade)
        return trade

    async def get_history(
        self,
        symbol: str | None = None,
        strategy: str | None = None,
        mode: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[Trade]]:
        stmt = select(Trade).order_by(Trade.created_at.desc())
        count_stmt = select(func.count()).select_from(Trade)

        if symbol:
            stmt = stmt.where(Trade.symbol == symbol.upper())
            count_stmt = count_stmt.where(Trade.symbol == symbol.upper())
        if strategy:
            stmt = stmt.where(Trade.strategy == strategy)
            count_stmt = count_stmt.where(Trade.strategy == strategy)
        if mode:
            stmt = stmt.where(Trade.mode == mode.upper())
            count_stmt = count_stmt.where(Trade.mode == mode.upper())

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return total, list(rows)

    async def get_by_id(self, trade_id: int) -> Trade | None:
        return await self._session.get(Trade, trade_id)

    async def count_by_mode(self, mode: str) -> int:
        stmt = select(func.count()).select_from(Trade).where(Trade.mode == mode.upper())
        return (await self._session.execute(stmt)).scalar_one()
