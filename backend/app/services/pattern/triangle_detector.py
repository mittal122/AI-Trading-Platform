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

PATTERN_NAMES = {
    "ascending": "Ascending Triangle",
    "descending": "Descending Triangle",
    "symmetrical": "Symmetrical Triangle",
}


class TriangleDetector(BasePatternDetector):
    """
    Ascending/Descending/Symmetrical Triangle — a resistance trendline (fit
    through recent swing highs) and a support trendline (fit through recent
    swing lows) that are converging. Classified by slope:
      Ascending  = flat resistance + rising support  (typically resolves up)
      Descending = falling resistance + flat support (typically resolves down)
      Symmetrical = falling resistance + rising support (direction unbiased
      until the actual breakout — this detector watches the upper line as
      the primary breakout level, a simplification worth knowing about).
    """

    def __init__(self):
        self.swings = SwingDetector()
        self.indicators = IndicatorService()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.TRIANGLE_LOOKBACK_BARS):].reset_index(drop=True)
        if len(window) < 30:
            return []

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        swings = self.swings.find_swings(window)
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]

        min_touches = cfg.TRIANGLE_MIN_TOUCHES_PER_SIDE
        if len(highs) < min_touches or len(lows) < min_touches:
            return []

        recent_highs = highs[-4:] if len(highs) >= 4 else highs
        recent_lows = lows[-4:] if len(lows) >= 4 else lows

        resistance_fit = fit_trendline([s.index for s in recent_highs], [s.price for s in recent_highs])
        support_fit = fit_trendline([s.index for s in recent_lows], [s.price for s in recent_lows])

        current_price = float(window["close"].iloc[-1])
        res_slope_pct = slope_pct_per_bar(resistance_fit, current_price)
        sup_slope_pct = slope_pct_per_bar(support_fit, current_price)
        res_class = classify_slope(res_slope_pct)
        sup_class = classify_slope(sup_slope_pct)

        pattern_type = self._classify(res_class, sup_class)
        if pattern_type is None:
            return []

        start_idx = min(recent_highs[0].index, recent_lows[0].index)
        end_idx = len(window) - 1
        width_start = resistance_fit.value_at(start_idx) - support_fit.value_at(start_idx)
        width_now = resistance_fit.value_at(end_idx) - support_fit.value_at(end_idx)
        if width_start <= 0 or width_now < 0:
            return []
        convergence_pct = (1 - width_now / width_start) * 100
        if convergence_pct < cfg.TRIANGLE_MIN_CONVERGENCE_PCT:
            return []

        return [self._build(
            window, resistance_fit, support_fit, pattern_type, start_idx, end_idx,
            recent_highs, recent_lows, symbol, interval, atr,
        )]

    @staticmethod
    def _classify(res_class: str, sup_class: str) -> str:
        if res_class == "FLAT" and sup_class == "RISING":
            return "ascending"
        if res_class == "FALLING" and sup_class == "FLAT":
            return "descending"
        if res_class == "FALLING" and sup_class == "RISING":
            return "symmetrical"
        return None

    def _build(
        self, df, resistance_fit, support_fit, pattern_type, start_idx, end_idx,
        recent_highs, recent_lows, symbol, interval, atr,
    ) -> DetectedPattern:
        pattern_name = PATTERN_NAMES[pattern_type]
        direction = {
            "ascending": PatternDirection.BULLISH,
            "descending": PatternDirection.BEARISH,
            "symmetrical": PatternDirection.NEUTRAL,
        }[pattern_type]

        resistance_now = resistance_fit.value_at(end_idx)
        support_now = support_fit.value_at(end_idx)
        current_price = float(df["close"].iloc[-1])

        is_bullish_bias = direction != PatternDirection.BEARISH
        breakout_level = resistance_now if is_bullish_bias else support_now
        invalidation_level = support_now if is_bullish_bias else resistance_now
        eff_direction = PatternDirection.BULLISH if is_bullish_bias else PatternDirection.BEARISH

        measured_move = resistance_fit.value_at(start_idx) - support_fit.value_at(start_idx)
        t1, t2, t3 = measured_move_targets(eff_direction, breakout_level, measured_move)
        entry_low, entry_high = (
            (breakout_level, breakout_level + atr * 0.3) if is_bullish_bias
            else (breakout_level - atr * 0.3, breakout_level)
        )
        stop_loss = invalidation_level
        rr = risk_reward(breakout_level, stop_loss, t1)
        status = status_from_breakout(eff_direction, current_price, breakout_level, invalidation_level, atr)

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
            pattern_size=60.0,
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type + "_triangle", formation_start),
            pattern_type=pattern_type + "_triangle", pattern_name=pattern_name,
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
