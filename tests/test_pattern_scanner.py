import backend.app.core.config  # noqa: F401 — triggers load_dotenv() for AI calls

from backend.app.core.pattern_config import pattern_config
from backend.app.services.market_service import MarketService
from backend.app.services.pattern.pattern_factory import PatternFactory
from backend.app.services.pattern.pattern_scanner import PatternScanner
from backend.app.services.pattern.fvg_detector import FVGDetector
from backend.app.services.pattern.swing_detector import SwingDetector

market = MarketService()
scanner = PatternScanner()

print("\n========== SWING DETECTOR ==========\n")
df = market.get_market_data(symbol="BTCUSDT", interval="1h", limit=300)
swings = SwingDetector().find_swings(df)
assert len(swings) > 0, "expected at least some swing points on 300 real candles"
print(f"PASS: found {len(swings)} swing points")

print("\n========== FVG DETECTOR ==========\n")
fvgs = FVGDetector().detect(df, "BTCUSDT", "1h")
for g in fvgs:
    assert g.top > g.bottom
    assert 0 <= g.strength <= 100
print(f"PASS: {len(fvgs)} FVGs, all well-formed")

print("\n========== ALL PATTERN DETECTORS (no AI) ==========\n")
for key in PatternFactory.list_detectors():
    detector = PatternFactory.get_detector(key)
    results = detector.detect(df, "BTCUSDT", "1h")
    for p in results:
        assert p.confidence >= 0 and p.confidence <= 100
        assert p.formation_start <= p.formation_end
        assert p.symbol == "BTCUSDT" and p.interval == "1h"
    print(f"{key:<20} -> {len(results)} pattern(s)")
print("PASS: every detector runs without error and returns well-formed patterns")

print("\n========== FULL SCAN (fast path, no AI — the new default) ==========\n")
import time as _time
t0 = _time.time()
result = scanner.scan("BTCUSDT", "1h", limit=300)
elapsed = _time.time() - t0
assert result.error is None
seen_ids = {p.id for p in result.patterns}
assert len(seen_ids) == len(result.patterns), "expected unique pattern ids"
for p in result.patterns:
    # The confidence floor only applies to the noisy candlestick family —
    # chart shapes and SMC structures bypass it deliberately (rare + wanted).
    if p.category == "candlestick":
        assert p.confidence >= pattern_config.PATTERN_SCAN_MIN_CONFIDENCE, "scan should filter below PATTERN_SCAN_MIN_CONFIDENCE"
    assert p.ai is None, "include_ai defaults to False — scan() should NOT auto-attach AI"
assert elapsed < 15.0, f"fast-path scan should be well under 15s, took {elapsed:.1f}s"
print(f"PASS: scan() returned {len(result.patterns)} patterns, {len(result.fvgs)} fvgs in {elapsed:.1f}s, no AI attached")

print("\n========== ON-DEMAND EXPLAIN (single pattern) ==========\n")
if result.patterns:
    explanation = scanner.explain_pattern(result.patterns[0])
    assert explanation.error is None, f"explain_pattern failed: {explanation.error}"
    print(f"PASS: explain_pattern() returned a recommendation of {explanation.recommendation}")
else:
    print("SKIP: no patterns found this run to explain")

print("\n========== FULL SCAN (include_ai=True, opt-in) ==========\n")
# Deliberately a much smaller limit than the main scan above: the
# candlestick-pattern engine (2026-07-04) finds far more patterns per scan
# than the old chart-shape detectors did (~129 vs ~30-54 at limit=300) —
# at limit=300 this assertion alone took ~4:42 wall-clock (pure NVIDIA API
# latency across ~129 sequential-batch AI calls, not a bug), which is far
# past a reasonable single-test budget. A smaller candle window keeps this
# test verifying the same thing (AI attaches to every pattern found) without
# the wait — include_ai=True's real-world cost scaling with pattern count is
# already documented/accepted behavior, not something this test needs to
# stress at full scale.
result_ai = scanner.scan("BTCUSDT", "1h", limit=60, include_ai=True)
for p in result_ai.patterns:
    assert p.ai is not None, "include_ai=True should attach an AI attempt to every pattern"
print(f"PASS: scan(include_ai=True) attached AI to all {len(result_ai.patterns)} patterns")

print("\n========== MULTI-TIMEFRAME SCAN ==========\n")
tf_results = scanner.scan_multi_timeframe("BTCUSDT", intervals=["15m", "1h"], limit=300)
assert len(tf_results) == 2
assert {r.interval for r in tf_results} == {"15m", "1h"}
print("PASS: scan_multi_timeframe returns one response per requested interval")

print("\n========== DASHBOARD ==========\n")
dash = scanner.dashboard("BTCUSDT", intervals=["1h"], limit=300)
confidences = [r.confidence for r in dash.rows]
assert confidences == sorted(confidences, reverse=True), "dashboard rows should be confidence-sorted"
print(f"PASS: dashboard returned {len(dash.rows)} rows, sorted by confidence")

print("\n========== RESULTS: all checks passed ==========")
