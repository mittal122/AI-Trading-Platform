import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, ChartPoint, DetectedPattern, LabelAnnotation,
    LevelAnnotation, PatternDirection, TrendlineAnnotation,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, breakout_strength_score, make_pattern_id,
    measured_move_targets, now_iso, risk_reward, status_from_breakout,
    volume_confirmation_score,
)
from backend.app.services.pattern.swing_detector import SwingDetector
from backend.app.services.pattern.trendline import classify_slope, fit_trendline, slope_pct_per_bar

# Diamonds and broadening formations are treated as bearish-biased reversal
# structures here (the classic "broadening top" / "diamond top" convention)
# — like the other NEUTRAL-natured patterns (symmetrical triangle,
# rectangle), the true direction is only certain once price actually breaks
# one side; this is a documented simplification, not a hard rule.


class DiamondBroadeningDetector(BasePatternDetector):
    """
    Broadening Formation — resistance rising AND support falling at the same
    time (the range expands instead of contracting, the opposite of a
    triangle). Diamond Pattern — a broadening formation in its first half
    that then contracts into a triangle in its second half, forming a
    rhombus shape.
    """

    def __init__(self):
        self.swings = SwingDetector()
        self.indicators = IndicatorService()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        patterns = []
        broadening = self._detect_broadening(df, symbol, interval, atr)
        if broadening:
            patterns.append(broadening)
        diamond = self._detect_diamond(df, symbol, interval, atr)
        if diamond:
            patterns.append(diamond)
        return patterns

    def _fit_sides(self, df: pd.DataFrame, min_touches: int):
        swings = self.swings.find_swings(df)
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]
        if len(highs) < min_touches or len(lows) < min_touches:
            return None
        recent_highs = highs[-4:] if len(highs) >= 4 else highs
        recent_lows = lows[-4:] if len(lows) >= 4 else lows
        resistance_fit = fit_trendline([s.index for s in recent_highs], [s.price for s in recent_highs])
        support_fit = fit_trendline([s.index for s in recent_lows], [s.price for s in recent_lows])
        return resistance_fit, support_fit, recent_highs, recent_lows

    def _detect_broadening(self, df, symbol, interval, atr):
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.BROADENING_LOOKBACK_BARS):].reset_index(drop=True)
        if len(window) < 30:
            return None

        fit = self._fit_sides(window, cfg.BROADENING_MIN_TOUCHES_PER_SIDE)
        if fit is None:
            return None
        resistance_fit, support_fit, recent_highs, recent_lows = fit

        current_price = float(window["close"].iloc[-1])
        res_class = classify_slope(slope_pct_per_bar(resistance_fit, current_price))
        sup_class = classify_slope(slope_pct_per_bar(support_fit, current_price))
        if not (res_class == "RISING" and sup_class == "FALLING"):
            return None

        start_idx = min(recent_highs[0].index, recent_lows[0].index)
        end_idx = len(window) - 1
        width_start = resistance_fit.value_at(start_idx) - support_fit.value_at(start_idx)
        width_now = resistance_fit.value_at(end_idx) - support_fit.value_at(end_idx)
        if width_start <= 0 or width_now <= width_start:
            return None
        expansion_pct = (width_now / width_start - 1) * 100
        if expansion_pct < cfg.TRIANGLE_MIN_CONVERGENCE_PCT:
            return None

        return self._build(
            window, resistance_fit, support_fit, "broadening_formation", "Broadening Formation",
            start_idx, end_idx, recent_highs, recent_lows, symbol, interval, atr,
        )

    def _detect_diamond(self, df, symbol, interval, atr):
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.DIAMOND_LOOKBACK_BARS):].reset_index(drop=True)
        if len(window) < 40:
            return None

        mid = len(window) // 2
        first_half = window.iloc[:mid].reset_index(drop=True)
        second_half = window.iloc[mid:].reset_index(drop=True)

        first_fit = self._fit_sides(first_half, 2)
        second_fit = self._fit_sides(second_half, 2)
        if first_fit is None or second_fit is None:
            return None

        f_res, f_sup, _, _ = first_fit
        s_res, s_sup, s_highs, s_lows = second_fit

        f_price = float(first_half["close"].iloc[-1])
        s_price = float(second_half["close"].iloc[-1])
        first_diverging = (
            classify_slope(slope_pct_per_bar(f_res, f_price)) == "RISING"
            and classify_slope(slope_pct_per_bar(f_sup, f_price)) == "FALLING"
        )
        second_converging = (
            classify_slope(slope_pct_per_bar(s_res, s_price)) == "FALLING"
            and classify_slope(slope_pct_per_bar(s_sup, s_price)) == "RISING"
        )
        if not (first_diverging and second_converging):
            return None

        start_idx = 0
        end_idx = len(window) - 1
        recent_highs = [s for s in [*self.swings.swing_highs(window)] if s.index >= mid][-4:] or s_highs
        recent_lows = [s for s in [*self.swings.swing_lows(window)] if s.index >= mid][-4:] or s_lows

        return self._build(
            window, s_res, s_sup, "diamond", "Diamond Pattern",
            start_idx, end_idx, recent_highs, recent_lows, symbol, interval, atr,
        )

    def _build(
        self, df, resistance_fit, support_fit, pattern_type, pattern_name,
        start_idx, end_idx, recent_highs, recent_lows, symbol, interval, atr,
    ) -> DetectedPattern:
        direction = PatternDirection.BEARISH  # documented simplification, see module docstring

        resistance_now = resistance_fit.value_at(end_idx)
        support_now = support_fit.value_at(end_idx)
        current_price = float(df["close"].iloc[-1])

        breakout_level = support_now
        invalidation_level = resistance_now

        measured_move = resistance_fit.value_at(start_idx) - support_fit.value_at(start_idx)
        t1, t2, t3 = measured_move_targets(direction, breakout_level, measured_move)
        entry_low, entry_high = breakout_level - atr * 0.3, breakout_level
        stop_loss = invalidation_level
        rr = risk_reward(breakout_level, stop_loss, t1)
        status = status_from_breakout(direction, current_price, breakout_level, invalidation_level, atr)

        formation_start = df["timestamps"].iloc[start_idx].isoformat()
        formation_end = df["timestamps"].iloc[end_idx].isoformat()

        annotations = ChartAnnotations(
            trendlines=[
                TrendlineAnnotation(label="resistance", points=[
                    ChartPoint(time=df["timestamps"].iloc[s.index].isoformat(), price=s.price) for s in recent_highs
                ]),
                TrendlineAnnotation(label="support", points=[
                    ChartPoint(time=df["timestamps"].iloc[s.index].isoformat(), price=s.price) for s in recent_lows
                ]),
            ],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(invalidation_level, 8)),
            ],
            labels=[LabelAnnotation(text=pattern_name, time=formation_end, price=resistance_now)],
        )

        confidence = algorithmic_confidence(
            geometry_fit=min(100.0, (resistance_fit.r_squared + support_fit.r_squared) / 2 * 100),
            volume_confirmation=volume_confirmation_score(df, start_idx, end_idx),
            breakout_strength=breakout_strength_score(current_price, breakout_level, atr),
            pattern_size=55.0,
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, formation_start),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=direction, confidence=confidence, status=status,
            formation_start=formation_start, formation_end=formation_end,
            current_price=current_price,
            breakout_level=round(breakout_level, 8),
            invalidation_level=round(invalidation_level, 8),
            entry_zone_low=round(entry_low, 8), entry_zone_high=round(entry_high, 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(t1, 8), target_2=round(t2, 8), target_3=round(t3, 8),
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )
