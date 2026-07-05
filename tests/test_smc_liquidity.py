"""A4 — SMC liquidity pools + sweeps (§5.6-5.7).

Synthetic: equal-highs pool with a confirmed sweep (poke + close-back within
1-2 bars, recent), a bare-poke case that must NOT sweep, and an equal-lows pool.
Plus live BTCUSDT smoke. Run: PYTHONPATH=. .venv/bin/python tests/test_smc_liquidity.py
"""

import backend.app.core.config  # noqa: F401

from datetime import datetime, timedelta

import pandas as pd

from backend.app.schemas.smc import Direction, Swing
from backend.app.services.market_service import MarketService
from backend.app.services.smc.liquidity import find_liquidity_pools, find_sweeps
from backend.app.services.smc.swing import find_swings


def build(n: int, ov: dict[int, dict]) -> pd.DataFrame:
    """n bars, defaults high=110/low=100/close=105, per-index overrides in `ov`."""
    t0 = datetime(2026, 1, 1)
    rows = []
    for i in range(n):
        o = ov.get(i, {})
        rows.append({
            "timestamps": t0 + timedelta(hours=i),
            "open": 105.0,
            "high": o.get("high", 110.0),
            "low": o.get("low", 100.0),
            "close": o.get("close", 105.0),
            "volume": 100.0, "amount": 10000.0,
        })
    return pd.DataFrame(rows)


def _swings():
    return [
        Swing(index=10, time="t", price=120.0, is_high=True),
        Swing(index=18, time="t", price=120.05, is_high=True),   # equal highs
        Swing(index=12, time="t", price=100.0, is_high=False),
        Swing(index=16, time="t", price=100.03, is_high=False),  # equal lows
    ]


def test_pools_and_sweep():
    # poke above the equal-highs pool at bar 20, close back below at bar 21.
    df = build(30, {
        10: {"high": 120.0}, 18: {"high": 120.05},
        20: {"high": 121.0, "close": 120.5},   # poke, close still above pool
        21: {"high": 120.5, "low": 117.0, "close": 118.0},  # close back below
    })
    swings = _swings()
    pools = find_liquidity_pools(df, swings)

    eq_high = [p for p in pools if p.direction == Direction.BEARISH]
    eq_low = [p for p in pools if p.direction == Direction.BULLISH]
    assert len(eq_high) == 1, f"expected 1 equal-highs pool, got {len(eq_high)}"
    assert len(eq_low) == 1, f"expected 1 equal-lows pool, got {len(eq_low)}"
    assert abs(eq_high[0].price - 120.025) < 1e-6, eq_high[0].price
    assert abs(eq_low[0].price - 100.015) < 1e-6, eq_low[0].price

    sweeps = find_sweeps(df, pools)
    assert len(sweeps) == 1, f"expected 1 sweep, got {len(sweeps)}"
    s = sweeps[0]
    assert s.direction == Direction.BEARISH
    assert s.sweep_index == 20 and s.reversal_index == 21, \
        f"sweep@{s.sweep_index} reversal@{s.reversal_index}"
    assert s.recent, "reversal within last 10 bars should be recent"
    print(f"PASS pools+sweep: eq-high@120.025 eq-low@100.015; "
          f"sweep@20 reversal@21 recent={s.recent}")


def test_bare_poke_not_a_sweep():
    # price pokes above the pool and CONSOLIDATES above it -> never closes back
    ov = {10: {"high": 120.0}, 18: {"high": 120.05}}
    for i in range(19, 30):  # all post-formation bars stay above the pool
        ov[i] = {"high": 121.0, "low": 120.2, "close": 120.6}
    df = build(30, ov)
    pools = find_liquidity_pools(df, _swings())
    sweeps = find_sweeps(df, pools)
    assert all(s.direction != Direction.BEARISH for s in sweeps), \
        "bare poke with no close-back must not confirm an equal-highs sweep"
    print("PASS bare-poke: no equal-highs sweep confirmed (close never returned)")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 300)
    swings = find_swings(df)
    pools = find_liquidity_pools(df, swings)
    sweeps = find_sweeps(df, pools)
    for p in pools:
        assert p.price > 0 and len(p.swing_indices) == 2
    for s in sweeps:
        assert s.reversal_index >= s.sweep_index
    recent = sum(1 for s in sweeps if s.recent)
    print(f"PASS live BTCUSDT/1h: {len(pools)} pools, {len(sweeps)} sweeps "
          f"({recent} recent)")


if __name__ == "__main__":
    test_pools_and_sweep()
    test_bare_poke_not_a_sweep()
    test_live()
    print("A4 OK")
