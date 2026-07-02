"""
Phase 7 — Live Trading tests.

Tests run in dry_run=True mode — no real orders placed.
Simulates candle-close events using historical Binance data.

Run: PYTHONPATH=. .venv/bin/python tests/test_live_trading.py
"""

import asyncio
import sys

from backend.app.schemas.execution import OrderSide
from backend.app.schemas.live_trading import LiveStartRequest
from backend.app.services.execution.binance_execution import BinanceExecution
from backend.app.services.market_service import MarketService
from backend.app.services.trading.live_trading_engine import LiveTradingEngine, LiveTradingFactory


def test_engine_init():
    print("\n--- Engine init ---")
    engine = LiveTradingEngine()
    assert not engine.is_running
    assert not engine.emergency_stopped
    assert engine.config is None
    print("PASS")


def test_start_components_dry_run():
    print("\n--- Start + component init (dry_run) ---")
    engine = LiveTradingEngine()
    req = LiveStartRequest(
        symbol="BTCUSDT",
        interval="5m",
        strategy="rsi",
        initial_balance=5000.0,
        dry_run=True,
    )
    engine._init_components(req)
    engine.config = req
    engine.is_running = True

    assert engine._portfolio is not None
    assert engine._execution is not None
    assert engine._execution.dry_run is True
    assert engine._execution.symbol == "BTCUSDT"

    status = engine.status()
    assert status.dry_run is True
    assert status.initial_balance == 5000.0
    assert status.equity == 5000.0
    assert not status.emergency_stopped
    print(f"  Equity  : ${status.equity:,.2f}")
    print(f"  Dry run : {status.dry_run}")
    print("PASS")


def test_binance_execution_dry_buy():
    print("\n--- BinanceExecution dry BUY ---")
    exec_engine = BinanceExecution(symbol="BTCUSDT", dry_run=True)
    result = exec_engine.execute(side=OrderSide.BUY, price=65000.0, quantity=0.001)

    assert result.side == OrderSide.BUY
    assert result.executed_price > 65000.0  # slippage applied
    assert result.quantity == 0.001
    assert result.fee > 0

    orders = exec_engine.get_orders()
    assert len(orders) == 1
    assert orders[0].is_dry_run is True
    assert orders[0].status == "FILLED_DRY"
    print(f"  Executed price : {result.executed_price:.4f}")
    print(f"  Fee            : {result.fee:.6f}")
    print(f"  Order ID       : {orders[0].order_id}")
    print("PASS")


def test_binance_execution_dry_sell():
    print("\n--- BinanceExecution dry SELL ---")
    exec_engine = BinanceExecution(symbol="BTCUSDT", dry_run=True)
    result = exec_engine.execute(side=OrderSide.SELL, price=65000.0, quantity=0.001)

    assert result.side == OrderSide.SELL
    assert result.executed_price < 65000.0  # slippage applied
    print(f"  Executed price : {result.executed_price:.4f}")
    print("PASS")


def test_affordable_quantity():
    print("\n--- calculate_affordable_quantity ---")
    exec_engine = BinanceExecution(symbol="BTCUSDT", dry_run=True)
    qty = exec_engine.calculate_affordable_quantity(
        cash=1000.0,
        price=65000.0,
        requested_quantity=0.1,
    )
    assert qty > 0
    assert qty < 0.1  # cash constraint
    print(f"  Affordable qty : {qty:.6f}")
    print("PASS")


def test_factory_singleton():
    print("\n--- LiveTradingFactory singleton ---")
    e1 = LiveTradingFactory.get_engine()
    e2 = LiveTradingFactory.get_engine()
    assert e1 is e2
    print("PASS")


def test_status_idle():
    print("\n--- Status when idle ---")
    engine = LiveTradingEngine()
    status = engine.status()
    assert not status.is_running
    assert not status.emergency_stopped
    assert status.order_count == 0
    print("PASS")


async def test_live_candle_simulation():
    """Simulate one closed candle in dry_run mode using real Binance data."""
    print("\n--- Candle simulation dry_run (real Binance data) ---")

    engine = LiveTradingEngine()
    req = LiveStartRequest(
        symbol="BTCUSDT",
        interval="5m",
        strategy="rsi",
        initial_balance=10000.0,
        dry_run=True,
    )
    engine._init_components(req)
    engine.config = req
    engine.is_running = True

    market = MarketService().get_market_data(symbol="BTCUSDT", interval="5m", limit=200)
    last_row = market.iloc[-1]

    kline = {
        "c": str(last_row["close"]),
        "o": str(last_row["open"]),
        "h": str(last_row["high"]),
        "l": str(last_row["low"]),
        "v": str(last_row["volume"]),
        "x": True,
    }

    await engine._on_candle_close(kline)

    status = engine.status()
    print(f"  Candles processed : {status.candles_processed}")
    print(f"  Last signal       : {status.last_signal}")
    print(f"  Last price        : {status.last_price}")
    print(f"  Cash              : ${status.cash:,.2f}")
    print(f"  Equity            : ${status.equity:,.2f}")
    print(f"  Order count       : {status.order_count}")
    print(f"  Open position     : {status.open_position}")

    assert status.candles_processed == 1
    assert status.last_signal in ("BUY", "SELL", "FLAT")
    assert status.equity > 0
    assert status.dry_run is True
    print("PASS")


async def test_emergency_stop():
    print("\n--- Emergency stop ---")
    engine = LiveTradingEngine()
    req = LiveStartRequest(
        symbol="BTCUSDT",
        interval="5m",
        strategy="rsi",
        initial_balance=10000.0,
        dry_run=True,
    )
    engine._init_components(req)
    engine.config = req
    engine.is_running = True

    result = await engine.stop(emergency=True)
    assert result["orders_cancelled"] == 0  # dry_run cancels 0 real orders
    assert engine.emergency_stopped is True
    assert not engine.is_running
    print(f"  Orders cancelled : {result['orders_cancelled']}")
    print(f"  Emergency stopped: {engine.emergency_stopped}")
    print("PASS")


if __name__ == "__main__":
    tests_sync = [
        test_engine_init,
        test_start_components_dry_run,
        test_binance_execution_dry_buy,
        test_binance_execution_dry_sell,
        test_affordable_quantity,
        test_factory_singleton,
        test_status_idle,
    ]

    tests_async = [
        test_live_candle_simulation,
        test_emergency_stop,
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

    for t in tests_async:
        try:
            asyncio.run(t())
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1

    print(f"\n========== RESULTS: {passed} passed, {failed} failed ==========")
    sys.exit(0 if failed == 0 else 1)
