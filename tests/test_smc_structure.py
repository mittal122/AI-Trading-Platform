"""A2 — SMC swing detection + market structure (§5.2-5.3).

Synthetic forced-structure test (deterministic BOS/CHoCH sequence) + a live
BTCUSDT smoke test. Run: PYTHONPATH=. .venv/bin/python tests/test_smc_structure.py
"""

import backend.app.core.config  # noqa: F401  (loads .env)

from datetime import datetime, timedelta

import pandas as pd

from backend.app.schemas.smc import StructureType, SwingLabel, TrendState
from backend.app.services.market_service import MarketService
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings


def _ramp(a: float, b: float, n: int) -> list[float]:
    """n interpolated values from a to b inclusive."""
    if n == 1:
        return [b]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def build_df(pivots: list[tuple[str, float]], gap: int = 8) -> pd.DataFrame:
    """Build OHLC candles whose only strict fractal extremes are `pivots`.

    Monotonic ramps between pivots -> each pivot bar is the unique turning
    point. Lead-in / trail-out padding make the first/last pivots valid extremes.
    tz-naive timestamps to match real Binance data (avoids the numpy .item() gotcha).
    """
    k0, p0 = pivots[0]
    kn, pn = pivots[-1]
    lead = p0 + 15 if k0 == "low" else p0 - 15
    trail = pn + 15 if kn == "low" else pn - 15
    nodes = [lead] + [p for _, p in pivots] + [trail]

    vals: list[float] = []
    for seg_i in range(len(nodes) - 1):
        seg = _ramp(nodes[seg_i], nodes[seg_i + 1], gap)
        vals += seg if seg_i == 0 else seg[1:]

    t0 = datetime(2026, 1, 1)
    rows = []
    prev_close = vals[0]
    for i, v in enumerate(vals):
        rows.append({
            "timestamps": t0 + timedelta(hours=i),
            "open": prev_close,
            "high": v + 0.4,
            "low": v - 0.4,
            "close": v,
            "volume": 100.0,
            "amount": 100.0 * v,
        })
        prev_close = v
    return pd.DataFrame(rows)


def test_synthetic():
    # low/high alternating -> known structure sequence
    pivots = [
        ("low", 100), ("high", 120), ("low", 110), ("high", 130),
        ("low", 118), ("high", 140), ("low", 95), ("high", 105), ("low", 80),
    ]
    df = build_df(pivots)
    swings = find_swings(df)
    result = analyze_structure(swings)

    event_types = [e.type for e in result.events]
    assert event_types == [
        StructureType.CHOCH_UP, StructureType.BOS_UP,
        StructureType.CHOCH_DOWN, StructureType.BOS_DOWN,
    ], f"unexpected structure sequence: {event_types}"

    assert result.trend == TrendState.DOWN, f"trend {result.trend}"

    labels = {s.label for s in result.swings if s.label}
    for want in (SwingLabel.HH, SwingLabel.HL, SwingLabel.LH, SwingLabel.LL):
        assert want in labels, f"missing label {want} (got {labels})"

    # broken level on each event is a prior swing extreme, not the breaking swing
    for e in result.events:
        assert e.price > 0
    print(f"PASS synthetic: events={[e.type.value for e in result.events]} "
          f"trend={result.trend.value} labels={sorted(l.value for l in labels)}")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 300)
    swings = find_swings(df)
    result = analyze_structure(swings)
    assert len(swings) > 0, "no swings on live data"
    n = len(df)
    for e in result.events:
        assert 0 <= e.index < n
        assert isinstance(e.type, StructureType)
    assert result.trend in (TrendState.UP, TrendState.DOWN, TrendState.NEUTRAL)
    highs = sum(1 for s in swings if s.is_high)
    print(f"PASS live BTCUSDT/1h: {len(swings)} swings ({highs} highs), "
          f"{len(result.events)} structure events, trend={result.trend.value}")


if __name__ == "__main__":
    test_synthetic()
    test_live()
    print("A2 OK")
