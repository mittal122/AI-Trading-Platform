"""Candlestick pattern engine — factory registration, live-data smoke run
across all ~32 patterns, and synthetic positive-path checks for a
representative sample from each of the three detector files (single/two/
three-candle). Full exhaustive per-pattern synthetic coverage would be ~32
cases; this covers the shared mechanics (trend-context gating, confirmation
via status_from_breakout, entry/stop/target math) once per family, which is
what would actually break if the shared helpers had a bug.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.app.schemas.pattern import PatternDirection, PatternStatus
from backend.app.services.market_service import MarketService
from backend.app.services.pattern.pattern_factory import PatternFactory
from backend.app.services.pattern.pattern_scanner import PatternScanner
from backend.app.services.pattern.single_candle_patterns import SingleCandlePatternDetector
from backend.app.services.pattern.three_candle_patterns import ThreeCandlePatternDetector
from backend.app.services.pattern.two_candle_patterns import TwoCandlePatternDetector


def _base_df(n=40, direction="DOWN", start_price=100.0, step=0.6):
    base_time = datetime(2026, 1, 1)  # tz-naive — matches real market data dtype
    timestamps = [base_time + timedelta(hours=i) for i in range(n)]
    sign = -1 if direction == "DOWN" else (1 if direction == "UP" else 0)
    closes = start_price + sign * np.arange(n) * step
    opens = closes - sign * step * 0.3
    highs = np.maximum(opens, closes) + 0.2
    lows = np.minimum(opens, closes) - 0.2
    return pd.DataFrame({
        "timestamps": timestamps, "open": opens, "high": highs,
        "low": lows, "close": closes, "volume": np.full(n, 100.0),
    })


def _append(df, o, h, l, c, v=100.0):
    ts = df["timestamps"].iloc[-1] + timedelta(hours=1)
    row = pd.DataFrame([{"timestamps": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}])
    return pd.concat([df, row], ignore_index=True)


def _find(results, pattern_type):
    matches = [p for p in results if p.pattern_type == pattern_type]
    assert matches, f"expected a '{pattern_type}' detection, found types: {[p.pattern_type for p in results]}"
    return matches[-1]


print("\n========== FACTORY REGISTRATION ==========\n")
assert set(PatternFactory.list_detectors()) == {"single_candle", "two_candle", "three_candle", "smc"}
print("PASS: old chart-shape detectors gone, candlestick + SMC detectors registered")

print("\n========== SINGLE-CANDLE: Marubozu (no trend requirement) ==========\n")
df = _base_df(direction="FLAT")
df = _append(df, o=100.0, h=110.2, l=99.8, c=110.0)
results = SingleCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "marubozu")
assert p.direction == PatternDirection.BULLISH
assert p.breakout_level == 110.2 and p.stop_loss == 99.8
print(f"PASS: {p.pattern_name} — {p.direction}, status={p.status}")

print("\n========== SINGLE-CANDLE: Standard Doji (neutral) ==========\n")
df = _base_df(direction="FLAT")
df = _append(df, o=100.0, h=101.0, l=99.0, c=100.0)
results = SingleCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "standard_doji")
assert p.direction == PatternDirection.NEUTRAL
assert p.status == PatternStatus.DEVELOPING
assert p.stop_loss is None and p.target_1 is None, "a true neutral doji should have no fixed stop/target"
print(f"PASS: {p.pattern_name} — correctly direction-neutral with no fixed stop/target")

print("\n========== SINGLE-CANDLE: Dragonfly Doji (requires downtrend) ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=100.0, h=100.2, l=95.0, c=100.0)
results = SingleCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "dragonfly_doji")
assert p.direction == PatternDirection.BULLISH
print(f"PASS: {p.pattern_name} — {p.direction}, status={p.status}")

print("\n========== SINGLE-CANDLE: Hammer (1:2 R/R target) ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=100.0, h=100.4, l=97.0, c=100.3)
results = SingleCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "hammer")
assert p.direction == PatternDirection.BULLISH
assert abs(p.risk_reward - 2.0) < 0.05, f"expected ~2.0 R/R, got {p.risk_reward}"
print(f"PASS: {p.pattern_name} — R/R={p.risk_reward}")

print("\n========== TWO-CANDLE: Bullish Engulfing ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=100.0, h=100.3, l=96.8, c=97.0, v=100.0)
df = _append(df, o=96.5, h=101.3, l=96.3, c=101.0, v=250.0)
results = TwoCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "bullish_engulfing")
assert p.direction == PatternDirection.BULLISH
assert p.breakout_level == 101.3 and p.stop_loss == 96.3
print(f"PASS: {p.pattern_name} — {p.direction}, status={p.status}")

print("\n========== TWO-CANDLE: Piercing Line ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=100.0, h=100.3, l=94.8, c=95.0)
df = _append(df, o=94.0, h=98.3, l=93.8, c=98.0)  # closes above (100+95)/2 = 97.5
results = TwoCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "piercing_line")
assert p.direction == PatternDirection.BULLISH
print(f"PASS: {p.pattern_name} — {p.direction}, status={p.status}")

print("\n========== TWO-CANDLE: Tweezer Bottom ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=99.0, h=99.5, l=95.0, c=96.0)
df = _append(df, o=96.5, h=99.8, l=95.05, c=99.0)  # low within 0.15% of prior low
results = TwoCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "tweezer_bottom")
assert p.direction == PatternDirection.BULLISH
print(f"PASS: {p.pattern_name} — {p.direction}, status={p.status}")

print("\n========== THREE-CANDLE: Morning Star ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=100.0, h=100.3, l=89.8, c=90.0)          # C1 — big bearish
df = _append(df, o=88.0, h=88.5, l=87.5, c=87.0)            # C2 — small star, gaps below C1 close
df = _append(df, o=89.0, h=97.3, l=88.8, c=97.0)            # C3 — bullish, closes well into C1 body (>95)
results = ThreeCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "morning_star")
assert p.direction == PatternDirection.BULLISH
print(f"PASS: {p.pattern_name} — {p.direction}, status={p.status}")

print("\n========== THREE-CANDLE: Three White Soldiers (trailing stop, no fixed target) ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=90.0, h=93.3, l=89.8, c=93.0)
df = _append(df, o=93.2, h=96.3, l=93.0, c=96.0)
df = _append(df, o=96.2, h=99.3, l=96.0, c=99.0)
results = ThreeCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "three_white_soldiers")
assert p.direction == PatternDirection.BULLISH
assert p.target_1 is None, "Three White Soldiers uses a trailing stop, not a fixed target"
print(f"PASS: {p.pattern_name} — {p.direction}, target_1={p.target_1} (trailing stop, as expected)")

print("\n========== THREE-CANDLE: Three Inside Up ==========\n")
df = _base_df(direction="DOWN")
df = _append(df, o=100.0, h=100.3, l=89.8, c=90.0)   # C1 — bearish mother
df = _append(df, o=91.0, h=98.3, l=90.8, c=98.0)      # C2 — smaller body inside C1
df = _append(df, o=98.2, h=102.3, l=98.0, c=102.0)    # C3 — closes above C1's open (100)
results = ThreeCandlePatternDetector().detect(df, "TESTUSDT", "1h")
p = _find(results, "three_inside_up")
assert p.direction == PatternDirection.BULLISH
assert abs(p.risk_reward - 1.5) < 0.05, f"expected ~1.5 R/R, got {p.risk_reward}"
print(f"PASS: {p.pattern_name} — R/R={p.risk_reward}")

print("\n========== LIVE DATA — all detectors, no errors ==========\n")
market = MarketService().get_market_data(symbol="BTCUSDT", interval="1h", limit=300)
for key in PatternFactory.list_detectors():
    detector = PatternFactory.get_detector(key)
    live_results = detector.detect(market, "BTCUSDT", "1h")
    for p in live_results:
        assert 0 <= p.confidence <= 100
        assert p.formation_start <= p.formation_end
    print(f"{key:<15} -> {len(live_results)} pattern(s)")
print("PASS: every registered detector runs cleanly on live data")

print("\n========== FULL SCAN VIA PatternScanner (fast path) ==========\n")
scanner = PatternScanner()
result = scanner.scan("BTCUSDT", "1h", limit=300)
assert result.error is None
for p in result.patterns:
    assert p.confidence >= 40.0
print(f"PASS: scan() returned {len(result.patterns)} candlestick/SMC patterns, {len(result.fvgs)} fvgs")

print("\n========== RESULTS: all checks passed ==========")
