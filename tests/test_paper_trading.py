"""
Phase 6 — Paper Trading tests.

Tests the engine logic without a live WebSocket connection.
Simulates candle-close events using historical Binance data.

Run: PYTHONPATH=. .venv/bin/python tests/test_paper_trading.py
"""

import asyncio
import sys

from backend.app.schemas.paper import PaperStartRequest
from backend.app.services.market_service import MarketService
from backend.app.services.paper.paper_trading_engine import PaperFactory, PaperTradingEngine


def test_engine_init():
    print("\n--- Engine init ---")
    engine = PaperTradingEngine()
    assert not engine.is_running
    assert engine.config is None
    assert engine._portfolio is None
    print("PASS")


def test_start_stop():
    print("\n--- Start / Stop ---")
    engine = PaperTradingEngine()

    # Start should fail without a running event loop (task needs loop)
    # so we test just the component init
    req = PaperStartRequest(
        symbol="BTCUSDT",
        interval="5m",
        strategy="rsi",
        initial_balance=5000.0,
    )
    engine._init_components(req)
    engine.config = req
    engine.is_running = True
    engine.started_at = "2026-07-01T00:00:00+00:00"

    status = engine.status()
    assert status.is_running
    assert status.initial_balance == 5000.0
    assert status.equity == 5000.0
    assert status.cash == 5000.0
    assert status.open_position is None
    assert status.trade_count == 0
    print(f"  Equity : ${status.equity:,.2f}")
    print(f"  Cash   : ${status.cash:,.2f}")
    print("PASS")


def test_status_no_running():
    print("\n--- Status when idle ---")
    engine = PaperTradingEngine()
    status = engine.status()
    assert not status.is_running
    assert status.trade_count == 0
    print("PASS")


async def test_live_candle_simulation():
    """Fetch real Binance candles and simulate one candle-close event."""
    print("\n--- Live candle simulation (real Binance data) ---")

    engine = PaperTradingEngine()
    req = PaperStartRequest(
        symbol="BTCUSDT",
        interval="5m",
        strategy="rsi",
        initial_balance=10000.0,
    )
    engine._init_components(req)
    engine.config = req
    engine.is_running = True
    engine.started_at = "2026-07-01T00:00:00+00:00"

    # Fetch live market data
    market = MarketService().get_market_data(symbol="BTCUSDT", interval="5m", limit=200)
    last_row = market.iloc[-1]

    # Build a fake kline dict (closed candle)
    kline = {
        "c": str(last_row["close"]),
        "o": str(last_row["open"]),
        "h": str(last_row["high"]),
        "l": str(last_row["low"]),
        "v": str(last_row["volume"]),
        "x": True,
    }

    # Run one candle-close cycle
    await engine._on_candle_close(kline)

    status = engine.status()
    print(f"  Candles processed : {status.candles_processed}")
    print(f"  Last signal       : {status.last_signal}")
    print(f"  Last price        : {status.last_price}")
    print(f"  Cash              : ${status.cash:,.2f}")
    print(f"  Equity            : ${status.equity:,.2f}")
    print(f"  Open position     : {status.open_position}")
    print(f"  Trade count       : {status.trade_count}")

    assert status.candles_processed == 1
    assert status.last_signal in ("BUY", "SELL", "FLAT")
    assert status.equity > 0
    print("PASS")


def test_factory_singleton():
    print("\n--- Factory singleton ---")
    e1 = PaperFactory.get_engine()
    e2 = PaperFactory.get_engine()
    assert e1 is e2
    print("PASS")


if __name__ == "__main__":
    tests_sync = [
        test_engine_init,
        test_start_stop,
        test_status_no_running,
        test_factory_singleton,
    ]

    passed = 0
    failed = 0

    for t in tests_sync:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1

    try:
        asyncio.run(test_live_candle_simulation())
        passed += 1
    except Exception as e:
        print(f"FAIL: test_live_candle_simulation — {e}")
        failed += 1

    print(f"\n========== RESULTS: {passed} passed, {failed} failed ==========")
    sys.exit(0 if failed == 0 else 1)
