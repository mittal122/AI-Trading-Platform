import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, DetectedPattern, LabelAnnotation, LevelAnnotation,
    PatternDirection, PatternStatus,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.candlestick_utils import (
    CandleMetrics, candle_metrics, is_doji, is_long_lower_wick, is_long_upper_wick,
    is_marubozu, local_trend, wick_at_least,
)
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, breakout_strength_score, clamp, make_pattern_id,
    nearest_swing_target, now_iso, risk_reward, status_from_breakout,
)
from backend.app.services.pattern.swing_detector import SwingDetector


class SingleCandlePatternDetector(BasePatternDetector):
    """
    Single-candle (and Inside Bar, which needs one prior "mother" candle)
    formations: Marubozu, Standard/Dragonfly/Gravestone Doji, Hammer,
    Hanging Man, Inverted Hammer, Shooting Star, Spinning Top, Inside Bar.

    Confirmable patterns (Marubozu, both directional Dojis, and the four
    hammer-family shapes) reuse `status_from_breakout()` — the pattern's own
    high/low is the breakout/confirmation trigger, its opposite side is the
    stop/invalidation level, so DEVELOPING -> CONFIRMED -> BROKEN falls out
    of the same shared logic every other pattern family uses.

    Standard Doji, Spinning Top, and Inside Bar are genuinely direction-
    neutral by definition — their own breakout determines which way they
    resolve, which hasn't happened yet at detection time. These are reported
    with direction=NEUTRAL, status always DEVELOPING, and no stop/target
    (both breakout directions are shown as chart levels instead) — that is
    the correct, honest representation of "undecided," not a missing feature.
    """

    def __init__(self):
        self.indicators = IndicatorService()
        self.swings = SwingDetector()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        if n < cfg.CANDLESTICK_TREND_LOOKBACK_BARS + 2:
            return []

        window = df.iloc[max(0, n - cfg.CANDLESTICK_LOOKBACK_BARS):].reset_index(drop=True)
        wn = len(window)
        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        swings = self.swings.find_swings(window)
        current_price = float(window["close"].iloc[-1])

        patterns: list[DetectedPattern] = []
        start = max(1, cfg.CANDLESTICK_TREND_LOOKBACK_BARS)
        for idx in range(start, wn):
            m = candle_metrics(window, idx)
            if m.total_range <= 0:
                continue
            trend = local_trend(window, idx)

            # A candle's own shape (Marubozu/Doji/Hammer-family/Spinning Top)
            # is mutually exclusive — one candle can't be two shapes at once,
            # so first match wins within this group.
            p = self._marubozu(window, m, symbol, interval, atr, swings, current_price)
            if p is None:
                p = self._doji_family(window, m, symbol, interval, atr, swings, current_price, trend)
            if p is None:
                p = self._hammer_family(window, m, symbol, interval, atr, swings, current_price, trend)
            if p is None:
                p = self._spinning_top(window, m, symbol, interval, atr)
            if p:
                patterns.append(p)

            # Inside Bar is a candle-PAIR relationship (containment vs. the
            # prior candle), completely independent of the current candle's
            # own shape — a candle can genuinely be both a Doji AND an Inside
            # Bar at once. Must NOT be shadowed by the shape checks above.
            p_inside = self._inside_bar(window, idx, m, symbol, interval, atr)
            if p_inside:
                patterns.append(p_inside)

        return patterns

    # ------------------------------------------------------------------
    # Marubozu
    # ------------------------------------------------------------------

    def _marubozu(self, df, m: CandleMetrics, symbol, interval, atr, swings, current_price):
        if not is_marubozu(m):
            return None
        direction = PatternDirection.BULLISH if m.is_bullish else PatternDirection.BEARISH
        breakout_level = m.high if direction == PatternDirection.BULLISH else m.low
        stop_loss = m.low if direction == PatternDirection.BULLISH else m.high
        wick_frac = (m.upper_wick + m.lower_wick) / m.total_range
        geometry_fit = clamp(100 - wick_frac * 100 / (pattern_config.CANDLESTICK_WICK_TOLERANCE_PCT / 100 * 2))
        return self._build(
            df, m, symbol, interval, "marubozu",
            "Bullish Marubozu" if direction == PatternDirection.BULLISH else "Bearish Marubozu",
            direction, breakout_level, stop_loss, atr, swings, current_price, geometry_fit,
        )

    # ------------------------------------------------------------------
    # Doji family (Standard / Dragonfly / Gravestone)
    # ------------------------------------------------------------------

    def _doji_family(self, df, m: CandleMetrics, symbol, interval, atr, swings, current_price, trend):
        if not is_doji(m):
            return None

        if trend == "DOWN" and is_long_lower_wick(m) and m.upper_wick <= m.total_range * 0.1:
            geometry_fit = clamp(m.lower_wick / m.total_range * 100)
            return self._build(
                df, m, symbol, interval, "dragonfly_doji", "Dragonfly Doji",
                PatternDirection.BULLISH, m.high, m.low, atr, swings, current_price, geometry_fit,
            )

        if trend == "UP" and is_long_upper_wick(m) and m.lower_wick <= m.total_range * 0.1:
            geometry_fit = clamp(m.upper_wick / m.total_range * 100)
            return self._build(
                df, m, symbol, interval, "gravestone_doji", "Gravestone Doji",
                PatternDirection.BEARISH, m.low, m.high, atr, swings, current_price, geometry_fit,
            )

        # Standard Doji — roughly balanced wicks, no directional bias yet.
        wick_diff = abs(m.upper_wick - m.lower_wick)
        if wick_diff <= m.total_range * 0.35:
            return self._build_neutral(
                m, symbol, interval, "standard_doji", "Standard Doji", m.low, m.high,
            )
        return None

    # ------------------------------------------------------------------
    # Hammer family (Hammer / Hanging Man / Inverted Hammer / Shooting Star)
    # ------------------------------------------------------------------

    def _hammer_family(self, df, m: CandleMetrics, symbol, interval, atr, swings, current_price, trend):
        opp_ratio = pattern_config.CANDLESTICK_OPPOSITE_WICK_MAX_RATIO
        lower_dominant = wick_at_least(m.lower_wick, m.body) and m.upper_wick <= m.lower_wick * opp_ratio
        upper_dominant = wick_at_least(m.upper_wick, m.body) and m.lower_wick <= m.upper_wick * opp_ratio

        if lower_dominant and trend == "DOWN":
            geometry_fit = clamp(m.lower_wick / max(m.body, m.total_range * 0.01) * 25)
            return self._build(
                df, m, symbol, interval, "hammer", "Hammer",
                PatternDirection.BULLISH, m.high, m.low, atr, swings, current_price, geometry_fit,
                rr_override=pattern_config.CANDLESTICK_DEFAULT_RR,
            )
        if lower_dominant and trend == "UP":
            geometry_fit = clamp(m.lower_wick / max(m.body, m.total_range * 0.01) * 25)
            return self._build(
                df, m, symbol, interval, "hanging_man", "Hanging Man",
                PatternDirection.BEARISH, m.low, m.high, atr, swings, current_price, geometry_fit,
            )
        if upper_dominant and trend == "DOWN":
            geometry_fit = clamp(m.upper_wick / max(m.body, m.total_range * 0.01) * 25)
            return self._build(
                df, m, symbol, interval, "inverted_hammer", "Inverted Hammer",
                PatternDirection.BULLISH, m.high, m.low, atr, swings, current_price, geometry_fit,
            )
        if upper_dominant and trend == "UP":
            geometry_fit = clamp(m.upper_wick / max(m.body, m.total_range * 0.01) * 25)
            return self._build(
                df, m, symbol, interval, "shooting_star", "Shooting Star",
                PatternDirection.BEARISH, m.low, m.high, atr, swings, current_price, geometry_fit,
            )
        return None

    # ------------------------------------------------------------------
    # Spinning Top — neutral, both wicks dominant over the body
    # ------------------------------------------------------------------

    def _spinning_top(self, df, m: CandleMetrics, symbol, interval, atr):
        if m.body > 0 and wick_at_least(m.upper_wick, m.body) and wick_at_least(m.lower_wick, m.body):
            return self._build_neutral(m, symbol, interval, "spinning_top", "Spinning Top", m.low, m.high)
        return None

    # ------------------------------------------------------------------
    # Inside Bar — needs the prior "mother" candle
    # ------------------------------------------------------------------

    def _inside_bar(self, df, idx, m: CandleMetrics, symbol, interval, atr):
        mother = candle_metrics(df, idx - 1)
        if mother.high > m.high and mother.low < m.low:
            # Pass the BABY (m, the current candle) — not the mother — so
            # formation_end/current_price/the chart label all land on the
            # candle where containment is actually confirmed, not one bar
            # too early. formation_start is overridden to the mother's
            # timestamp so the pattern's full span is still represented.
            return self._build_neutral(
                m, symbol, interval, "inside_bar", "Inside Bar", mother.low, mother.high,
                formation_start_override=mother.timestamp,
            )
        return None

    # ------------------------------------------------------------------
    # Shared builders
    # ------------------------------------------------------------------

    def _build(
        self, df, m: CandleMetrics, symbol, interval, pattern_type, pattern_name,
        direction: PatternDirection, breakout_level: float, stop_loss: float, atr: float,
        swings, current_price: float, geometry_fit: float,
        rr_override: float | None = None,
    ) -> DetectedPattern:
        status = status_from_breakout(direction, current_price, breakout_level, stop_loss, atr)
        if rr_override:
            risk = abs(breakout_level - stop_loss)
            sign = 1 if direction == PatternDirection.BULLISH else -1
            target_1 = breakout_level + sign * risk * rr_override
        else:
            target_1 = nearest_swing_target(swings, m.idx, direction, current_price, atr)
        rr = risk_reward(breakout_level, stop_loss, target_1)

        confidence = algorithmic_confidence(
            geometry_fit=geometry_fit,
            volume_confirmation=50.0,
            breakout_strength=breakout_strength_score(current_price, breakout_level, atr),
            pattern_size=clamp(m.total_range / atr * 40),
        )

        annotations = ChartAnnotations(
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(stop_loss, 8)),
            ],
            labels=[LabelAnnotation(text=pattern_name, time=m.timestamp, price=m.high if m.is_bullish else m.low)],
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, m.timestamp),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=direction, confidence=confidence, status=status,
            formation_start=m.timestamp, formation_end=m.timestamp,
            current_price=current_price,
            breakout_level=round(breakout_level, 8), invalidation_level=round(stop_loss, 8),
            entry_zone_low=round(breakout_level, 8), entry_zone_high=round(breakout_level, 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(target_1, 8), risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )

    def _build_neutral(
        self, m: CandleMetrics, symbol, interval, pattern_type, pattern_name,
        range_low: float, range_high: float, formation_start_override: str | None = None,
    ) -> DetectedPattern:
        annotations = ChartAnnotations(
            levels=[
                LevelAnnotation(label="range_high", price=round(range_high, 8)),
                LevelAnnotation(label="range_low", price=round(range_low, 8)),
            ],
            labels=[LabelAnnotation(text=pattern_name, time=m.timestamp, price=m.close)],
        )
        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, m.timestamp),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=PatternDirection.NEUTRAL, confidence=55.0, status=PatternStatus.DEVELOPING,
            formation_start=formation_start_override or m.timestamp, formation_end=m.timestamp,
            current_price=m.close,
            entry_zone_low=round(range_low, 8), entry_zone_high=round(range_high, 8),
            annotations=annotations, last_updated=now_iso(),
        )
