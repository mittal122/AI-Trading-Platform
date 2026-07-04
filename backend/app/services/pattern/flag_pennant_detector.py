import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, ChartPoint, DetectedPattern, LabelAnnotation,
    LevelAnnotation, PatternDirection, TrendlineAnnotation, ZoneAnnotation,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, breakout_strength_score, make_pattern_id,
    measured_move_targets, now_iso, risk_reward, status_from_breakout,
    volume_confirmation_score,
)


class FlagPennantDetector(BasePatternDetector):
    """
    Bull Flag / Bear Flag / Pennant — a sharp impulsive move (the
    "flagpole") followed by a brief, shallow consolidation before an
    expected continuation. Distinguished from the flagpole's move (via
    `close` price change) and from each other by whether the consolidation
    range stays roughly constant width (flag, a parallel channel) or
    narrows (pennant, a small converging triangle).
    """

    def __init__(self):
        self.indicators = IndicatorService()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        total_needed = cfg.FLAGPOLE_LOOKBACK_BARS + cfg.FLAG_MAX_CONSOLIDATION_BARS
        if n < total_needed + 5:
            return []

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        window = df.iloc[max(0, n - total_needed):].reset_index(drop=True)
        wn = len(window)

        for consolidation_len in range(cfg.FLAG_MIN_CONSOLIDATION_BARS, cfg.FLAG_MAX_CONSOLIDATION_BARS + 1):
            split = wn - consolidation_len
            pole_start = max(0, split - cfg.FLAGPOLE_LOOKBACK_BARS)
            if pole_start >= split:
                continue

            pole = window.iloc[pole_start:split]
            consolidation = window.iloc[split:]
            if len(pole) < 5 or len(consolidation) < cfg.FLAG_MIN_CONSOLIDATION_BARS:
                continue

            pole_open = float(pole["close"].iloc[0])
            pole_close = float(pole["close"].iloc[-1])
            if pole_open <= 0:
                continue
            pole_move_pct = (pole_close - pole_open) / pole_open * 100

            if abs(pole_move_pct) < cfg.FLAGPOLE_MIN_MOVE_PCT:
                continue

            is_bullish_pole = pole_move_pct > 0
            cons_high = float(consolidation["high"].max())
            cons_low = float(consolidation["low"].min())
            pole_range = abs(pole_close - pole_open)
            retrace_pct = (cons_high - cons_low) / pole_range * 100 if pole_range > 0 else 999

            if retrace_pct > cfg.FLAG_MAX_RETRACE_PCT:
                continue

            return [self._build(
                window, pole, consolidation, pole_start, split, wn - 1,
                is_bullish_pole, pole_range, symbol, interval, atr,
            )]

        return []

    @staticmethod
    def _is_pennant(consolidation: pd.DataFrame) -> bool:
        half = max(2, len(consolidation) // 2)
        first_half = consolidation.iloc[:half]
        second_half = consolidation.iloc[half:]
        width_start = float(first_half["high"].max() - first_half["low"].min())
        width_end = float(second_half["high"].max() - second_half["low"].min())
        return width_start > 0 and (width_end / width_start) < 0.7

    def _build(
        self, df, pole, consolidation, pole_start_idx, split_idx, end_idx,
        is_bullish_pole: bool, pole_range: float, symbol, interval, atr,
    ) -> DetectedPattern:
        is_pennant = self._is_pennant(consolidation)
        if is_pennant:
            pattern_type, pattern_name = "pennant", "Pennant"
        elif is_bullish_pole:
            pattern_type, pattern_name = "bull_flag", "Bull Flag"
        else:
            pattern_type, pattern_name = "bear_flag", "Bear Flag"

        direction = PatternDirection.BULLISH if is_bullish_pole else PatternDirection.BEARISH
        cons_high = float(consolidation["high"].max())
        cons_low = float(consolidation["low"].min())
        current_price = float(df["close"].iloc[-1])

        breakout_level = cons_high if is_bullish_pole else cons_low
        invalidation_level = cons_low if is_bullish_pole else cons_high

        t1, t2, t3 = measured_move_targets(direction, breakout_level, pole_range)
        entry_low, entry_high = (
            (breakout_level, breakout_level + atr * 0.3) if is_bullish_pole
            else (breakout_level - atr * 0.3, breakout_level)
        )
        stop_loss = invalidation_level
        rr = risk_reward(breakout_level, stop_loss, t1)
        status = status_from_breakout(direction, current_price, breakout_level, invalidation_level, atr)

        formation_start = df["timestamps"].iloc[pole_start_idx].isoformat()
        formation_end = df["timestamps"].iloc[end_idx].isoformat()

        annotations = ChartAnnotations(
            trendlines=[
                TrendlineAnnotation(label="flagpole", points=[
                    ChartPoint(time=df["timestamps"].iloc[pole_start_idx].isoformat(), price=float(pole["close"].iloc[0])),
                    ChartPoint(time=df["timestamps"].iloc[split_idx].isoformat(), price=float(pole["close"].iloc[-1])),
                ]),
            ],
            zones=[ZoneAnnotation(
                label="consolidation", start_time=df["timestamps"].iloc[split_idx].isoformat(),
                end_time=formation_end, top=cons_high, bottom=cons_low, bias=direction,
            )],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(invalidation_level, 8)),
            ],
            labels=[LabelAnnotation(text=pattern_name, time=formation_end, price=cons_high)],
        )

        confidence = algorithmic_confidence(
            geometry_fit=70.0 if is_pennant else 60.0,
            volume_confirmation=volume_confirmation_score(df, pole_start_idx, split_idx),
            breakout_strength=breakout_strength_score(current_price, breakout_level, atr),
            pattern_size=60.0,
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
