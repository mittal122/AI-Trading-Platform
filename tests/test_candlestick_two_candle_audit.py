"""Dedicated audit suite — two-candle patterns (Batch 2 of 3).

Same structure as the single-candle audit: POSITIVE / NEGATIVE / EDGE per
pattern. Run after any change to two_candle_patterns.py.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.app.schemas.pattern import PatternDirection
from backend.app.services.pattern.two_candle_patterns import TwoCandlePatternDetector


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


DET = TwoCandlePatternDetector()
results_log = []


def _detect_last(built_df):
    results = DET.detect(built_df, "AUDITUSDT", "1h")
    last_ts = built_df["timestamps"].iloc[-1].isoformat()
    return [p for p in results if p.formation_end == last_ts]


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
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} — {detail}")
    assert ok, f"{name}: {detail}"


# ============================================================
print("\n========== BULLISH KICKER ==========\n")
base = _base_df()
c1 = _append(base, o=1000.0, h=1005.0, l=985.0, c=990.0, v=100.0)      # bearish
c2 = _append(c1, o=1010.0, h=1030.0, l=1008.0, c=1025.0, v=250.0)      # bullish, gaps above C1.high(1005)
check("Bullish Kicker POS", c2, "bullish_kicker", PatternDirection.BULLISH)

c1n = _append(base, o=1000.0, h=1005.0, l=985.0, c=990.0, v=100.0)
c2n = _append(c1n, o=1000.0, h=1030.0, l=998.0, c=1025.0, v=250.0)     # NO gap (open below C1.high)
check("Bullish Kicker NEG (no gap)", c2n, None)

c1e = _append(base, o=1000.0, h=1005.0, l=985.0, c=990.0, v=100.0)
gap_edge = 1005.0 * 1.0005  # exactly at 0.05% min-gap boundary
c2e = _append(c1e, o=gap_edge + 0.01, h=gap_edge + 20, l=gap_edge, c=gap_edge + 15, v=250.0)
check("Bullish Kicker EDGE (gap just past min threshold)", c2e, "bullish_kicker", PatternDirection.BULLISH)


print("\n========== BEARISH KICKER ==========\n")
c1 = _append(base, o=1000.0, h=1015.0, l=995.0, c=1010.0, v=100.0)     # bullish
c2 = _append(c1, o=985.0, h=987.0, l=960.0, c=965.0, v=250.0)          # bearish, gaps below C1.low(995)
check("Bearish Kicker POS", c2, "bearish_kicker", PatternDirection.BEARISH)

c1n = _append(base, o=1000.0, h=1015.0, l=995.0, c=1010.0, v=100.0)
c2n = _append(c1n, o=1000.0, h=1005.0, l=960.0, c=965.0, v=250.0)      # no gap
check("Bearish Kicker NEG (no gap)", c2n, None)


print("\n========== BULLISH ENGULFING ==========\n")
base_down = _base_df(direction="DOWN")
c1 = _append(base_down, o=1000.0, h=1002.0, l=988.0, c=990.0, v=100.0)   # bearish
c2 = _append(c1, o=985.0, h=1010.0, l=983.0, c=1005.0, v=250.0)          # bullish, fully engulfs
check("Bullish Engulfing POS", c2, "bullish_engulfing", PatternDirection.BULLISH)

# NEG — regression for the color-check bug: C1 is BULLISH (wrong color) and
# C2 is a small bullish candle sitting inside it. The old code only checked
# body-overlap inequalities (c2.close>=c1.open and c2.open<=c1.close), which
# this shape also satisfies — it would have wrongly fired as "engulfing"
# despite neither candle being the required color.
c1_wrong = _append(base_down, o=1000.0, h=1008.0, l=998.0, c=1005.0, v=100.0)  # BULLISH, not bearish
c2_wrong = _append(c1_wrong, o=1002.0, h=1006.0, l=1001.0, c=1004.0, v=250.0)  # small bullish, inside C1's body
check("Bullish Engulfing NEG (regression: wrong colors, overlap math alone)", c2_wrong, None)

# EDGE: C2 body edges exactly touch C1's body edges
c1e = _append(base_down, o=1000.0, h=1002.0, l=988.0, c=990.0, v=100.0)
c2e = _append(c1e, o=990.0, h=1005.0, l=988.0, c=1000.0, v=250.0)  # c2.open==c1.close, c2.close==c1.open
check("Bullish Engulfing EDGE (body edges exactly touching)", c2e, "bullish_engulfing", PatternDirection.BULLISH)


print("\n========== BEARISH ENGULFING ==========\n")
base_up = _base_df(direction="UP")
c1 = _append(base_up, o=990.0, h=1002.0, l=988.0, c=1000.0, v=100.0)     # bullish
c2 = _append(c1, o=1005.0, h=1007.0, l=980.0, c=985.0, v=250.0)          # bearish, fully engulfs
check("Bearish Engulfing POS", c2, "bearish_engulfing", PatternDirection.BEARISH)

c1_wrong = _append(base_up, o=1005.0, h=1008.0, l=998.0, c=1000.0, v=100.0)  # BEARISH, not bullish
c2_wrong = _append(c1_wrong, o=1002.0, h=1004.0, l=1000.0, c=1001.0, v=250.0)  # small bearish inside
check("Bearish Engulfing NEG (regression: wrong colors)", c2_wrong, None)


print("\n========== BULLISH HARAMI ==========\n")
c1 = _append(base_down, o=1010.0, h=1012.0, l=988.0, c=990.0, v=100.0)   # bearish, big body(20)
c2 = _append(c1, o=995.0, h=1005.0, l=993.0, c=1000.0, v=100.0)          # small body(5) inside
check("Bullish Harami POS", c2, "bullish_harami", PatternDirection.BULLISH)

c1n = _append(base_down, o=1010.0, h=1012.0, l=988.0, c=990.0, v=100.0)
c2n = _append(c1n, o=1005.0, h=1008.0, l=970.0, c=975.0, v=100.0)        # bearish, body(30) bigger than C1's(20), no gap
check("Bullish Harami NEG (C2 body bigger than C1's, wrong color)", c2n, None)


print("\n========== BEARISH HARAMI ==========\n")
c1 = _append(base_up, o=990.0, h=1012.0, l=988.0, c=1010.0, v=100.0)     # bullish, big body(20)
c2 = _append(c1, o=1005.0, h=1007.0, l=995.0, c=1000.0, v=100.0)         # small body(5) inside
check("Bearish Harami POS", c2, "bearish_harami", PatternDirection.BEARISH)

c1n = _append(base_up, o=990.0, h=1012.0, l=988.0, c=1010.0, v=100.0)
c2n = _append(c1n, o=980.0, h=1030.0, l=975.0, c=985.0, v=100.0)         # bigger body, not contained
check("Bearish Harami NEG (C2 body not contained)", c2n, None)


print("\n========== PIERCING LINE ==========\n")
c1 = _append(base_down, o=1010.0, h=1012.0, l=988.0, c=990.0, v=100.0)   # bearish, body 20, midpoint=1000
c2 = _append(c1, o=980.0, h=1008.0, l=978.0, c=1005.0, v=100.0)          # gaps down, closes above midpoint(1000)
check("Piercing Line POS", c2, "piercing_line", PatternDirection.BULLISH)

c1n = _append(base_down, o=1010.0, h=1012.0, l=988.0, c=990.0, v=100.0)
c2n = _append(c1n, o=980.0, h=996.0, l=978.0, c=995.0, v=100.0)          # closes below midpoint(1000)
check("Piercing Line NEG (doesn't close above midpoint)", c2n, None)

c1e = _append(base_down, o=1010.0, h=1012.0, l=988.0, c=990.0, v=100.0)
c2e = _append(c1e, o=980.0, h=1001.0, l=978.0, c=1000.0, v=100.0)        # closes exactly AT midpoint (strict > required)
check("Piercing Line EDGE (closes exactly at midpoint, strict > fails)", c2e, None)


print("\n========== DARK CLOUD COVER ==========\n")
c1 = _append(base_up, o=990.0, h=1012.0, l=988.0, c=1010.0, v=100.0)     # bullish, body 20, midpoint=1000
c2 = _append(c1, o=1020.0, h=1022.0, l=995.0, c=997.0, v=100.0)          # gaps up, closes below midpoint(1000)
check("Dark Cloud Cover POS", c2, "dark_cloud_cover", PatternDirection.BEARISH)

c1n = _append(base_up, o=990.0, h=1012.0, l=988.0, c=1010.0, v=100.0)
c2n = _append(c1n, o=1020.0, h=1022.0, l=1004.0, c=1005.0, v=100.0)      # closes above midpoint
check("Dark Cloud Cover NEG (doesn't close below midpoint)", c2n, None)


print("\n========== TWEEZER BOTTOM ==========\n")
c1 = _append(base_down, o=1005.0, h=1010.0, l=980.0, c=1000.0, v=100.0)
c2 = _append(c1, o=999.0, h=1015.0, l=980.1, c=1010.0, v=100.0)          # low within 0.15% of C1.low
check("Tweezer Bottom POS", c2, "tweezer_bottom", PatternDirection.BULLISH)

c1n = _append(base_down, o=1005.0, h=1010.0, l=980.0, c=1000.0, v=100.0)
c2n = _append(c1n, o=999.0, h=1015.0, l=970.0, c=1010.0, v=100.0)        # low far from C1.low
check("Tweezer Bottom NEG (lows not equal)", c2n, None)


print("\n========== TWEEZER TOP ==========\n")
c1 = _append(base_up, o=995.0, h=1020.0, l=990.0, c=1010.0, v=100.0)
c2 = _append(c1, o=1005.0, h=1019.9, l=985.0, c=995.0, v=100.0)          # high within 0.15% of C1.high
check("Tweezer Top POS", c2, "tweezer_top", PatternDirection.BEARISH)

c1n = _append(base_up, o=995.0, h=1020.0, l=990.0, c=1010.0, v=100.0)
c2n = _append(c1n, o=1005.0, h=1035.0, l=985.0, c=995.0, v=100.0)        # highs not equal
check("Tweezer Top NEG (highs not equal)", c2n, None)


print("\n========== RESULTS ==========\n")
passed = sum(1 for _, ok, _ in results_log if ok)
print(f"{passed}/{len(results_log)} checks passed")
print("\nPASS: all two-candle pattern audits passed" if passed == len(results_log) else "FAIL: see above")
