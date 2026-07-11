"""SMC auto-tester — decision core + early close (flip support)."""

import asyncio

from backend.app.services.smc.auto_tester import decide
from backend.app.services.paper.manual_paper_trader import ManualPaperTrader
from backend.app.schemas.paper import ManualOrderRequest


def test_decide():
    # Flat + clear primary → enter that side
    assert decide("long", 80, 30, None, 40, 10) == ("enter", "long")
    assert decide("short", 30, 80, None, 40, 10) == ("enter", "short")
    # Flat + neutral primary → higher-scoring side wins (the "strong side")
    assert decide("neutral", 55, 45, None, 40, 10) == ("enter", "long")
    assert decide("neutral", 45, 55, None, 40, 10) == ("enter", "short")
    # Flat but nothing clears min_score → wait
    assert decide("neutral", 30, 20, None, 40, 10) == ("wait", None)
    assert decide("long", 35, 10, None, 40, 10) == ("wait", None)
    # Holding long, no reversal → hold ("hold until target")
    assert decide("long", 70, 50, "long", 40, 10) == ("hold", "long")
    # Opposite stronger but within the margin → still hold
    assert decide("neutral", 60, 65, "long", 40, 10) == ("hold", "long")
    # Opposite beats current by >= margin AND clears min_score → flip
    assert decide("short", 40, 75, "long", 40, 10) == ("flip", "short")
    assert decide("long", 75, 40, "short", 40, 10) == ("flip", "long")
    # Opposite dominant but below min_score → hold, never enter junk
    assert decide("neutral", 10, 35, "long", 40, 10) == ("hold", "long")
    print("PASS: decide() — enter/wait/hold/flip logic")


def test_close_now_books_flip():
    async def run():
        trader = ManualPaperTrader(starting_balance=10_000)

        # Stub live price so no network is touched.
        async def fake_price(symbol, interval):
            return 105.0
        trader._latest_price = fake_price  # type: ignore[method-assign]

        async def fake_save(**kwargs):
            return None
        trader._db.save_trade = fake_save  # type: ignore[method-assign]

        order = trader.place(ManualOrderRequest(
            symbol="TESTUSDT", strategy="smc_autotest", direction="BUY",
            entry=100.0, stop_loss=95.0, take_profit=120.0,
            risk_percent=1.0, interval="5m",
        ))
        assert order.status == "OPEN"

        closed = await trader.close_now(order.id)
        assert closed.status == "CLOSED"
        assert closed.exit_reason == "FLIPPED"
        expected = (105.0 - 100.0) * order.quantity
        assert abs(closed.realized_pnl - expected) < 1e-6
        assert trader.status().open_count == 0

        # Idempotent: closing again must fail cleanly, PnL not double-booked
        balance_after = trader.balance
        try:
            await trader.close_now(order.id)
            raise AssertionError("second close_now should raise")
        except ValueError:
            pass
        assert trader.balance == balance_after
        # Direct double-_close is also a no-op
        await trader._close(closed, 200.0, "STOP_LOSS")
        assert trader.balance == balance_after

    asyncio.run(run())
    print("PASS: close_now() closes at market, books FLIPPED PnL once")


if __name__ == "__main__":
    test_decide()
    test_close_now_books_flip()
    print("\nRESULTS: all checks passed")
