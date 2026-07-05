"""Repository for the SMC scanner tables (watchlist / settings / signals)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import SmcScannerSettings, SmcSignal, SmcWatch


class SmcScannerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ----- watchlist -----
    async def list_watches(self, active_only: bool = False) -> list[SmcWatch]:
        stmt = select(SmcWatch)
        if active_only:
            stmt = stmt.where(SmcWatch.active == 1)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_watch(self, symbol: str, interval: str) -> SmcWatch | None:
        stmt = select(SmcWatch).where(
            SmcWatch.symbol == symbol.upper(), SmcWatch.interval == interval)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add_watch(self, symbol: str, interval: str) -> SmcWatch:
        existing = await self.get_watch(symbol, interval)
        if existing:
            existing.active = 1
            await self.session.commit()
            return existing
        watch = SmcWatch(symbol=symbol.upper(), interval=interval, active=1)
        self.session.add(watch)
        await self.session.commit()
        await self.session.refresh(watch)
        return watch

    async def set_active(self, watch_id: int, active: bool) -> SmcWatch | None:
        w = await self.session.get(SmcWatch, watch_id)
        if w:
            w.active = 1 if active else 0
            await self.session.commit()
        return w

    async def remove_watch(self, watch_id: int) -> bool:
        w = await self.session.get(SmcWatch, watch_id)
        if not w:
            return False
        await self.session.delete(w)
        await self.session.commit()
        return True

    async def update_cursor(self, watch_id: int, candle_time: str) -> None:
        w = await self.session.get(SmcWatch, watch_id)
        if w:
            w.last_scanned_candle_time = candle_time
            await self.session.commit()

    # ----- settings (single row) -----
    async def get_settings(self) -> SmcScannerSettings:
        row = (await self.session.execute(select(SmcScannerSettings))).scalars().first()
        if row is None:
            row = SmcScannerSettings(enabled=0, max_signals_per_week=4)
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
        return row

    async def update_settings(self, enabled: bool, max_per_week: int) -> SmcScannerSettings:
        row = await self.get_settings()
        row.enabled = 1 if enabled else 0
        row.max_signals_per_week = max_per_week
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    # ----- signals -----
    async def list_signals(self, limit: int = 100) -> list[SmcSignal]:
        stmt = select(SmcSignal).order_by(SmcSignal.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_signal(self, signal_id: int) -> SmcSignal | None:
        return await self.session.get(SmcSignal, signal_id)

    async def count_signals_since(self, since: datetime) -> int:
        stmt = select(SmcSignal).where(SmcSignal.created_at >= since)
        return len(list((await self.session.execute(stmt)).scalars().all()))

    async def has_live_duplicate(self, symbol: str, interval: str, side: str,
                                 within_hours: int) -> bool:
        since = datetime.now(timezone.utc) - timedelta(hours=within_hours)
        stmt = select(SmcSignal).where(
            SmcSignal.symbol == symbol.upper(),
            SmcSignal.interval == interval,
            SmcSignal.side == side,
            SmcSignal.status.in_(("new", "accepted")),
            SmcSignal.created_at >= since,
        )
        return (await self.session.execute(stmt)).scalars().first() is not None

    async def save_signal(self, signal: SmcSignal) -> SmcSignal:
        self.session.add(signal)
        await self.session.commit()
        await self.session.refresh(signal)
        return signal

    async def update_signal(self, signal: SmcSignal) -> SmcSignal:
        await self.session.commit()
        await self.session.refresh(signal)
        return signal
