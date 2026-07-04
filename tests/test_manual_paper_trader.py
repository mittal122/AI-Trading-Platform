"""ManualPaperTrader — level validation, PnL math, and the equity
accounting fix (equity = balance + unrealized PnL, NOT balance + position
notional — the old formula showed +$500 equity the instant a $500 position
opened). Uses an isolated trader instance with DB persistence stubbed out,
so nothing touches trading.db.
"""

import asyncio

from backend.app.schemas.paper import ManualOrderRequest
from backend.app.services.paper.manual_paper_trader import ManualPaperTrader


async def main():
    trader = ManualPaperTrader(starting_balance=10_000.0)

    async def _noop_save(**kwargs):
        return None
    trader._db.save_trade = _noop_save  # keep the test off the real DB

    print("\n========== LEVEL VALIDATION ==========\n")
    for direction, entry, sl, tp in [
        ("BUY", 100.0, 105.0, 110.0),   # SL above entry
        ("BUY", 100.0, 95.0, 99.0),     # TP below entry
        ("SELL", 100.0, 95.0, 90.0),    # SL below entry
        ("SELL", 100.0, 105.0, 102.0),  # TP above entry
    ]:
        try:
            trader.place(ManualOrderRequest(
                symbol="TESTUSDT", direction=direction, entry=entry,
                stop_loss=sl, take_profit=tp,
            ))
            raise AssertionError(f"{direction} entry={entry} sl={sl} tp={tp} should have been rejected")
        except ValueError:
            pass
    print("PASS: all 4 invalid level orderings rejected")

    print("\n========== EQUITY ACCOUNTING ==========\n")
    order = trader.place(ManualOrderRequest(
        symbol="TESTUSDT", direction="BUY", entry=100.0,
        stop_loss=95.0, take_profit=110.0, risk_percent=1.0,
    ))
    st = trader.status()
    assert st.balance == 10_000.0
    assert abs(st.equity - 10_000.0) < 1e-6, (
        f"equity must equal balance while unrealized PnL is 0, got {st.equity} "
        "(the old bug added the position's full notional value)"
    )
    print(f"PASS: order #{order.id} open, equity == balance == $10,000 (no phantom notional)")

    # Simulate the monitor updating price +5 — equity should rise by exactly the uPnL.
    order.current_price = 105.0
    order.unrealized_pnl = round((105.0 - 100.0) * order.quantity, 4)
    st2 = trader.status()
    assert abs(st2.equity - (10_000.0 + order.unrealized_pnl)) < 1e-3
    print(f"PASS: price +5 → equity = balance + uPnL (${st2.equity})")

    print("\n========== CLOSE BOOKS PNL ==========\n")
    await trader._close(order, 110.0, "TAKE_PROFIT")
    expected_pnl = (110.0 - 100.0) * order.quantity
    st3 = trader.status()
    assert st3.open_count == 0
    assert abs(st3.balance - (10_000.0 + expected_pnl)) < 1e-3
    assert abs(st3.realized_pnl - expected_pnl) < 1e-3
    assert st3.closed_orders[-1].exit_reason == "TAKE_PROFIT"
    print(f"PASS: TP close booked pnl={expected_pnl:.4f}, balance={st3.balance}")

    print("\n========== SELL-SIDE PNL ==========\n")
    sell = trader.place(ManualOrderRequest(
        symbol="TESTUSDT", direction="SELL", entry=100.0,
        stop_loss=105.0, take_profit=90.0, risk_percent=1.0,
    ))
    assert trader._pnl(sell, 95.0) > 0, "SELL profits when price falls"
    assert trader._pnl(sell, 105.0) < 0, "SELL loses when price rises"
    assert trader._hit(sell, 105.0) == "STOP_LOSS"
    assert trader._hit(sell, 90.0) == "TAKE_PROFIT"
    assert trader._hit(sell, 99.0) is None
    print("PASS: SELL-side pnl signs and SL/TP hit detection correct")

    for task in list(trader._tasks):
        task.cancel()

    print("\n========== RESULTS: all checks passed ==========")


asyncio.run(main())
