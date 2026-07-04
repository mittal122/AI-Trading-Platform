"""Restored classical chart-shape detectors (Double/Triple Top/Bottom, H&S,
Triangle, Wedge, Flag/Pennant, Channel/Rectangle) — synthetic Double Top
positive path (exercises the forward-resolution status upgrade), plus a
live-data smoke run across all 6 families asserting well-formed output and
drawable annotations.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.app.schemas.pattern import PatternDirection, PatternStatus
from backend.app.services.pattern.double_triple_patterns import DoubleTriplePatternDetector
from backend.app.services.pattern.pattern_factory import PatternFactory
from backend.app.services.market_service import MarketService

SHAPE_KEYS = [
    "staircase", "double_triple", "head_shoulders", "triangle", "wedge",
    "flag_pennant", "channel_rectangle", "cup_handle",
]


def _df(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    base_time = datetime(2026, 1, 1)  # tz-naive — matches real market data dtype
    c = np.array(closes, dtype=float)
    return pd.DataFrame({
        "timestamps": [base_time + timedelta(hours=i) for i in range(n)],
        "open": c - 0.15,
        "high": c + 0.6,
        "low": c - 0.6,
        "close": c,
        "volume": np.full(n, 100.0),
    })


print("\n========== SYNTHETIC DOUBLE TOP (forward-resolved) ==========\n")
# Rise → peak ~120 → trough ~110 (>2% retrace) → second peak ~120 → break
# below the neckline afterwards → should be a CONFIRMED (bearish) Double Top.
closes = (
    list(np.linspace(100, 120, 15))     # rally to peak 1 (idx 14)
    + list(np.linspace(119, 110, 8))    # retrace to trough (~8.3% deep)
    + list(np.linspace(111, 120, 8))    # rally to peak 2 (idx ~30)
    + list(np.linspace(119, 104, 12))   # breakdown through the neckline
    + list(np.linspace(104, 103, 7))    # drift after the move
)
df = _df(closes)
results = DoubleTriplePatternDetector().detect(df, "TESTUSDT", "1h")
tops = [p for p in results if p.pattern_type in ("double_top", "triple_top")]
assert tops, f"expected a double/triple top, got {[p.pattern_type for p in results]}"
p = tops[0]
assert p.direction == PatternDirection.BEARISH
assert p.status == PatternStatus.CONFIRMED, (
    f"price broke the neckline right after formation — forward resolution should say CONFIRMED, got {p.status}"
)
assert p.annotations.trendlines and p.annotations.trendlines[0].label == "neckline"
print(f"PASS: {p.pattern_name} — {p.direction}, status={p.status}, neckline drawn at {p.breakout_level}")

print("\n========== SYNTHETIC ASCENDING STAIRCASE ==========\n")
from backend.app.services.pattern.staircase_detector import StaircaseDetector

# Clean stair-steps: rise ~10, retrace ~4, repeat — higher highs AND higher
# lows throughout, net move far beyond the ATR floor. Segment joints are
# offset slightly so no two adjacent bars share an identical high/low (the
# fractal swing detector requires a STRICT local extreme).
stair_closes = []
level = 100.0
for _ in range(6):
    stair_closes += list(np.linspace(level, level + 10, 8))          # step up (peak = level+10)
    stair_closes += list(np.linspace(level + 9.4, level + 6.2, 6))   # shallow retrace
    level += 6  # next leg starts at level+6 — a strict local minimum at each joint
df_stairs = _df(stair_closes)
stair_results = StaircaseDetector().detect(df_stairs, "TESTUSDT", "1h")
assert stair_results, "expected an ascending staircase on clean HH/HL stair-steps"
sp = stair_results[0]
assert sp.pattern_type == "ascending_staircase"
assert sp.direction == PatternDirection.BULLISH
zig = sp.annotations.trendlines[0]
assert zig.label == "staircase_up" and len(zig.points) >= 6, "staircase must draw a multi-point zigzag"
print(f"PASS: {sp.pattern_name} — zigzag with {len(zig.points)} swing points drawn")

print("\n========== LIVE DATA — all 8 shape families ==========\n")
market = MarketService().get_market_data(symbol="BTCUSDT", interval="1h", limit=1000)
total = 0
for key in SHAPE_KEYS:
    detector = PatternFactory.get_detector(key)
    found = detector.detect(market, "BTCUSDT", "1h")
    for pat in found:
        assert 0 <= pat.confidence <= 100
        assert pat.formation_start <= pat.formation_end
        assert pat.status in (PatternStatus.CONFIRMED, PatternStatus.DEVELOPING, PatternStatus.BROKEN)
        # every chart shape must be drawable: at least one trendline or zone
        assert pat.annotations.trendlines or pat.annotations.zones, (
            f"{pat.pattern_name} has nothing to draw on the chart"
        )
    total += len(found)
    print(f"{key:<20} -> {len(found)} pattern(s)")
print(f"PASS: all 8 shape detectors run cleanly ({total} patterns), every result drawable")

print("\n========== RESULTS: all checks passed ==========")
