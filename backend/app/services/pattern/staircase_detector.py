import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, ChartPoint, DetectedPattern, LabelAnnotation,
    LevelAnnotation, PatternDirection, TrendlineAnnotation,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, breakout_strength_score, clamp, make_pattern_id,
    now_iso, risk_reward, status_from_breakout, volume_confirmation_score,
)
from backend.app.services.pattern.swing_detector import SwingDetector


class StaircaseDetector(BasePatternDetector):
    """
    Ascending / Descending Staircase — the most basic trend-structure
    pattern: an ascending staircase makes higher highs AND higher lows
    step by step (a bull market's normal walk upward); the descending
    mirror makes lower highs and lower lows.

    Detection: the last STAIRCASE_MIN_SWINGS_PER_SIDE swing highs must be
    strictly increasing AND the same count of swing lows strictly
    increasing (ascending; mirrored for descending), with a net move of at
    least STAIRCASE_MIN_NET_MOVE_ATR ATRs so a flat wobble doesn't count.

    Live-edge pattern (the staircase is the CURRENT trend), so status uses
    current-price semantics: continuation triggers past the latest swing
    high (ascending), invalidated below the latest higher-low — a break of
    structure ends the staircase.

    Drawing: a zigzag polyline through the alternating swing points — the
    literal staircase from the reference material.
    """

    def __init__(self):
        self.indicators = IndicatorService()
        self.swings = SwingDetector()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.STAIRCASE_LOOKBACK_BARS):].reset_index(drop=True)
        if len(window) < 30:
            return []

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        k = cfg.STAIRCASE_MIN_SWINGS_PER_SIDE
        highs = self.swings.swing_highs(window)[-k:]
        lows = self.swings.swing_lows(window)[-k:]
        if len(highs) < k or len(lows) < k:
            return []

        ascending = (
            all(highs[i].price < highs[i + 1].price for i in range(len(highs) - 1))
            and all(lows[i].price < lows[i + 1].price for i in range(len(lows) - 1))
        )
        descending = (
            all(highs[i].price > highs[i + 1].price for i in range(len(highs) - 1))
            and all(lows[i].price > lows[i + 1].price for i in range(len(lows) - 1))
        )
        if not ascending and not descending:
            return []

        # Net move must be meaningful relative to volatility.
        steps = sorted(highs + lows, key=lambda s: s.index)
        net_move = abs(steps[-1].price - steps[0].price)
        if net_move < atr * cfg.STAIRCASE_MIN_NET_MOVE_ATR:
            return []

        return [self._build(window, steps, highs, lows, ascending, symbol, interval, atr)]

    def _build(self, df, steps, highs, lows, ascending: bool, symbol, interval, atr) -> DetectedPattern:
        direction = PatternDirection.BULLISH if ascending else PatternDirection.BEARISH
        pattern_type = "ascending_staircase" if ascending else "descending_staircase"
        pattern_name = "Ascending Staircase" if ascending else "Descending Staircase"
        current_price = float(df["close"].iloc[-1])

        if ascending:
            breakout_level = highs[-1].price      # continuation past the latest higher-high
            invalidation_level = lows[-1].price   # break of the latest higher-low ends the trend
        else:
            breakout_level = lows[-1].price
            invalidation_level = highs[-1].price

        # Target: one more "step" of the same average size beyond the trigger.
        avg_step = sum(
            abs(steps[i + 1].price - steps[i].price) for i in range(len(steps) - 1)
        ) / max(1, len(steps) - 1)
        sign = 1 if ascending else -1
        target_1 = breakout_level + sign * avg_step
        stop_loss = invalidation_level
        rr = risk_reward(breakout_level, stop_loss, target_1)
        status = status_from_breakout(direction, current_price, breakout_level, invalidation_level, atr)

        formation_start = df["timestamps"].iloc[steps[0].index].isoformat()
        formation_end = df["timestamps"].iloc[steps[-1].index].isoformat()

        zigzag = TrendlineAnnotation(
            label="staircase_up" if ascending else "staircase_down",
            points=[
                ChartPoint(time=df["timestamps"].iloc[s.index].isoformat(), price=s.price)
                for s in steps
            ],
        )
        annotations = ChartAnnotations(
            trendlines=[zigzag],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(invalidation_level, 8)),
            ],
            labels=[LabelAnnotation(text=pattern_name, time=formation_end, price=steps[-1].price)],
        )

        # Geometry: how uniform the steps are — a clean staircase has
        # consistently-sized steps, not one giant leap plus noise.
        step_sizes = [abs(steps[i + 1].price - steps[i].price) for i in range(len(steps) - 1)]
        mean_step = sum(step_sizes) / len(step_sizes)
        uniformity = 100 - clamp(
            (max(step_sizes) - min(step_sizes)) / mean_step * 50 if mean_step > 0 else 100
        )
        confidence = algorithmic_confidence(
            geometry_fit=clamp(uniformity),
            volume_confirmation=volume_confirmation_score(df, steps[0].index, steps[-1].index),
            breakout_strength=breakout_strength_score(current_price, breakout_level, atr),
            pattern_size=clamp(abs(steps[-1].price - steps[0].price) / atr * 10),
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
            entry_zone_low=round(min(breakout_level, current_price), 8),
            entry_zone_high=round(max(breakout_level, current_price), 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(target_1, 8),
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )
