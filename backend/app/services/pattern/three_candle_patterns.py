import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, DetectedPattern, LabelAnnotation, LevelAnnotation, PatternDirection,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.candlestick_utils import (
    STATUS_STRENGTH_SCORE, CandleMetrics, candle_metrics, formation_zone, higher_volume,
    is_doji, local_trend, opens_within_body, resolve_forward_status,
)
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, clamp, make_pattern_id, nearest_swing_target, now_iso, risk_reward,
)
from backend.app.services.pattern.swing_detector import SwingDetector


class ThreeCandlePatternDetector(BasePatternDetector):
    """
    Three-(and four-)candle formations: Morning/Evening Star, Bullish/Bearish
    Abandoned Baby, Three White Soldiers/Black Crows, Bullish/Bearish Three
    Line Strike, Three Outside Up/Down, Three Inside Up/Down.

    Several of these (Star, Three Line Strike, Three Outside/Inside) are
    confirmed by their own last candle at formation time — no separate
    waiting period, per the source rules ("C3/C4 itself is the
    confirmation"). `status_from_breakout()` still handles this correctly:
    the breakout level is set at the exact price the pattern's own rule
    already requires price to have cleared, so status reads CONFIRMED
    immediately (and can still flip to BROKEN later if price reverses hard
    against it) rather than needing a special immediate-confirm code path.
    """

    def __init__(self):
        self.indicators = IndicatorService()
        self.swings = SwingDetector()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        if n < cfg.CANDLESTICK_TREND_LOOKBACK_BARS + 4:
            return []

        window = df.iloc[max(0, n - cfg.CANDLESTICK_LOOKBACK_BARS):].reset_index(drop=True)
        wn = len(window)
        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        swings = self.swings.find_swings(window)
        current_price = float(window["close"].iloc[-1])

        # Abandoned Baby is a strictly rarer, stricter variant of Star (Doji
        # middle candle + full gaps on both sides) — any genuine Abandoned
        # Baby ALSO satisfies Star's looser gap requirement. Must be checked
        # FIRST, or Star always matches first and Abandoned Baby can never
        # fire (same "specific before general" ordering rule as the
        # Doji-family-before-Hammer-family priority in the single-candle
        # detector).
        three_checks = [
            self._abandoned_baby, self._star, self._soldiers_crows,
            self._three_outside, self._three_inside,
        ]

        patterns: list[DetectedPattern] = []
        min_range = atr * cfg.CANDLESTICK_MIN_RANGE_ATR_RATIO
        start = max(2, cfg.CANDLESTICK_TREND_LOOKBACK_BARS)
        for idx in range(start, wn):
            c1 = candle_metrics(window, idx - 2)
            c2 = candle_metrics(window, idx - 1)
            c3 = candle_metrics(window, idx)
            if min(c1.total_range, c2.total_range, c3.total_range) <= 0:
                continue
            # Noise floor — the formation's largest candle must be real
            # relative to recent volatility (see the two-candle detector).
            if max(c1.total_range, c2.total_range, c3.total_range) < min_range:
                continue
            trend = local_trend(window, idx - 2)

            matched = False
            for check in three_checks:
                p = check(window, c1, c2, c3, symbol, interval, atr, swings, current_price, trend)
                if p:
                    patterns.append(p)
                    matched = True
                    break
            if matched:
                continue

            if idx >= 3:
                p = self._three_line_strike(
                    window, candle_metrics(window, idx - 3), c1, c2, c3,
                    symbol, interval, atr, swings, current_price, local_trend(window, idx - 3),
                )
                if p:
                    patterns.append(p)

        return patterns

    # ------------------------------------------------------------------
    # Morning Star / Evening Star
    # ------------------------------------------------------------------

    def _star(self, df, c1, c2, c3, symbol, interval, atr, swings, current_price, trend):
        cfg = pattern_config
        star_max = c1.body * cfg.CANDLESTICK_STAR_BODY_MAX_PCT / 100

        if (trend == "DOWN" and c1.is_bearish and c2.body <= star_max
                and max(c2.open, c2.close) < c1.close):
            # C3 must also gap UP from the star (C2) — a required detection
            # condition on its own, separate from "closes into C1's body"
            # (the confirmation). Missing this let a C3 that merely overlaps
            # C2's body still count as a Morning Star.
            if c3.is_bullish and min(c3.open, c3.close) > max(c2.open, c2.close) and c3.close > c1.midpoint:
                geometry_fit = clamp((c3.close - c1.midpoint) / max(c1.body, 1e-9) * 60)
                return self._build(
                    df, c1, c3, symbol, interval, "morning_star", "Morning Star",
                    PatternDirection.BULLISH, breakout_level=c1.midpoint, stop_loss=c2.low,
                    atr=atr, swings=swings, current_price=current_price, geometry_fit=geometry_fit,
                )

        if (trend == "UP" and c1.is_bullish and c2.body <= star_max
                and min(c2.open, c2.close) > c1.close):
            # C3 must gap DOWN from the star (mirror of the check above).
            if c3.is_bearish and max(c3.open, c3.close) < min(c2.open, c2.close) and c3.close < c1.midpoint:
                geometry_fit = clamp((c1.midpoint - c3.close) / max(c1.body, 1e-9) * 60)
                return self._build(
                    df, c1, c3, symbol, interval, "evening_star", "Evening Star",
                    PatternDirection.BEARISH, breakout_level=c1.midpoint, stop_loss=c2.high,
                    atr=atr, swings=swings, current_price=current_price, geometry_fit=geometry_fit,
                )
        return None

    # ------------------------------------------------------------------
    # Abandoned Baby — Star, but C2 is a Doji with NO wick overlap either side
    # ------------------------------------------------------------------

    def _abandoned_baby(self, df, c1, c2, c3, symbol, interval, atr, swings, current_price, trend):
        if not is_doji(c2):
            return None

        if trend == "DOWN" and c1.is_bearish and c2.high < c1.low and c3.low > c2.high:
            return self._build(
                df, c1, c3, symbol, interval, "bullish_abandoned_baby", "Bullish Abandoned Baby",
                PatternDirection.BULLISH, breakout_level=c3.high, stop_loss=c2.low,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=85.0,
            )
        if trend == "UP" and c1.is_bullish and c2.low > c1.high and c3.high < c2.low:
            return self._build(
                df, c1, c3, symbol, interval, "bearish_abandoned_baby", "Bearish Abandoned Baby",
                PatternDirection.BEARISH, breakout_level=c3.low, stop_loss=c2.high,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=85.0,
            )
        return None

    # ------------------------------------------------------------------
    # Three White Soldiers / Three Black Crows
    # ------------------------------------------------------------------

    def _soldiers_crows(self, df, c1, c2, c3, symbol, interval, atr, swings, current_price, trend):
        min_body = atr * pattern_config.CANDLESTICK_SOLDIER_CROW_MIN_ATR_MULT

        # Each candle should open within the prior candle's real body — a
        # genuine grinding advance/decline, not 3 candles that merely close
        # higher/lower while gapping wildly apart from each other (which
        # real technical-analysis definitions of "soldiers"/"crows"
        # explicitly exclude).
        opens_within_prior_body = opens_within_body(c1, c2) and opens_within_body(c2, c3)

        if (trend == "DOWN" and c1.is_bullish and c2.is_bullish and c3.is_bullish
                and opens_within_prior_body
                and min(c1.body, c2.body, c3.body) >= min_body and c3.close > c2.close > c1.close):
            return self._build(
                df, c1, c3, symbol, interval, "three_white_soldiers", "Three White Soldiers",
                PatternDirection.BULLISH, breakout_level=c3.high, stop_loss=c1.low,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=80.0,
                no_fixed_target=True,
            )
        if (trend == "UP" and c1.is_bearish and c2.is_bearish and c3.is_bearish
                and opens_within_prior_body
                and min(c1.body, c2.body, c3.body) >= min_body and c3.close < c2.close < c1.close):
            return self._build(
                df, c1, c3, symbol, interval, "three_black_crows", "Three Black Crows",
                PatternDirection.BEARISH, breakout_level=c3.low, stop_loss=c1.high,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=80.0,
                no_fixed_target=True,
            )
        return None

    # ------------------------------------------------------------------
    # Three Line Strike — Three Soldiers/Crows swallowed by one massive
    # opposite candle (C4). Confirmed immediately by its own C4.
    # ------------------------------------------------------------------

    def _three_line_strike(self, df, c1, c2, c3, c4, symbol, interval, atr, swings, current_price, trend):
        if (trend == "DOWN" and c1.is_bearish and c2.is_bearish and c3.is_bearish
                and c3.close < c2.close < c1.close and c4.is_bullish and c4.close > c1.open):
            return self._build(
                df, c1, c4, symbol, interval, "bullish_three_line_strike", "Bullish Three Line Strike",
                PatternDirection.BULLISH, breakout_level=c1.open, stop_loss=c4.low,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=85.0,
            )
        if (trend == "UP" and c1.is_bullish and c2.is_bullish and c3.is_bullish
                and c3.close > c2.close > c1.close and c4.is_bearish and c4.close < c1.open):
            return self._build(
                df, c1, c4, symbol, interval, "bearish_three_line_strike", "Bearish Three Line Strike",
                PatternDirection.BEARISH, breakout_level=c1.open, stop_loss=c4.high,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=85.0,
            )
        return None

    # ------------------------------------------------------------------
    # Three Outside Up / Down — Engulfing (C1,C2) confirmed by C3
    # ------------------------------------------------------------------

    def _three_outside(self, df, c1, c2, c3, symbol, interval, atr, swings, current_price, trend):
        # Same fix as the 2-candle Bullish/Bearish Engulfing: body-overlap
        # math alone doesn't force the right colors on C1/C2.
        if (trend == "DOWN" and c1.is_bearish and c2.is_bullish
                and c2.close >= c1.open and c2.open <= c1.close
                and c3.close > c2.close and higher_volume(c3, c1)):
            return self._build(
                df, c1, c3, symbol, interval, "three_outside_up", "Three Outside Up",
                PatternDirection.BULLISH, breakout_level=c2.close, stop_loss=c2.low,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=75.0, rr_override=1.5,
            )
        if (trend == "UP" and c1.is_bullish and c2.is_bearish
                and c2.open >= c1.close and c2.close <= c1.open and c3.close < c2.close):
            return self._build(
                df, c1, c3, symbol, interval, "three_outside_down", "Three Outside Down",
                PatternDirection.BEARISH, breakout_level=c2.close, stop_loss=c2.high,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=75.0, rr_override=1.5,
            )
        return None

    # ------------------------------------------------------------------
    # Three Inside Up / Down — Harami (C1,C2) confirmed by C3
    # ------------------------------------------------------------------

    def _three_inside(self, df, c1, c2, c3, symbol, interval, atr, swings, current_price, trend):
        if (trend == "DOWN" and c1.is_bearish and c2.body < c1.body
                and c2.open > c1.close and c2.close < c1.open and c3.close > c1.open):
            return self._build(
                df, c1, c3, symbol, interval, "three_inside_up", "Three Inside Up",
                PatternDirection.BULLISH, breakout_level=c1.open, stop_loss=c1.low,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=75.0, rr_override=1.5,
            )
        if (trend == "UP" and c1.is_bullish and c2.body < c1.body
                and c2.open < c1.close and c2.close > c1.open and c3.close < c1.open):
            return self._build(
                df, c1, c3, symbol, interval, "three_inside_down", "Three Inside Down",
                PatternDirection.BEARISH, breakout_level=c1.open, stop_loss=c1.high,
                atr=atr, swings=swings, current_price=current_price, geometry_fit=75.0, rr_override=1.5,
            )
        return None

    # ------------------------------------------------------------------
    # Shared builder
    # ------------------------------------------------------------------

    def _build(
        self, df, c_start: CandleMetrics, c_end: CandleMetrics, symbol, interval,
        pattern_type, pattern_name, direction: PatternDirection,
        breakout_level: float, stop_loss: float, atr: float,
        swings, current_price: float, geometry_fit: float,
        rr_override: float | None = None, no_fixed_target: bool = False,
    ) -> DetectedPattern:
        status = resolve_forward_status(df, c_end.idx, direction, breakout_level, stop_loss, atr)

        target_1 = None
        rr = None
        if not no_fixed_target:
            if rr_override:
                risk = abs(breakout_level - stop_loss)
                sign = 1 if direction == PatternDirection.BULLISH else -1
                target_1 = breakout_level + sign * risk * rr_override
            else:
                target_1 = nearest_swing_target(swings, c_end.idx, direction, current_price, atr)
            rr = risk_reward(breakout_level, stop_loss, target_1)

        confidence = algorithmic_confidence(
            geometry_fit=geometry_fit,
            volume_confirmation=50.0,
            breakout_strength=STATUS_STRENGTH_SCORE[status],
            pattern_size=clamp((c_start.total_range + c_end.total_range) / (2 * atr) * 40),
        )

        annotations = ChartAnnotations(
            zones=[formation_zone(df, c_start.idx, c_end.idx, pattern_name, direction)],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(stop_loss, 8)),
            ],
            labels=[
                LabelAnnotation(
                    text=pattern_name, time=c_end.timestamp,
                    price=c_end.high if c_end.is_bullish else c_end.low,
                ),
            ],
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, c_start.timestamp),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=direction, confidence=round(confidence, 2), status=status,
            formation_start=c_start.timestamp, formation_end=c_end.timestamp,
            current_price=current_price,
            breakout_level=round(breakout_level, 8), invalidation_level=round(stop_loss, 8),
            entry_zone_low=round(breakout_level, 8), entry_zone_high=round(breakout_level, 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(target_1, 8) if target_1 is not None else None,
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )
