"""Shared per-candle metrics + context helpers for the candlestick pattern
detectors (single/two/three-candle). Keeps body/wick/trend math in one
place instead of duplicating it across ~30 pattern checks."""

from dataclasses import dataclass

import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import PatternDirection, PatternStatus, ZoneAnnotation
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


def gapped_up(prev: CandleMetrics, curr: CandleMetrics) -> bool:
    min_gap = prev.high * pattern_config.CANDLESTICK_GAP_MIN_PCT / 100
    return curr.open > prev.high + min_gap


def gapped_down(prev: CandleMetrics, curr: CandleMetrics) -> bool:
    min_gap = prev.low * pattern_config.CANDLESTICK_GAP_MIN_PCT / 100
    return curr.open < prev.low - min_gap


def higher_volume(curr: CandleMetrics, prev: CandleMetrics) -> bool:
    return curr.volume > prev.volume * pattern_config.CANDLESTICK_VOLUME_MULTIPLIER


def opens_within_body(prev: CandleMetrics, curr: CandleMetrics) -> bool:
    """curr opens inside prev's real body — a genuine grinding advance/
    decline, not a gap away from it. Used by Three White Soldiers/Black
    Crows to exclude parabolic runs of same-colored candles that merely
    close progressively higher/lower without actually building on each
    other's range."""
    lo, hi = min(prev.open, prev.close), max(prev.open, prev.close)
    return lo <= curr.open <= hi


def resolve_forward_status(
    df: pd.DataFrame,
    end_idx: int,
    direction: PatternDirection,
    breakout_level: float,
    invalidation_level: float,
    atr: float,
) -> PatternStatus:
    """Resolve a pattern's status against the candles that came AFTER it —
    not against today's price, which is meaningless for a pattern formed
    hundreds of bars ago (the old `status_from_breakout(current_price=...)`
    approach marked historical patterns CONFIRMED/BROKEN essentially at
    random once the full-chart scan landed).

    Walks forward bar by bar from the pattern's completion; whichever level
    is touched first decides. Invalidation is checked before breakout within
    the same bar — the pessimistic read when one candle spans both.

    Still unresolved at the live edge of the chart, inside the window →
    DEVELOPING (a genuinely open setup). Unresolved past the window →
    BROKEN: the setup expired without triggering and is no longer tradeable.
    """
    cfg = pattern_config
    margin = cfg.BREAKOUT_CONFIRMATION_ATR_MULT * atr
    n = len(df)
    window_end = min(n, end_idx + 1 + cfg.CANDLESTICK_CONFIRMATION_WINDOW_BARS)

    for i in range(end_idx + 1, window_end):
        high = float(df["high"].iloc[i])
        low = float(df["low"].iloc[i])
        if direction == PatternDirection.BULLISH:
            if low <= invalidation_level:
                return PatternStatus.BROKEN
            if high >= breakout_level + margin:
                return PatternStatus.CONFIRMED
        else:
            if high >= invalidation_level:
                return PatternStatus.BROKEN
            if low <= breakout_level - margin:
                return PatternStatus.CONFIRMED

    still_in_window = (n - (end_idx + 1)) < cfg.CANDLESTICK_CONFIRMATION_WINDOW_BARS
    return PatternStatus.DEVELOPING if still_in_window else PatternStatus.BROKEN


# Feeds algorithmic_confidence's breakout-strength component from the
# pattern's actual resolved outcome — a pattern that triggered cleanly IS
# the evidence of breakout strength; one that expired or failed isn't.
STATUS_STRENGTH_SCORE = {
    PatternStatus.CONFIRMED: 85.0,
    PatternStatus.DEVELOPING: 45.0,
    PatternStatus.BROKEN: 15.0,
}


def formation_zone(
    df: pd.DataFrame, start_idx: int, end_idx: int, label: str, direction: PatternDirection,
) -> ZoneAnnotation:
    """Rectangle spanning the candles that form the pattern — this is what
    actually DRAWS the pattern on the chart (rendered by the frontend's
    RectanglesPrimitive, same machinery FVG zones already use). The right
    edge extends one bar past the last formation candle so a single-candle
    pattern still has visible width instead of a zero-width line."""
    segment = df.iloc[start_idx: end_idx + 1]
    top = float(segment["high"].max())
    bottom = float(segment["low"].min())
    n = len(df)
    if end_idx + 1 < n:
        end_time = df["timestamps"].iloc[end_idx + 1]
    elif n >= 2:
        end_time = df["timestamps"].iloc[end_idx] + (df["timestamps"].iloc[-1] - df["timestamps"].iloc[-2])
    else:
        end_time = df["timestamps"].iloc[end_idx]
    return ZoneAnnotation(
        label=label,
        start_time=df["timestamps"].iloc[start_idx].isoformat(),
        end_time=end_time.isoformat(),
        top=top,
        bottom=bottom,
        bias=direction,
    )


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
