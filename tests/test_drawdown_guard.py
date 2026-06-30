import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.risk.drawdown_guard import DrawdownGuard


def test_no_drawdown():
    guard = DrawdownGuard()
    guard.update(10000)
    can_trade, action = guard.check(10000)
    assert can_trade is True
    assert action == ""
    print("No drawdown → can_trade=True PASS")


def test_halt_at_10_pct():
    guard = DrawdownGuard()
    guard.update(10000)
    can_trade, action = guard.check(9000)  # 10% drawdown
    assert can_trade is False
    assert action == "HALT"
    print("10% drawdown → HALT PASS")


def test_close_all_at_20_pct():
    guard = DrawdownGuard()
    guard.update(10000)
    can_trade, action = guard.check(8000)  # 20% drawdown
    assert can_trade is False
    assert action == "CLOSE_ALL"
    print("20% drawdown → CLOSE_ALL PASS")


def test_peak_tracking():
    guard = DrawdownGuard()
    guard.update(8000)
    guard.update(10000)
    guard.update(9000)
    assert guard.peak_equity == 10000
    dd = guard.current_drawdown(9000)
    assert abs(dd - 0.10) < 0.001
    print(f"Peak tracking → peak=10000, dd={dd*100:.1f}% PASS")


def test_recovery_after_drawdown():
    guard = DrawdownGuard()
    guard.update(10000)
    can_trade, _ = guard.check(9000)
    assert can_trade is False
    # Equity recovers above halt threshold
    guard.update(10000)
    can_trade, action = guard.check(9500)
    assert can_trade is True
    assert action == ""
    print("Recovery from drawdown → can_trade=True PASS")


def test_status_dict():
    guard = DrawdownGuard()
    guard.update(10000)
    status = guard.status(9500)
    assert "drawdown_pct" in status
    assert status["peak_equity"] == 10000
    print(f"Status: {status}")


if __name__ == "__main__":
    test_no_drawdown()
    test_halt_at_10_pct()
    test_close_all_at_20_pct()
    test_peak_tracking()
    test_recovery_after_drawdown()
    test_status_dict()
    print("\nAll DrawdownGuard tests PASSED")
