"""TrendlineTool — direction/strength on live data + synthetic uptrends."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.app.schemas.pattern import PatternDirection
from backend.app.services.analysis.analysis_factory import AnalysisFactory
from backend.app.services.analysis.trend_tool import TrendlineTool
from backend.app.services.market_service import MarketService


def _series_to_df(closes: np.ndarray) -> pd.DataFrame:
    n = len(closes)
    base_time = datetime(2026, 1, 1)  # tz-naive — matches real market data's dtype (see swing_detector .item() usage)
    timestamps = [base_time + timedelta(hours=i) for i in range(n)]
    return pd.DataFrame({
        "timestamps": timestamps,
        "open": closes - 0.1,
        "high": closes + 0.5,
        "low": closes - 0.5,
        "close": closes,
        "volume": np.full(n, 100.0),
    })


def _monotonic_uptrend(n: int = 250) -> pd.DataFrame:
    """No real oscillation — drift dominates, so no genuine swing highs/lows
    should form (correct behavior: a straight line has no structure to read,
    only a slope)."""
    return _series_to_df(100 + np.arange(n) * 0.5 + np.sin(np.arange(n) / 5) * 0.8)


def _oscillating_uptrend(n: int = 250) -> pd.DataFrame:
    """Drift small relative to oscillation amplitude, so distinct local
    peaks/troughs (swing highs/lows) form on top of the rising trend —
    exercises the channel-fitting + HH/HL structure path."""
    return _series_to_df(100 + np.arange(n) * 0.15 + np.sin(np.arange(n) / 3.2) * 6)


print("\n========== FACTORY REGISTRATION ==========\n")
assert "trend" in AnalysisFactory.list_tools()
assert isinstance(AnalysisFactory.get_tool("trend"), TrendlineTool)
print("PASS: 'trend' registered in AnalysisFactory")

tool = TrendlineTool()

print("\n========== SYNTHETIC MONOTONIC UPTREND (no channel) ==========\n")
df = _monotonic_uptrend()
result = tool.analyze(df, "TESTUSDT", "1h")
print(result.summary)
assert result.bias == PatternDirection.BULLISH, f"expected BULLISH, got {result.bias}"
assert result.data["slope_direction"] == "RISING"
assert result.data["slope_pct_per_bar"] > 0
assert result.data["trend_strength_pct"] > 90, "clean synthetic uptrend should fit tightly"
assert [tl.label for tl in result.annotations.trendlines] == ["trend_line"], (
    "a driftless straight line has no swings — no channel should be drawn"
)
print("PASS: monotonic uptrend detected as BULLISH/RISING, high fit, trend line only")

print("\n========== SYNTHETIC OSCILLATING UPTREND (channel + structure) ==========\n")
df2 = _oscillating_uptrend()
result2 = tool.analyze(df2, "TESTUSDT", "1h")
print(result2.summary)
assert result2.bias == PatternDirection.BULLISH, f"expected BULLISH, got {result2.bias}"
assert result2.data["swing_highs_used"] >= 2 and result2.data["swing_lows_used"] >= 2
assert [tl.label for tl in result2.annotations.trendlines] == [
    "trend_line", "trend_resistance", "trend_support",
]
assert "higher highs" in result2.data["structure"]
print("PASS: oscillating uptrend produces HH/HL structure + a full channel")

print("\n========== LIVE DATA ==========\n")
market = MarketService().get_market_data(symbol="BTCUSDT", interval="1h", limit=300)
live_result = tool.analyze(market, "BTCUSDT", "1h")
print(live_result.bias, live_result.summary)
assert live_result.tool_key == "trend"
assert live_result.error is None
assert len(live_result.annotations.trendlines) >= 1
print("PASS: live BTCUSDT/1h scan returns a valid trend result")

print("\n========== RESULTS: all checks passed ==========")
