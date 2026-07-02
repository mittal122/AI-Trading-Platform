from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BacktestRun


class BacktestRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: BacktestRun) -> BacktestRun:
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def get_recent(
        self,
        strategy: str | None = None,
        symbol: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, list[BacktestRun]]:
        stmt = select(BacktestRun).order_by(BacktestRun.created_at.desc())
        count_stmt = select(func.count()).select_from(BacktestRun)

        if strategy:
            stmt = stmt.where(BacktestRun.strategy == strategy)
            count_stmt = count_stmt.where(BacktestRun.strategy == strategy)
        if symbol:
            stmt = stmt.where(BacktestRun.symbol == symbol.upper())
            count_stmt = count_stmt.where(BacktestRun.symbol == symbol.upper())

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return total, list(rows)

    async def get_by_id(self, run_id: int) -> BacktestRun | None:
        return await self._session.get(BacktestRun, run_id)

    async def delete_by_id(self, run_id: int) -> bool:
        run = await self._session.get(BacktestRun, run_id)
        if run is None:
            return False
        await self._session.delete(run)
        await self._session.commit()
        return True

    async def delete_all(self) -> int:
        count_stmt = select(func.count()).select_from(BacktestRun)
        total = (await self._session.execute(count_stmt)).scalar_one()
        await self._session.execute(delete(BacktestRun))
        await self._session.commit()
        return total
