"""
DatabaseService — thin async wrapper around trade + backtest repositories.

Usage (from async context):
    async with DatabaseService() as svc:
        trade = await svc.save_trade(...)
        runs = await svc.get_backtest_history()
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import BacktestRun, Trade
from backend.app.db.repository.backtest_repo import BacktestRepository
from backend.app.db.repository.trade_repo import TradeRepository


class DatabaseService:
    """Context manager that opens one session per logical operation."""

    @asynccontextmanager
    async def _session(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def save_trade(
        self,
        symbol: str,
        strategy: str,
        mode: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        exit_reason: str = "",
        entry_timestamp: str = "",
        direction: str = "BUY",
    ) -> Trade:
        pnl_percent = ((exit_price - entry_price) / entry_price * 100) if entry_price else 0.0
        now = datetime.now(timezone.utc).isoformat()

        record = Trade(
            symbol=symbol.upper(),
            strategy=strategy,
            direction=direction,
            mode=mode.upper(),
            entry_price=round(entry_price, 8),
            exit_price=round(exit_price, 8),
            quantity=round(quantity, 8),
            pnl=round(pnl, 8),
            pnl_percent=round(pnl_percent, 4),
            exit_reason=exit_reason,
            entry_timestamp=entry_timestamp,
            exit_timestamp=now,
        )

        async with self._session() as session:
            repo = TradeRepository(session)
            return await repo.save(record)

    async def get_trade_history(
        self,
        symbol: str | None = None,
        strategy: str | None = None,
        mode: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[Trade]]:
        async with self._session() as session:
            repo = TradeRepository(session)
            return await repo.get_history(
                symbol=symbol,
                strategy=strategy,
                mode=mode,
                limit=limit,
                offset=offset,
            )

    async def save_backtest_run(
        self,
        strategy: str,
        symbol: str,
        interval: str,
        limit: int,
        initial_balance: float,
        final_balance: float,
        total_return: float,
        total_trades: int,
        win_rate: float,
        profit_factor: float,
        sharpe_ratio: float,
        max_drawdown: float,
        winning_trades: int = 0,
        losing_trades: int = 0,
        avg_win: float = 0.0,
        avg_loss: float = 0.0,
        expectancy: float = 0.0,
        sortino_ratio: float = 0.0,
        calmar_ratio: float = 0.0,
    ) -> BacktestRun:
        record = BacktestRun(
            strategy=strategy,
            symbol=symbol.upper(),
            interval=interval,
            limit=limit,
            initial_balance=round(initial_balance, 4),
            final_balance=round(final_balance, 4),
            total_return=round(total_return, 4),
            total_trades=total_trades,
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            max_drawdown=round(max_drawdown, 4),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=round(avg_win, 4),
            avg_loss=round(avg_loss, 4),
            expectancy=round(expectancy, 4),
            sortino_ratio=round(sortino_ratio, 4),
            calmar_ratio=round(calmar_ratio, 4),
        )
        async with self._session() as session:
            repo = BacktestRepository(session)
            return await repo.save(record)

    async def get_backtest_history(
        self,
        strategy: str | None = None,
        symbol: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, list[BacktestRun]]:
        async with self._session() as session:
            repo = BacktestRepository(session)
            return await repo.get_recent(strategy=strategy, symbol=symbol, limit=limit, offset=offset)

    async def delete_backtest_run(self, run_id: int) -> bool:
        async with self._session() as session:
            repo = BacktestRepository(session)
            return await repo.delete_by_id(run_id)

    async def delete_all_backtest_runs(self) -> int:
        async with self._session() as session:
            repo = BacktestRepository(session)
            return await repo.delete_all()
