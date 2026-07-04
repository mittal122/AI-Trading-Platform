"""Shared per-candle metrics + context helpers for the candlestick pattern
detectors (single/two/three-candle). Keeps body/wick/trend math in one
place instead of duplicating it across ~30 pattern checks."""

from dataclasses import dataclass

import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.services.pattern.trendline import classify_slope, fit_trendline, slope_pct_per_bar


@dataclass
class CandleMetrics:
    idx: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: str

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def total_range(self) -> float:
        return self.high - self.low

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.open > self.close

    @property
    def midpoint(self) -> float:
        return (self.open + self.close) / 2


def candle_metrics(df: pd.DataFrame, idx: int) -> CandleMetrics:
    row = df.iloc[idx]
    return CandleMetrics(
        idx=idx,
        open=float(row["open"]), high=float(row["high"]),
        low=float(row["low"]), close=float(row["close"]),
        volume=float(row["volume"]),
        timestamp=row["timestamps"].isoformat(),
    )


def is_marubozu(m: CandleMetrics) -> bool:
    if m.total_range <= 0:
        return False
    tol = m.total_range * pattern_config.CANDLESTICK_WICK_TOLERANCE_PCT / 100
    return m.upper_wick <= tol and m.lower_wick <= tol and m.body >= m.total_range * 0.95


def is_doji(m: CandleMetrics) -> bool:
    if m.total_range <= 0:
        return False
    return m.body <= m.total_range * pattern_config.CANDLESTICK_DOJI_BODY_MAX_PCT / 100


def is_long_lower_wick(m: CandleMetrics) -> bool:
    if m.total_range <= 0:
        return False
    return m.lower_wick >= m.total_range * pattern_config.CANDLESTICK_LONG_WICK_MIN_PCT / 100


def is_long_upper_wick(m: CandleMetrics) -> bool:
    if m.total_range <= 0:
        return False
    return m.upper_wick >= m.total_range * pattern_config.CANDLESTICK_LONG_WICK_MIN_PCT / 100


def wick_at_least(wick: float, body: float) -> bool:
    """wick >= ratio * body — with body==0 (a doji-like candle) treated as
    satisfying any positive wick, so a hammer-shaped doji still qualifies."""
    ratio = pattern_config.CANDLESTICK_WICK_TO_BODY_RATIO
    if body <= 0:
        return wick > 0
    return wick >= body * ratio


def roughly_equal(a: float, b: float, tolerance_pct: float) -> bool:
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(abs(a), abs(b)) <= tolerance_pct / 100


def gapped_up(prev: CandleMetrics, curr: CandleMetrics) -> bool:
    min_gap = prev.high * pattern_config.CANDLESTICK_GAP_MIN_PCT / 100
    return curr.open > prev.high + min_gap


def gapped_down(prev: CandleMetrics, curr: CandleMetrics) -> bool:
    min_gap = prev.low * pattern_config.CANDLESTICK_GAP_MIN_PCT / 100
    return curr.open < prev.low - min_gap


def higher_volume(curr: CandleMetrics, prev: CandleMetrics) -> bool:
    return curr.volume > prev.volume * pattern_config.CANDLESTICK_VOLUME_MULTIPLIER


def local_trend(df: pd.DataFrame, idx: int) -> str:
    """UP / DOWN / FLAT — least-squares slope of closes over a short local
    window ending at idx (not including idx itself, so the pattern's own
    candle(s) don't bias the "prior trend" read). Reuses the same
    fit_trendline/classify_slope primitives as the Trend Line analysis tool."""
    cfg = pattern_config
    lookback = cfg.CANDLESTICK_TREND_LOOKBACK_BARS
    start = max(0, idx - lookback)
    if start >= idx or idx - start < 3:
        return "FLAT"
    closes = df["close"].iloc[start:idx].tolist()
    fit = fit_trendline(list(range(len(closes))), closes)
    reference_price = closes[-1]
    slope_pct = slope_pct_per_bar(fit, reference_price)
    label = classify_slope(slope_pct, cfg.CANDLESTICK_TREND_FLAT_TOLERANCE_PCT)
    return {"RISING": "UP", "FALLING": "DOWN", "FLAT": "FLAT"}[label]
