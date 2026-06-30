import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.trade.exit_manager import ExitManager
from backend.app.services.trade.trade_state import TradeState


def make_trade(entry=100.0, sl=95.0, tp=110.0):
    return TradeState(
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        quantity=1.0,
        entry_timestamp="2024-01-01T00:00:00",
        peak_price=entry,
        atr_at_entry=5.0,
    )


def test_partial_exit_triggers_at_1_to_1():
    em = ExitManager()
    trade = make_trade(entry=100.0, sl=95.0, tp=110.0)
    # 1:1 RR is at entry + risk = 100 + 5 = 105
    should_exit, reason = em.check_exit(
        price=105.0,
        signal_direction="BUY",
        trade=trade,
        atr=5.0,
    )
    assert should_exit is True
    assert reason == "PARTIAL_EXIT"
    assert trade.partial_exit_done is True
    print("PARTIAL_EXIT triggers at 1:1 RR PASS")


def test_partial_exit_fires_only_once():
    em = ExitManager()
    trade = make_trade(entry=100.0, sl=95.0, tp=110.0)
    # First call at 1:1 → PARTIAL_EXIT
    em.check_exit(price=105.0, signal_direction="BUY", trade=trade, atr=5.0)
    # Second call — partial already done, should NOT fire again
    should_exit, reason = em.check_exit(
        price=107.0,
        signal_direction="BUY",
        trade=trade,
        atr=5.0,
    )
    assert reason != "PARTIAL_EXIT"
    print("PARTIAL_EXIT fires only once PASS")


def test_full_tp_after_partial():
    em = ExitManager()
    trade = make_trade(entry=100.0, sl=95.0, tp=110.0)
    trade.partial_exit_done = True  # already partially exited
    should_exit, reason = em.check_exit(
        price=110.0,
        signal_direction="BUY",
        trade=trade,
        atr=5.0,
    )
    assert should_exit is True
    assert reason == "TAKE_PROFIT"
    print("Full TAKE_PROFIT after partial PASS")


def test_stop_loss_before_partial():
    em = ExitManager()
    trade = make_trade(entry=100.0, sl=95.0, tp=110.0)
    should_exit, reason = em.check_exit(
        price=94.0,
        signal_direction="SELL",
        trade=trade,
        atr=5.0,
    )
    assert should_exit is True
    assert reason == "STOP_LOSS"
    print("STOP_LOSS before partial PASS")


if __name__ == "__main__":
    test_partial_exit_triggers_at_1_to_1()
    test_partial_exit_fires_only_once()
    test_full_tp_after_partial()
    test_stop_loss_before_partial()
    print("\nAll Partial Exit tests PASSED")
