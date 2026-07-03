from backend.app.services.strategy.signal_scanner import SignalScanner
from backend.app.services.strategy.strategy_factory import StrategyFactory

scanner = SignalScanner()

print("\n========== SCAN ALL STRATEGIES ==========\n")

results = scanner.scan_all_strategies(symbol="BTCUSDT", interval="1h", limit=300)

assert len(results) == len(StrategyFactory.list_strategies())
seen_strategies = {r.strategy for r in results}
assert len(seen_strategies) == len(results), "expected one signal per strategy, got duplicates"

for r in results:
    print(f"{r.strategy:<20} {r.direction.value:<5} conf={r.confidence:5.1f}  eta={r.eta_display}  error={r.error}")
    assert r.error is None, f"{r.strategy} failed: {r.error}"

print("\nPASS: scan_all_strategies returns one signal per registered strategy, no errors")

print("\n========== SCAN MULTI-TIMEFRAME ==========\n")

tf_results = scanner.scan_timeframes(strategy="rsi", symbol="BTCUSDT", intervals=["5m", "15m", "1h"], limit=300)

assert len(tf_results) == 3
assert {r.interval for r in tf_results} == {"5m", "15m", "1h"}

for r in tf_results:
    print(f"{r.interval:<5} {r.direction.value:<5} conf={r.confidence:5.1f}  eta={r.eta_display}")
    assert r.error is None, f"{r.interval} failed: {r.error}"

print("\nPASS: scan_timeframes returns one signal per requested interval, no errors")

print("\n========== RESULTS: all checks passed ==========")
