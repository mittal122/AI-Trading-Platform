"""A3 — SMC order blocks + fair value gaps (§5.4-5.5).

Explicit-candle synthetic tests (isolate OB origin/mitigation incl. the
wick-is-not-mitigation rule, and FVG fill) + live BTCUSDT smoke.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_ob_fvg.py
"""

import backend.app.core.config  # noqa: F401

from datetime import datetime, timedelta

import pandas as pd

from backend.app.schemas.smc import Direction, StructureEvent, StructureType
from backend.app.services.market_service import MarketService
from backend.app.services.smc.fvg import find_fvgs
from backend.app.services.smc.order_blocks import find_order_blocks
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings


def build_ohlc(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    t0 = datetime(2026, 1, 1)
    return pd.DataFrame([
        {"timestamps": t0 + timedelta(hours=i), "open": o, "high": h,
         "low": low, "close": c, "volume": 100.0, "amount": 100.0 * c}
        for i, (o, h, low, c) in enumerate(rows)
    ])


def test_order_block():
    # bar5 = last down candle (OB origin, range [107,113]); bars6-9 impulse up;
    # break at bar9. bar11 WICKS into the zone (low 106) but closes above -> not
    # mitigation. bar12 CLOSES below the low (105<107) -> mitigation.
    rows = [
        (100, 101, 99, 100.5), (100.5, 102, 100, 101.5), (101.5, 103, 101, 102.5),
        (102.5, 104, 102, 103.5), (103.5, 105, 103, 104.5),
        (112, 113, 107, 108),                      # 5: DOWN origin
        (108, 115, 108, 114), (114, 120, 113, 119),  # 6,7 up
        (119, 125, 118, 124), (124, 130, 123, 129),  # 8,9 up (break at 9)
        (129, 131, 128, 130),                      # 10
        (130, 132, 106, 129),                      # 11: wick into zone, close above
        (129, 130, 104, 105),                      # 12: close below low -> mitigate
    ]
    df = build_ohlc(rows)
    events = [StructureEvent(index=9, time=df["timestamps"].iloc[9].isoformat(),
                             price=105.0, type=StructureType.BOS_UP)]
    obs = find_order_blocks(df, events)
    assert len(obs) == 1, f"expected 1 OB, got {len(obs)}"
    ob = obs[0]
    assert ob.index == 5 and ob.direction == Direction.BULLISH
    assert ob.bottom == 107 and ob.top == 113, f"OB range {ob.bottom}-{ob.top}"
    assert ob.mitigated and ob.mitigated_index == 12, \
        f"mitigation wrong: {ob.mitigated} @ {ob.mitigated_index} (wick at 11 must be ignored)"
    print(f"PASS order block: bullish OB [{ob.bottom},{ob.top}] @5, "
          f"mitigated @12 (wick @11 correctly ignored)")


def test_fvg():
    rows = [
        (100, 100, 98, 99),      # 0 (i-1 bull)
        (99, 106, 101, 105),     # 1 (i bull)
        (105, 103, 101, 102),    # 2 (i+1 bull): low 101 > 100 -> bull FVG [100,101]
        (102, 104, 102, 103),    # 3 no fill
        (103, 103, 99, 100),     # 4 low 99 <= 100 -> fills bull FVG
        (100, 101, 97, 98),      # 5 filler
        (95, 95, 90, 91),        # 6 (i-1 bear)
        (91, 89, 84, 85),        # 7 (i bear)
        (85, 88, 84, 86),        # 8 (i+1 bear): high 88 < 90 -> bear FVG [88,90]
        (86, 92, 86, 90),        # 9 high 92 >= 90 -> fills bear FVG
    ]
    df = build_ohlc(rows)
    fvgs = find_fvgs(df)

    bull = [f for f in fvgs if f.direction == Direction.BULLISH and f.bottom == 100]
    assert bull, f"bullish FVG [100,101] not found: {[(f.direction.value,f.bottom,f.top) for f in fvgs]}"
    b = bull[0]
    assert b.top == 101 and b.filled and b.filled_index == 4, \
        f"bull FVG wrong: top={b.top} filled={b.filled}@{b.filled_index}"

    bear = [f for f in fvgs if f.direction == Direction.BEARISH and f.bottom == 88]
    assert bear, "bearish FVG [88,90] not found"
    be = bear[0]
    assert be.top == 90 and be.filled and be.filled_index == 9, \
        f"bear FVG wrong: top={be.top} filled={be.filled}@{be.filled_index}"
    print(f"PASS fvg: bull [100,101] filled@4, bear [88,90] filled@9 "
          f"({len(fvgs)} total detected)")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 300)
    events = analyze_structure(find_swings(df)).events
    obs = find_order_blocks(df, events)
    fvgs = find_fvgs(df)
    n = len(df)
    for ob in obs:
        assert ob.top >= ob.bottom and 0 <= ob.index < n
    for f in fvgs:
        assert f.top > f.bottom and 0 <= f.index < n
    unmit = sum(1 for o in obs if not o.mitigated)
    openf = sum(1 for f in fvgs if not f.filled)
    print(f"PASS live BTCUSDT/1h: {len(obs)} OBs ({unmit} unmitigated), "
          f"{len(fvgs)} FVGs ({openf} open)")


if __name__ == "__main__":
    test_order_block()
    test_fvg()
    test_live()
    print("A3 OK")
