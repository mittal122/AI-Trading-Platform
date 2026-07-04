import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, DetectedPattern, LabelAnnotation, LevelAnnotation, PatternDirection,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.candlestick_utils import (
    CandleMetrics, candle_metrics, gapped_down, gapped_up, higher_volume, local_trend,
    roughly_equal,
)
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, breakout_strength_score, clamp, make_pattern_id,
    nearest_swing_target, now_iso, risk_reward, status_from_breakout,
)
from backend.app.services.pattern.swing_detector import SwingDetector


class TwoCandlePatternDetector(BasePatternDetector):
    """
    Two-candle formations: Bullish/Bearish Kicker, Bullish/Bearish Engulfing,
    Bullish/Bearish Harami, Piercing Line, Dark Cloud Cover, Tweezer Bottom/Top.

    C1 is the "prior" candle, C2 the "signal" candle at the scan index. Every
    pattern here resolves via a real confirmation candle (C3, i.e. anything
    from idx+1 onward reflected in current_price) — same shared
    `status_from_breakout()` mechanism as the single-candle detector.
    """

    def __init__(self):
        self.indicators = IndicatorService()
        self.swings = SwingDetector()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        if n < cfg.CANDLESTICK_TREND_LOOKBACK_BARS + 3:
            return []

        window = df.iloc[max(0, n - cfg.CANDLESTICK_LOOKBACK_BARS):].reset_index(drop=True)
        wn = len(window)
        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        swings = self.swings.find_swings(window)
        current_price = float(window["close"].iloc[-1])

        checks = [
            self._kicker, self._engulfing, self._harami,
            self._piercing_dark_cloud, self._tweezer,
        ]

        patterns: list[DetectedPattern] = []
        start = max(1, cfg.CANDLESTICK_TREND_LOOKBACK_BARS)
        for idx in range(start, wn):
            c1 = candle_metrics(window, idx - 1)
            c2 = candle_metrics(window, idx)
            if c1.total_range <= 0 or c2.total_range <= 0:
                continue
            trend = local_trend(window, idx - 1)
            for check in checks:
                p = check(window, c1, c2, symbol, interval, atr, swings, current_price, trend)
                if p:
                    patterns.append(p)
                    break

        return patterns

    # ------------------------------------------------------------------
    # Kickers — no trend-context requirement (the gap+volume shock itself
    # is the signal, regardless of prior trend)
    # ------------------------------------------------------------------

    def _kicker(self, df, c1, c2, symbol, interval, atr, swings, current_price, trend):
        if c1.is_bearish and c2.is_bullish and gapped_up(c1, c2) and higher_volume(c2, c1):
            return self._build(
                df, c1, c2, symbol, interval, "bullish_kicker", "Bullish Kicker",
                PatternDirection.BULLISH, breakout_level=c1.high, stop_loss=c1.low,
                atr=atr, swings=swings, current_price=current_price,
                geometry_fit=75.0, rr_override=pattern_config.CANDLESTICK_DEFAULT_RR,
            )
        if c1.is_bullish and c2.is_bearish and gapped_down(c1, c2) and higher_volume(c2, c1):
            return self._build(
                df, c1, c2, symbol, interval, "bearish_kicker", "Bearish Kicker",
                PatternDirection.BEARISH, breakout_level=c2.low, stop_loss=c1.high,
                atr=atr, swings=swings, current_price=current_price,
                geometry_fit=75.0, no_fixed_target=True,
            )
        return None

    # ------------------------------------------------------------------
    # Engulfing
    # ------------------------------------------------------------------

    def _engulfing(self, df, c1, c2, symbol, interval, atr, swings, current_price, trend):
        # Body-overlap math alone doesn't force the right colors — e.g. two
        # same-colored small candles sitting inside a larger one can satisfy
        # the overlap inequalities without being an engulfing pattern at
        # all. C1/C2 color is part of the definition, not implied by it.
        if (trend == "DOWN" and c1.is_bearish and c2.is_bullish
                and higher_volume(c2, c1) and c2.close >= c1.open and c2.open <= c1.close):
            geometry_fit = clamp(c2.body / max(c1.body, 1e-9) * 50)
            return self._build(
                df, c1, c2, symbol, interval, "bullish_engulfing", "Bullish Engulfing",
                PatternDirection.BULLISH, breakout_level=c2.high, stop_loss=c2.low,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=geometry_fit,
            )
        if (trend == "UP" and c1.is_bullish and c2.is_bearish
                and higher_volume(c2, c1) and c2.open >= c1.close and c2.close <= c1.open):
            geometry_fit = clamp(c2.body / max(c1.body, 1e-9) * 50)
            return self._build(
                df, c1, c2, symbol, interval, "bearish_engulfing", "Bearish Engulfing",
                PatternDirection.BEARISH, breakout_level=c2.low, stop_loss=c2.high,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=geometry_fit,
            )
        return None

    # ------------------------------------------------------------------
    # Harami
    # ------------------------------------------------------------------

    def _harami(self, df, c1, c2, symbol, interval, atr, swings, current_price, trend):
        if trend == "DOWN" and c1.is_bearish and c2.body < c1.body and c2.open > c1.close and c2.close < c1.open:
            return self._build(
                df, c1, c2, symbol, interval, "bullish_harami", "Bullish Harami",
                PatternDirection.BULLISH, breakout_level=c1.high, stop_loss=c1.low,
                atr=atr, swings=swings, current_price=current_price,
                geometry_fit=70.0, rr_override=1.5,
            )
        if trend == "UP" and c1.is_bullish and c2.body < c1.body and c2.open < c1.close and c2.close > c1.open:
            pattern_low = min(c1.low, c2.low)
            stop_loss = max(c1.high, c2.high)
            return self._build(
                df, c1, c2, symbol, interval, "bearish_harami", "Bearish Harami",
                PatternDirection.BEARISH, breakout_level=pattern_low, stop_loss=stop_loss,
                atr=atr, swings=swings, current_price=current_price,
                geometry_fit=70.0, rr_override=1.5,
            )
        return None

    # ------------------------------------------------------------------
    # Piercing Line / Dark Cloud Cover
    # ------------------------------------------------------------------

    def _piercing_dark_cloud(self, df, c1, c2, symbol, interval, atr, swings, current_price, trend):
        cfg = pattern_config
        if trend == "DOWN" and c1.is_bearish and c2.is_bullish and gapped_down(c1, c2):
            midpoint = c1.open - (c1.open - c1.close) * cfg.CANDLESTICK_MIDPOINT_THRESHOLD
            if c2.close > midpoint:
                geometry_fit = clamp((c2.close - c1.close) / max(c1.body, 1e-9) * 50)
                return self._build(
                    df, c1, c2, symbol, interval, "piercing_line", "Piercing Line",
                    PatternDirection.BULLISH, breakout_level=c2.high, stop_loss=c2.low,
                    atr=atr, swings=swings, current_price=current_price, geometry_fit=geometry_fit,
                )
        if trend == "UP" and c1.is_bullish and c2.is_bearish and gapped_up(c1, c2):
            midpoint = c1.open + (c1.close - c1.open) * cfg.CANDLESTICK_MIDPOINT_THRESHOLD
            if c2.close < midpoint:
                geometry_fit = clamp((c1.close - c2.close) / max(c1.body, 1e-9) * 50)
                return self._build(
                    df, c1, c2, symbol, interval, "dark_cloud_cover", "Dark Cloud Cover",
                    PatternDirection.BEARISH, breakout_level=c2.low, stop_loss=c2.high,
                    atr=atr, swings=swings, current_price=current_price, geometry_fit=geometry_fit,
                )
        return None

    # ------------------------------------------------------------------
    # Tweezer Bottom / Top
    # ------------------------------------------------------------------

    def _tweezer(self, df, c1, c2, symbol, interval, atr, swings, current_price, trend):
        cfg = pattern_config
        if trend == "DOWN" and roughly_equal(c1.low, c2.low, cfg.CANDLESTICK_EQUAL_LEVEL_TOLERANCE_PCT):
            stop_loss = min(c1.low, c2.low)
            return self._build(
                df, c1, c2, symbol, interval, "tweezer_bottom", "Tweezer Bottom",
                PatternDirection.BULLISH, breakout_level=c2.high, stop_loss=stop_loss,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=65.0,
            )
        if trend == "UP" and roughly_equal(c1.high, c2.high, cfg.CANDLESTICK_EQUAL_LEVEL_TOLERANCE_PCT):
            stop_loss = max(c1.high, c2.high)
            return self._build(
                df, c1, c2, symbol, interval, "tweezer_top", "Tweezer Top",
                PatternDirection.BEARISH, breakout_level=c2.low, stop_loss=stop_loss,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=65.0,
            )
        return None

    # ------------------------------------------------------------------
    # Shared builder
    # ------------------------------------------------------------------

    def _build(
        self, df, c1: CandleMetrics, c2: CandleMetrics, symbol, interval, pattern_type, pattern_name,
        direction: PatternDirection, breakout_level: float, stop_loss: float, atr: float,
        swings, current_price: float, geometry_fit: float,
        rr_override: float | None = None, no_fixed_target: bool = False,
    ) -> DetectedPattern:
        status = status_from_breakout(direction, current_price, breakout_level, stop_loss, atr)

        target_1 = None
        rr = None
        if not no_fixed_target:
            if rr_override:
                risk = abs(breakout_level - stop_loss)
                sign = 1 if direction == PatternDirection.BULLISH else -1
                target_1 = breakout_level + sign * risk * rr_override
            else:
                target_1 = nearest_swing_target(swings, c2.idx, direction, current_price, atr)
            rr = risk_reward(breakout_level, stop_loss, target_1)

        confidence = algorithmic_confidence(
            geometry_fit=geometry_fit,
            volume_confirmation=50.0 + (10.0 if c2.volume > c1.volume else 0.0),
            breakout_strength=breakout_strength_score(current_price, breakout_level, atr),
            pattern_size=clamp((c1.total_range + c2.total_range) / (2 * atr) * 40),
        )

        annotations = ChartAnnotations(
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(stop_loss, 8)),
            ],
            labels=[
                LabelAnnotation(text=pattern_name, time=c2.timestamp, price=c2.high if c2.is_bullish else c2.low),
            ],
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, c1.timestamp),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=direction, confidence=round(confidence, 2), status=status,
            formation_start=c1.timestamp, formation_end=c2.timestamp,
            current_price=current_price,
            breakout_level=round(breakout_level, 8), invalidation_level=round(stop_loss, 8),
            entry_zone_low=round(breakout_level, 8), entry_zone_high=round(breakout_level, 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(target_1, 8) if target_1 is not None else None,
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )
