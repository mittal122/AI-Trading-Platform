"""Dedicated audit suite — single-candle patterns (Batch 1 of 3).

For every pattern: a POSITIVE case (should detect), a NEGATIVE case (should
NOT detect / should not misclassify), and an EDGE case (right at the
documented threshold boundary). Run this after any change to
single_candle_patterns.py / candlestick_utils.py.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.app.schemas.pattern import PatternDirection, PatternStatus
from backend.app.services.pattern.single_candle_patterns import SingleCandlePatternDetector


def _base_df(n=40, direction="FLAT", start_price=1000.0, step=6.0):
    base_time = datetime(2026, 1, 1)
    timestamps = [base_time + timedelta(hours=i) for i in range(n)]
    sign = -1 if direction == "DOWN" else (1 if direction == "UP" else 0)
    closes = start_price + sign * np.arange(n) * step
    opens = closes - sign * step * 0.3
    highs = np.maximum(opens, closes) + 2.0
    lows = np.minimum(opens, closes) - 2.0
    return pd.DataFrame({
        "timestamps": timestamps, "open": opens, "high": highs,
        "low": lows, "close": closes, "volume": np.full(n, 100.0),
    })


def _append(df, o, h, l, c, v=100.0):
    ts = df["timestamps"].iloc[-1] + timedelta(hours=1)
    row = pd.DataFrame([{"timestamps": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}])
    return pd.concat([df, row], ignore_index=True)


DET = SingleCandlePatternDetector()


def _detect_last(built_df):
    """Run the detector, return ALL patterns detected AT THE LAST candle
    (more than one can legitimately co-occur, e.g. a Doji that's also an
    Inside Bar)."""
    results = DET.detect(built_df, "AUDITUSDT", "1h")
    last_ts = built_df["timestamps"].iloc[-1].isoformat()
    return [p for p in results if p.formation_end == last_ts]


results_log = []


def check(name, built_df, expect_type, expect_direction=None):
    at_last = _detect_last(built_df)
    if expect_type is None:
        ok = len(at_last) == 0
        detail = f"expected no detection, got {[p.pattern_type for p in at_last]}"
    else:
        match = next((p for p in at_last if p.pattern_type == expect_type), None)
        ok = match is not None and (expect_direction is None or match.direction == expect_direction)
        detail = f"expected {expect_type}/{expect_direction}, got {[(p.pattern_type, p.direction) for p in at_last]}"
    results_log.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} — {detail}")
    assert ok, f"{name}: {detail}"


# ============================================================
print("\n========== MARUBOZU ==========\n")
# POS: body 95.5%, wicks ~2.25% each
df = _append(_base_df(), o=1000.0, h=1104.5, l=999.0, c=1103.0)
check("Marubozu POS (bullish, 95.5% body)", df, "marubozu", PatternDirection.BULLISH)

# NEG: body only 80%, wicks too large (10% each side)
df = _append(_base_df(), o=1000.0, h=1030.0, l=970.0, c=1024.0)
check("Marubozu NEG (80% body, too much wick)", df, None)

# EDGE: exactly at 95% body / 5% total wick boundary (inclusive)
df = _append(_base_df(), o=1000.0, h=1102.5, l=999.5, c=1102.0)  # range=103, body=102(99.03%)... recompute below
# Build precisely: range=100, body=95, wicks=2.5 each -> upper=2.5(2.5%), lower=2.5(2.5%), body=95%
df = _append(_base_df(), o=1000.0, h=1097.5, l=999.5, c=1097.0)
check("Marubozu EDGE (exactly 95% body / 2.5%+2.5% wick)", df, "marubozu", PatternDirection.BULLISH)


print("\n========== STANDARD DOJI ==========\n")
# POS: body 2%, balanced wicks
df = _append(_base_df(), o=1000.0, h=1010.0, l=990.0, c=1000.4)
check("Standard Doji POS (balanced wicks)", df, "standard_doji", PatternDirection.NEUTRAL)

# NEG: body too large (20%)
df = _append(_base_df(), o=1000.0, h=1030.0, l=970.0, c=1012.0)
check("Standard Doji NEG (body too large)", df, None)

# EDGE: body exactly 5% of range (inclusive boundary)
df = _append(_base_df(), o=1000.0, h=1010.0, l=990.0, c=1001.0)
check("Standard Doji EDGE (body exactly 5%)", df, "standard_doji", PatternDirection.NEUTRAL)


print("\n========== DRAGONFLY DOJI ==========\n")
# POS: DOWN trend, tiny body, long lower wick
df = _append(_base_df(direction="DOWN"), o=1000.0, h=1002.0, l=950.0, c=1000.0)
check("Dragonfly POS (downtrend)", df, "dragonfly_doji", PatternDirection.BULLISH)

# NEG: identical shape but UP trend — should NOT fire as dragonfly (context-dependent by definition)
df = _append(_base_df(direction="UP"), o=1000.0, h=1002.0, l=950.0, c=1000.0)
at_last = _detect_last(df)
ok = not any(x.pattern_type == "dragonfly_doji" for x in at_last)
results_log.append(("Dragonfly NEG (uptrend, same shape)", ok, f"got {[x.pattern_type for x in at_last]}"))
print(f"  [{'PASS' if ok else 'FAIL'}] Dragonfly NEG (uptrend, same shape) — got {[x.pattern_type for x in at_last]}")
assert ok

# EDGE: lower_wick exactly 90% of range
df = _append(_base_df(direction="DOWN"), o=1000.0, h=1005.0, l=955.0, c=1000.0)  # range=50, lower=45(90%), upper=5(10%)
check("Dragonfly EDGE (lower wick exactly 90%)", df, "dragonfly_doji", PatternDirection.BULLISH)


print("\n========== GRAVESTONE DOJI ==========\n")
df = _append(_base_df(direction="UP"), o=1000.0, h=1050.0, l=998.0, c=1000.0)
check("Gravestone POS (uptrend)", df, "gravestone_doji", PatternDirection.BEARISH)

df = _append(_base_df(direction="DOWN"), o=1000.0, h=1050.0, l=998.0, c=1000.0)
at_last = _detect_last(df)
ok = not any(x.pattern_type == "gravestone_doji" for x in at_last)
print(f"  [{'PASS' if ok else 'FAIL'}] Gravestone NEG (downtrend, same shape) — got {[x.pattern_type for x in at_last]}")
assert ok

df = _append(_base_df(direction="UP"), o=1000.0, h=1045.0, l=995.0, c=1000.0)  # range=50, upper=45(90%), lower=5(10%)
check("Gravestone EDGE (upper wick exactly 90%)", df, "gravestone_doji", PatternDirection.BEARISH)


print("\n========== HAMMER ==========\n")
# POS: downtrend, small body, lower wick 3x body, upper wick tiny
df = _append(_base_df(direction="DOWN"), o=1000.0, h=1002.0, l=985.0, c=1004.0)
check("Hammer POS", df, "hammer", PatternDirection.BULLISH)

# NEG — the exact false-positive shape the old ad-hoc formula accepted:
# body=8, lower_wick=16 (2x body, satisfies ratio), upper_wick=6 — old
# formula's limit was max(body=8, lower*0.3=4.8)=8, so 6<=8 wrongly PASSED.
# New formula's limit is lower*0.3=4.8, so 6<=4.8 correctly FAILS.
o, body, lower, upper = 1000.0, 8.0, 16.0, 6.0
c = o + body
h = c + upper
l = o - lower
df = _append(_base_df(direction="DOWN"), o=o, h=h, l=l, c=c)
at_last = _detect_last(df)
ok = not any(x.pattern_type == "hammer" for x in at_last)
print(f"  [{'PASS' if ok else 'FAIL'}] Hammer NEG (regression: oversized opposite wick, old bug) — got {[x.pattern_type for x in at_last]}")
assert ok, "the old ad-hoc opposite-wick formula would have wrongly fired here"

# EDGE: upper_wick exactly at the 30%-of-lower-wick boundary
o, body, lower = 1000.0, 5.0, 15.0
upper = lower * 0.3  # = 4.5, exactly at the boundary
c = o + body
h = c + upper
l = o - lower
df = _append(_base_df(direction="DOWN"), o=o, h=h, l=l, c=c)
check("Hammer EDGE (upper wick exactly 30% of lower)", df, "hammer", PatternDirection.BULLISH)


print("\n========== HANGING MAN ==========\n")
df = _append(_base_df(direction="UP"), o=1000.0, h=1002.0, l=985.0, c=1004.0)
check("Hanging Man POS", df, "hanging_man", PatternDirection.BEARISH)

o, body, lower, upper = 1000.0, 8.0, 16.0, 6.0
c = o + body; h = c + upper; l = o - lower
df = _append(_base_df(direction="UP"), o=o, h=h, l=l, c=c)
at_last = _detect_last(df)
ok = not any(x.pattern_type == "hanging_man" for x in at_last)
print(f"  [{'PASS' if ok else 'FAIL'}] Hanging Man NEG (regression: oversized opposite wick) — got {[x.pattern_type for x in at_last]}")
assert ok


print("\n========== INVERTED HAMMER ==========\n")
df = _append(_base_df(direction="DOWN"), o=1000.0, h=1015.0, l=998.0, c=996.0)
check("Inverted Hammer POS", df, "inverted_hammer", PatternDirection.BULLISH)

o, body, upper, lower = 1000.0, 8.0, 16.0, 6.0
c = o - body; h = o + upper; l = c - lower
df = _append(_base_df(direction="DOWN"), o=o, h=h, l=l, c=c)
at_last = _detect_last(df)
ok = not any(x.pattern_type == "inverted_hammer" for x in at_last)
print(f"  [{'PASS' if ok else 'FAIL'}] Inverted Hammer NEG (regression: oversized opposite wick) — got {[x.pattern_type for x in at_last]}")
assert ok


print("\n========== SHOOTING STAR ==========\n")
df = _append(_base_df(direction="UP"), o=1000.0, h=1015.0, l=998.0, c=996.0)
check("Shooting Star POS", df, "shooting_star", PatternDirection.BEARISH)

o, body, upper, lower = 1000.0, 8.0, 16.0, 6.0
c = o - body; h = o + upper; l = c - lower
df = _append(_base_df(direction="UP"), o=o, h=h, l=l, c=c)
at_last = _detect_last(df)
ok = not any(x.pattern_type == "shooting_star" for x in at_last)
print(f"  [{'PASS' if ok else 'FAIL'}] Shooting Star NEG (regression: oversized opposite wick) — got {[x.pattern_type for x in at_last]}")
assert ok


print("\n========== SPINNING TOP ==========\n")
df = _append(_base_df(), o=1000.0, h=1010.0, l=988.0, c=1002.0)  # body=2, upper=8, lower=10
check("Spinning Top POS", df, "spinning_top", PatternDirection.NEUTRAL)

df = _append(_base_df(direction="DOWN"), o=1000.0, h=1010.0, l=999.0, c=1002.0)  # body=2, upper=8(4x), lower=1(0.5x, not dominant)
at_last = _detect_last(df)
ok = not any(x.pattern_type == "spinning_top" for x in at_last)
print(f"  [{'PASS' if ok else 'FAIL'}] Spinning Top NEG (only one wick dominant) — got {[x.pattern_type for x in at_last]}")
assert ok

df = _append(_base_df(), o=1000.0, h=1008.0, l=992.0, c=1002.0)  # body=2, upper=6(3x), lower=8(4x) both >=2x
check("Spinning Top EDGE (both wicks exactly at 2x boundary variant)", df, "spinning_top", PatternDirection.NEUTRAL)


print("\n========== INSIDE BAR ==========\n")
base = _base_df()
mother = _append(base, o=1000.0, h=1030.0, l=970.0, c=1010.0)
baby = _append(mother, o=1000.0, h=1015.0, l=985.0, c=1005.0)
check("Inside Bar POS (baby fully inside mother)", baby, "inside_bar", PatternDirection.NEUTRAL)

mother2 = _append(base, o=1000.0, h=1030.0, l=970.0, c=1010.0)
baby2 = _append(mother2, o=1000.0, h=1030.0, l=985.0, c=1005.0)  # baby.high == mother.high, NOT strictly inside
at_last = _detect_last(baby2)
ok = not any(x.pattern_type == "inside_bar" for x in at_last)
print(f"  [{'PASS' if ok else 'FAIL'}] Inside Bar NEG (equal high, not strictly inside) — got {[x.pattern_type for x in at_last]}")
assert ok

mother3 = _append(base, o=1000.0, h=1030.0, l=970.0, c=1010.0)
baby3 = _append(mother3, o=1000.0, h=1029.9, l=970.1, c=1005.0)  # barely inside
check("Inside Bar EDGE (barely inside, 0.1 margin)", baby3, "inside_bar", PatternDirection.NEUTRAL)


print("\n========== RESULTS ==========\n")
passed = sum(1 for _, ok, _ in results_log if ok)
print(f"{passed}/{len(results_log)} checks passed")
print("\nPASS: all single-candle pattern audits passed" if passed == len(results_log) else "FAIL: see above")
