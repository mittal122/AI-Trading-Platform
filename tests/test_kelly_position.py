import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.position.kelly_position import KellyPosition


def test_kelly_basic_calculation():
    kelly = KellyPosition(win_rate=0.55)
    result = kelly.calculate(
        account_equity=10000,
        entry=100.0,
        stop_loss=95.0,
        risk_percent=100,
        risk_reward=2.0,
    )
    # f* = (2*0.55 - 0.45) / 2 = 0.325 → capped at 0.25
    assert result.quantity > 0
    assert result.exposure <= 25.0 + 0.01  # capped at 25%
    print(f"Kelly fraction used: {result.risk_percent:.2f}%  Qty: {result.quantity:.4f}")


def test_kelly_negative_edge():
    # win_rate=0.3, RR=1.0 → negative kelly → no trade
    kelly = KellyPosition(win_rate=0.30)
    result = kelly.calculate(
        account_equity=10000,
        entry=100.0,
        stop_loss=99.0,
        risk_percent=100,
        risk_reward=1.0,
    )
    assert result.quantity == 0.0
    print("Negative edge → qty=0 PASS")


def test_kelly_cap_at_25_pct():
    kelly = KellyPosition(win_rate=0.80, max_kelly=0.25)
    result = kelly.calculate(
        account_equity=10000,
        entry=50.0,
        stop_loss=45.0,
        risk_percent=100,
        risk_reward=5.0,
    )
    assert result.position_value <= 10000 * 0.25 + 0.01
    print(f"Position value {result.position_value:.2f} ≤ 25% of equity PASS")


def test_kelly_zero_risk_per_unit():
    kelly = KellyPosition()
    result = kelly.calculate(
        account_equity=10000,
        entry=100.0,
        stop_loss=100.0,  # same as entry → zero risk
        risk_percent=1.0,
    )
    assert result.quantity == 0.0
    print("Zero risk per unit → qty=0 PASS")


def test_kelly_factory():
    from backend.app.services.position.position_factory import PositionFactory
    engine = PositionFactory.get_engine("kelly")
    assert isinstance(engine, KellyPosition)
    print("PositionFactory kelly PASS")


if __name__ == "__main__":
    test_kelly_basic_calculation()
    test_kelly_negative_edge()
    test_kelly_cap_at_25_pct()
    test_kelly_zero_risk_per_unit()
    test_kelly_factory()
    print("\nAll Kelly tests PASSED")
