"""Dedicated audit suite — three/four-candle patterns (Batch 3 of 3).

Same POSITIVE / NEGATIVE / EDGE structure. Run after any change to
three_candle_patterns.py.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.app.schemas.pattern import PatternDirection
from backend.app.services.pattern.three_candle_patterns import ThreeCandlePatternDetector


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


DET = ThreeCandlePatternDetector()
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


def check_not(name, built_df, forbidden_type):
    at_last = _detect_last(built_df)
    ok = not any(p.pattern_type == forbidden_type for p in at_last)
    results_log.append((name, ok, f"got {[p.pattern_type for p in at_last]}"))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} — got {[p.pattern_type for p in at_last]}")
    assert ok


base_down = _base_df(direction="DOWN")
base_up = _base_df(direction="UP")


# ============================================================
print("\n========== MORNING STAR ==========\n")
c1 = _append(base_down, o=1000.0, h=1003.0, l=898.0, c=900.0, v=100.0)   # bearish, body=100, midpoint=950
c2 = _append(c1, o=880.0, h=881.0, l=879.0, c=879.5, v=100.0)             # star, body-top=880 < c1.close(900)
c3 = _append(c2, o=890.0, h=970.0, l=888.0, c=965.0, v=100.0)             # gaps up from c2(body-top 881), closes>950
check("Morning Star POS", c3, "morning_star", PatternDirection.BULLISH)

# NEG — regression: C3 overlaps C2's body instead of gapping up from it
# (old code only checked "C3 closes above C1's midpoint", missing "C3 gaps
# up from C2" — this shape used to wrongly pass).
c1n = _append(base_down, o=1000.0, h=1003.0, l=898.0, c=900.0, v=100.0)
c2n = _append(c1n, o=880.0, h=881.0, l=879.0, c=879.5, v=100.0)
c3n = _append(c2n, o=875.0, h=970.0, l=873.0, c=965.0, v=100.0)  # opens BELOW c2's body (875 < 879), overlaps
check_not("Morning Star NEG (regression: C3 doesn't gap up from C2)", c3n, "morning_star")

print("\n========== EVENING STAR ==========\n")
c1 = _append(base_up, o=900.0, h=1002.0, l=897.0, c=1000.0, v=100.0)      # bullish, body=100, midpoint=950
c2 = _append(c1, o=1019.0, h=1021.0, l=1018.5, c=1020.0, v=100.0)         # star, body-bottom=1019 > c1.close(1000)
c3 = _append(c2, o=1010.0, h=1012.0, l=930.0, c=935.0, v=100.0)           # gaps down from c2(body-bottom 1019), closes<950
check("Evening Star POS", c3, "evening_star", PatternDirection.BEARISH)

c1n = _append(base_up, o=900.0, h=1002.0, l=897.0, c=1000.0, v=100.0)
c2n = _append(c1n, o=1019.0, h=1021.0, l=1018.5, c=1020.0, v=100.0)
c3n = _append(c2n, o=1025.0, h=1027.0, l=930.0, c=935.0, v=100.0)  # opens ABOVE c2's body, overlaps (doesn't gap down)
check_not("Evening Star NEG (regression: C3 doesn't gap down from C2)", c3n, "evening_star")


print("\n========== BULLISH ABANDONED BABY ==========\n")
c1 = _append(base_down, o=1000.0, h=1003.0, l=898.0, c=900.0, v=100.0)
c2 = _append(c1, o=890.0, h=892.0, l=886.0, c=890.2, v=100.0)   # true doji (body=0.2, range=6, ratio=3.3%), gaps below c1.low(898)
c3 = _append(c2, o=905.0, h=970.0, l=900.0, c=965.0, v=100.0)   # gaps above c2.high(892)
check("Bullish Abandoned Baby POS", c3, "bullish_abandoned_baby", PatternDirection.BULLISH)

c1n = _append(base_down, o=1000.0, h=1003.0, l=898.0, c=900.0, v=100.0)
c2n = _append(c1n, o=890.0, h=892.0, l=886.0, c=890.2, v=100.0)  # same doji
c3n = _append(c2n, o=888.0, h=970.0, l=884.0, c=965.0, v=100.0)  # opens/lows INSIDE c2's range -> does NOT gap above
check_not("Bullish Abandoned Baby NEG (C3 doesn't gap above C2)", c3n, "bullish_abandoned_baby")


print("\n========== BEARISH ABANDONED BABY ==========\n")
c1 = _append(base_up, o=900.0, h=1002.0, l=897.0, c=1000.0, v=100.0)
c2 = _append(c1, o=1010.0, h=1013.0, l=1006.0, c=1010.3, v=100.0)  # true doji (body=0.3, range=7, ratio=4.3%), gaps above c1.high(1002)
c3 = _append(c2, o=995.0, h=1000.0, l=930.0, c=935.0, v=100.0)     # gaps below c2.low(1006)
check("Bearish Abandoned Baby POS", c3, "bearish_abandoned_baby", PatternDirection.BEARISH)


print("\n========== THREE WHITE SOLDIERS ==========\n")
c1 = _append(base_down, o=900.0, h=933.3, l=898.0, c=933.0, v=100.0)
c2 = _append(c1, o=920.0, h=963.3, l=919.0, c=963.0, v=100.0)   # opens within C1's body [900,933]
c3 = _append(c2, o=950.0, h=993.3, l=949.0, c=993.0, v=100.0)   # opens within C2's body [920,963]
check("Three White Soldiers POS", c3, "three_white_soldiers", PatternDirection.BULLISH)

# NEG — regression: C3 gaps up AWAY from C2's body entirely (parabolic, not
# a genuine grinding advance) — old code only checked closes ascending,
# missing "opens within prior body."
c1n = _append(base_down, o=900.0, h=933.3, l=898.0, c=933.0, v=100.0)
c2n = _append(c1n, o=920.0, h=963.3, l=919.0, c=963.0, v=100.0)
c3n = _append(c2n, o=1000.0, h=1033.3, l=999.0, c=1033.0, v=100.0)  # opens WAY above C2's body (gaps away)
check_not("Three White Soldiers NEG (regression: C3 gaps away from C2's body)", c3n, "three_white_soldiers")


print("\n========== THREE BLACK CROWS ==========\n")
c1 = _append(base_up, o=1000.0, h=1002.0, l=966.7, c=967.0, v=100.0)
c2 = _append(c1, o=980.0, h=982.0, l=936.7, c=937.0, v=100.0)   # opens within C1's body
c3 = _append(c2, o=950.0, h=952.0, l=906.7, c=907.0, v=100.0)   # opens within C2's body
check("Three Black Crows POS", c3, "three_black_crows", PatternDirection.BEARISH)

c1n = _append(base_up, o=1000.0, h=1002.0, l=966.7, c=967.0, v=100.0)
c2n = _append(c1n, o=980.0, h=982.0, l=936.7, c=937.0, v=100.0)
c3n = _append(c2n, o=880.0, h=882.0, l=846.7, c=847.0, v=100.0)  # gaps way below C2's body
check_not("Three Black Crows NEG (regression: C3 gaps away from C2's body)", c3n, "three_black_crows")


print("\n========== BULLISH THREE LINE STRIKE ==========\n")
c1 = _append(base_down, o=1000.0, h=1002.0, l=970.0, c=972.0, v=100.0)
c2 = _append(c1, o=970.0, h=972.0, l=940.0, c=942.0, v=100.0)
c3 = _append(c2, o=940.0, h=942.0, l=910.0, c=912.0, v=100.0)
c4 = _append(c3, o=912.0, h=1015.0, l=910.0, c=1005.0, v=100.0)  # massive bullish, closes above c1.open(1000)
check("Bullish Three Line Strike POS", c4, "bullish_three_line_strike", PatternDirection.BULLISH)

c4n = _append(c3, o=912.0, h=999.0, l=910.0, c=995.0, v=100.0)   # closes below c1.open(1000) — doesn't strike out
check_not("Bullish Three Line Strike NEG (C4 doesn't close above C1.open)", c4n, "bullish_three_line_strike")


print("\n========== BEARISH THREE LINE STRIKE ==========\n")
c1 = _append(base_up, o=900.0, h=930.0, l=898.0, c=928.0, v=100.0)
c2 = _append(c1, o=928.0, h=960.0, l=926.0, c=958.0, v=100.0)
c3 = _append(c2, o=958.0, h=990.0, l=956.0, c=988.0, v=100.0)
c4 = _append(c3, o=988.0, h=990.0, l=885.0, c=895.0, v=100.0)    # massive bearish, closes below c1.open(900)
check("Bearish Three Line Strike POS", c4, "bearish_three_line_strike", PatternDirection.BEARISH)


print("\n========== THREE OUTSIDE UP ==========\n")
c1 = _append(base_down, o=1000.0, h=1002.0, l=988.0, c=990.0, v=100.0)   # bearish
c2 = _append(c1, o=985.0, h=1010.0, l=983.0, c=1005.0, v=250.0)          # bullish, engulfs
c3 = _append(c2, o=1006.0, h=1020.0, l=1004.0, c=1015.0, v=300.0)        # closes higher than c2, higher vol than c1
check("Three Outside Up POS", c3, "three_outside_up", PatternDirection.BULLISH)

# NEG — regression: C1 is bullish (wrong color), small C2 inside it —
# satisfies overlap math but is not a real engulfing pair.
c1n = _append(base_down, o=1000.0, h=1008.0, l=998.0, c=1005.0, v=100.0)  # bullish (wrong)
c2n = _append(c1n, o=1002.0, h=1006.0, l=1001.0, c=1004.0, v=250.0)       # small bullish inside
c3n = _append(c2n, o=1004.0, h=1010.0, l=1003.0, c=1009.0, v=300.0)
check_not("Three Outside Up NEG (regression: wrong C1/C2 colors)", c3n, "three_outside_up")


print("\n========== THREE OUTSIDE DOWN ==========\n")
c1 = _append(base_up, o=990.0, h=1002.0, l=988.0, c=1000.0, v=100.0)     # bullish
c2 = _append(c1, o=1005.0, h=1007.0, l=980.0, c=985.0, v=100.0)          # bearish, engulfs
c3 = _append(c2, o=984.0, h=986.0, l=970.0, c=975.0, v=100.0)            # closes lower than c2
check("Three Outside Down POS", c3, "three_outside_down", PatternDirection.BEARISH)

c1n = _append(base_up, o=1005.0, h=1008.0, l=998.0, c=1000.0, v=100.0)   # bearish (wrong)
c2n = _append(c1n, o=1002.0, h=1004.0, l=1000.0, c=1001.0, v=100.0)      # small bearish inside
c3n = _append(c2n, o=1001.0, h=1002.0, l=995.0, c=996.0, v=100.0)
check_not("Three Outside Down NEG (regression: wrong C1/C2 colors)", c3n, "three_outside_down")


print("\n========== THREE INSIDE UP ==========\n")
c1 = _append(base_down, o=1010.0, h=1012.0, l=988.0, c=990.0, v=100.0)   # bearish, big body
c2 = _append(c1, o=995.0, h=1005.0, l=993.0, c=1000.0, v=100.0)          # small body inside
c3 = _append(c2, o=1001.0, h=1020.0, l=999.0, c=1015.0, v=100.0)         # closes above c1.open(1010)
check("Three Inside Up POS", c3, "three_inside_up", PatternDirection.BULLISH)


print("\n========== THREE INSIDE DOWN ==========\n")
c1 = _append(base_up, o=990.0, h=1012.0, l=988.0, c=1010.0, v=100.0)     # bullish, big body
c2 = _append(c1, o=1005.0, h=1007.0, l=995.0, c=1000.0, v=100.0)         # small body inside
c3 = _append(c2, o=999.0, h=1001.0, l=980.0, c=985.0, v=100.0)           # closes below c1.open(990)
check("Three Inside Down POS", c3, "three_inside_down", PatternDirection.BEARISH)


print("\n========== RESULTS ==========\n")
passed = sum(1 for _, ok, _ in results_log if ok)
print(f"{passed}/{len(results_log)} checks passed")
print("\nPASS: all three-candle pattern audits passed" if passed == len(results_log) else "FAIL: see above")
