import backend.app.core.config  # noqa: F401 — triggers load_dotenv() for AI calls

from backend.app.services.market_service import MarketService
from backend.app.services.analysis.analysis_factory import AnalysisFactory
from backend.app.services.analysis.analysis_scanner import AnalysisScanner

market = MarketService()
scanner = AnalysisScanner()

print("\n========== ALL ANALYSIS TOOLS (no AI) ==========\n")
df = market.get_market_data(symbol="BTCUSDT", interval="1h", limit=300)

for key in AnalysisFactory.list_tools():
    tool = AnalysisFactory.get_tool(key)
    result = tool.analyze(df, "BTCUSDT", "1h")
    assert result.error is None, f"{key} failed: {result.error}"
    assert result.symbol == "BTCUSDT" and result.interval == "1h"
    assert result.bias in ("BULLISH", "BEARISH", "NEUTRAL")
    assert result.summary
    print(f"{key:<20} -> {result.bias:<8} {result.summary[:80]}")
print("\nPASS: every tool runs without error and returns well-formed results")

print("\n========== SCANNER (concurrent, subset of tools) ==========\n")
result = scanner.scan("BTCUSDT", "1h", tool_keys=["vwap", "atr"], limit=300)
assert len(result.tools) == 2
assert {t.tool_key for t in result.tools} == {"vwap", "atr"}
print("PASS: scanner runs only the requested tools")

print("\n========== SCANNER (default = all tools) ==========\n")
result = scanner.scan("BTCUSDT", "1h", limit=300)
assert len(result.tools) == len(AnalysisFactory.list_tools())
print(f"PASS: scanner defaults to all {len(result.tools)} registered tools")

print("\n========== AI CONFLUENCE EXPLAINER ==========\n")
from backend.app.services.ai.analysis_explainer import AnalysisExplainer

explainer = AnalysisExplainer()
explanation = explainer.explain("BTCUSDT", "1h", result.tools)
assert explanation.error is None, f"AI explanation failed: {explanation.error}"
assert explanation.reasoning, "expected non-empty reasoning"
print(f"PASS: AI confluence bias={explanation.market_bias} confidence={explanation.confidence_score}")

print("\n========== RESULTS: all checks passed ==========")
