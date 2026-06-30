import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.risk.daily_loss_limit import DailyLossLimit


def test_can_trade_initially():
    limit = DailyLossLimit()
    assert limit.can_trade(10000) is True
    print("Initial state → can_trade=True PASS")


def test_halt_when_limit_hit():
    limit = DailyLossLimit()
    limit.can_trade(10000)  # initialise day_start_equity=10000
    limit.record_pnl(-250)  # 2.5% loss on 10000 → exceeds 2% limit
    assert limit.can_trade(10000) is False
    print("2.5% loss → can_trade=False PASS")


def test_within_limit():
    limit = DailyLossLimit()
    limit.can_trade(10000)
    limit.record_pnl(-150)  # 1.5% loss → under 2% limit
    assert limit.can_trade(10000) is True
    print("1.5% loss → can_trade=True PASS")


def test_positive_pnl_allows_trading():
    limit = DailyLossLimit()
    limit.can_trade(10000)
    limit.record_pnl(500)
    assert limit.can_trade(10000) is True
    print("Positive PnL → can_trade=True PASS")


def test_pnl_accumulates():
    limit = DailyLossLimit()
    limit.can_trade(10000)
    limit.record_pnl(-100)
    limit.record_pnl(-80)
    limit.record_pnl(-30)  # total = -210 → 2.1% loss
    assert limit.can_trade(10000) is False
    print("Accumulated -210 → 2.1% → halted PASS")


def test_status_dict():
    limit = DailyLossLimit()
    limit.can_trade(10000)
    limit.record_pnl(-100)
    status = limit.status(10000)
    assert "daily_loss_pct" in status
    assert status["limit_pct"] == 2.0
    print(f"Status: {status}")


if __name__ == "__main__":
    test_can_trade_initially()
    test_halt_when_limit_hit()
    test_within_limit()
    test_positive_pnl_allows_trading()
    test_pnl_accumulates()
    test_status_dict()
    print("\nAll DailyLossLimit tests PASSED")
