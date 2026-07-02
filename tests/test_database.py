"""
Phase 8 — Database Integration tests.

Uses SQLite in-memory — no PostgreSQL required.
Run: PYTHONPATH=. .venv/bin/python tests/test_database.py
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.db import models  # noqa: F401 — registers models
from backend.app.db.database import Base
from backend.app.db.models import BacktestRun, Trade
from backend.app.db.repository.backtest_repo import BacktestRepository
from backend.app.db.repository.trade_repo import TradeRepository

# In-memory SQLite for tests — no external DB required
_TEST_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(_TEST_URL, connect_args={"check_same_thread": False})
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def test_save_and_query_trade():
    print("\n--- Save + query Trade ---")
    async with _SessionLocal() as session:
        repo = TradeRepository(session)

        trade = Trade(
            symbol="BTCUSDT",
            strategy="rsi",
            direction="BUY",
            mode="PAPER",
            entry_price=64000.0,
            exit_price=66000.0,
            quantity=0.01,
            pnl=20.0,
            pnl_percent=3.125,
            exit_reason="TAKE_PROFIT",
            entry_timestamp="2026-07-01T10:00:00+00:00",
            exit_timestamp="2026-07-01T11:00:00+00:00",
        )
        saved = await repo.save(trade)

        assert saved.id is not None
        assert saved.symbol == "BTCUSDT"
        assert saved.pnl == 20.0
        print(f"  Trade ID  : {saved.id}")
        print(f"  Symbol    : {saved.symbol}")
        print(f"  PnL       : ${saved.pnl:.2f}")
        print(f"  Exit      : {saved.exit_reason}")

    print("PASS")


async def test_trade_history_filter():
    print("\n--- Trade history filtering ---")
    async with _SessionLocal() as session:
        repo = TradeRepository(session)

        # Record baseline counts before inserting
        btc_before, _ = await repo.get_history(symbol="BTCUSDT")
        live_before, _ = await repo.get_history(mode="LIVE")
        rsi_before, _ = await repo.get_history(strategy="rsi_filter_test")

        for sym, strat, mode in [
            ("BTCUSDT", "rsi_filter_test", "PAPER"),
            ("ETHUSDT", "ema_filter_test", "PAPER"),
            ("BTCUSDT", "macd_filter_test", "LIVE"),
        ]:
            await repo.save(Trade(
                symbol=sym, strategy=strat, direction="BUY", mode=mode,
                entry_price=1000.0, exit_price=1100.0, quantity=0.1,
                pnl=10.0, pnl_percent=10.0, exit_reason="TP",
                entry_timestamp="", exit_timestamp="",
            ))

        btc_after, _ = await repo.get_history(symbol="BTCUSDT")
        live_after, _ = await repo.get_history(mode="LIVE")
        rsi_after, _ = await repo.get_history(strategy="rsi_filter_test")

        assert btc_after - btc_before == 2, f"Expected +2 BTCUSDT, got +{btc_after - btc_before}"
        assert live_after - live_before == 1, f"Expected +1 LIVE, got +{live_after - live_before}"
        assert rsi_after - rsi_before == 1, f"Expected +1 rsi_filter_test, got +{rsi_after - rsi_before}"

        print(f"  BTCUSDT delta : +2 ✓")
        print(f"  LIVE delta    : +1 ✓")
        print(f"  RSI delta     : +1 ✓")
    print("PASS")


async def test_save_backtest_run():
    print("\n--- Save + query BacktestRun ---")
    async with _SessionLocal() as session:
        repo = BacktestRepository(session)

        run = BacktestRun(
            strategy="rsi",
            symbol="BTCUSDT",
            interval="5m",
            limit=300,
            initial_balance=10000.0,
            final_balance=10850.0,
            total_return=8.5,
            total_trades=12,
            win_rate=58.33,
            profit_factor=1.62,
            sharpe_ratio=1.21,
            max_drawdown=4.2,
        )
        saved = await repo.save(run)

        assert saved.id is not None
        assert saved.strategy == "rsi"
        assert saved.total_trades == 12
        print(f"  Run ID       : {saved.id}")
        print(f"  Strategy     : {saved.strategy}")
        print(f"  Total Return : {saved.total_return}%")
        print(f"  Sharpe       : {saved.sharpe_ratio}")

    print("PASS")


async def test_backtest_history_filter():
    print("\n--- Backtest history filtering ---")
    async with _SessionLocal() as session:
        repo = BacktestRepository(session)

        # Use unique strategy name to isolate from other tests
        for strat in ["rsi_bt_test", "ema_bt_test", "rsi_bt_test"]:
            await repo.save(BacktestRun(
                strategy=strat, symbol="BTCUSDT", interval="5m", limit=300,
                initial_balance=10000.0, final_balance=10500.0, total_return=5.0,
                total_trades=10, win_rate=60.0, profit_factor=1.5,
                sharpe_ratio=1.1, max_drawdown=3.0,
            ))

        runs = await repo.get_recent(strategy="rsi_bt_test")
        assert len(runs) == 2, f"Expected 2, got {len(runs)}"
        print(f"  RSI backtest runs: {len(runs)} ✓")

    print("PASS")


async def test_db_service_integration():
    """Test DatabaseService using the in-memory engine (patches AsyncSessionLocal)."""
    print("\n--- DatabaseService integration ---")
    import backend.app.services.db_service as db_module
    from unittest.mock import patch

    # Patch the session factory to use test engine
    with patch.object(db_module, "AsyncSessionLocal", _SessionLocal):
        from backend.app.services.db_service import DatabaseService
        svc = DatabaseService()

        trade = await svc.save_trade(
            symbol="BTCUSDT",
            strategy="rsi",
            mode="PAPER",
            entry_price=63000.0,
            exit_price=65000.0,
            quantity=0.01,
            pnl=20.0,
            exit_reason="TAKE_PROFIT",
            entry_timestamp="2026-07-01T10:00:00+00:00",
        )
        assert trade.id is not None
        assert trade.pnl_percent == round((65000 - 63000) / 63000 * 100, 4)
        print(f"  Saved trade ID : {trade.id}")
        print(f"  PnL%           : {trade.pnl_percent:.4f}%")

        total, trades = await svc.get_trade_history(symbol="BTCUSDT")
        assert total >= 1
        print(f"  History total  : {total}")

    print("PASS")


async def main():
    await _setup()

    tests = [
        test_save_and_query_trade,
        test_trade_history_filter,
        test_save_backtest_run,
        test_backtest_history_filter,
        test_db_service_integration,
    ]

    passed = 0
    failed = 0
    for t in tests:
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
