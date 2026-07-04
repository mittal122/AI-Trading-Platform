import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, ChartPoint, DetectedPattern, LabelAnnotation,
    LevelAnnotation, PatternDirection, TrendlineAnnotation,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.candlestick_utils import (
    STATUS_STRENGTH_SCORE, resolve_forward_status,
)
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, clamp, make_pattern_id,
    measured_move_targets, now_iso, risk_reward,
    volume_confirmation_score,
)
from backend.app.services.pattern.swing_detector import SwingDetector, SwingPoint
from backend.app.services.pattern.trendline import fit_trendline


class HeadShouldersDetector(BasePatternDetector):
    """
    Head & Shoulders (bearish) and Inverse Head & Shoulders (bullish) — three
    consecutive swing extremes where the middle one ("head") is more extreme
    than the two roughly-equal outer ones ("shoulders"). The neckline
    connects the two troughs/peaks between them — it's a fitted line (2
    points), not necessarily horizontal, since the second trough often sits
    a bit higher/lower than the first in real data.
    """

    def __init__(self):
        self.swings = SwingDetector()
        self.indicators = IndicatorService()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.HS_LOOKBACK_BARS):].reset_index(drop=True)
        if len(window) < 30:
            return []

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        swings = self.swings.find_swings(window)
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]

        patterns = []
        patterns += self._scan(window, highs, is_bearish=True, symbol=symbol, interval=interval, atr=atr)
        patterns += self._scan(window, lows, is_bearish=False, symbol=symbol, interval=interval, atr=atr)
        return patterns

    def _scan(self, df, extremes: list[SwingPoint], is_bearish: bool, symbol, interval, atr) -> list[DetectedPattern]:
        cfg = pattern_config
        results = []
        for i in range(len(extremes) - 2):
            ls, head, rs = extremes[i], extremes[i + 1], extremes[i + 2]
            if not self._is_head(ls, head, rs, is_bearish):
                continue
            if not self._shoulders_match(ls, rs):
                continue
            results.append(self._build(df, ls, head, rs, is_bearish, symbol, interval, atr))
        return results

    @staticmethod
    def _is_head(ls: SwingPoint, head: SwingPoint, rs: SwingPoint, is_bearish: bool) -> bool:
        prom = pattern_config.HS_HEAD_MIN_PROMINENCE_PCT / 100
        if is_bearish:
            return head.price > ls.price * (1 + prom) and head.price > rs.price * (1 + prom)
        return head.price < ls.price * (1 - prom) and head.price < rs.price * (1 - prom)

    @staticmethod
    def _shoulders_match(ls: SwingPoint, rs: SwingPoint) -> bool:
        tol = pattern_config.HS_SHOULDER_TOLERANCE_PCT / 100
        return abs(ls.price - rs.price) / max(ls.price, rs.price) <= tol

    def _build(self, df, ls, head, rs, is_bearish: bool, symbol, interval, atr) -> DetectedPattern:
        pattern_type = "head_shoulders" if is_bearish else "inverse_head_shoulders"
        pattern_name = "Head & Shoulders" if is_bearish else "Inverse Head & Shoulders"
        direction = PatternDirection.BEARISH if is_bearish else PatternDirection.BULLISH
        extreme_col = "low" if is_bearish else "high"

        trough1_seg = df.iloc[ls.index: head.index + 1]
        trough2_seg = df.iloc[head.index: rs.index + 1]
        t1_idx = trough1_seg[extreme_col].idxmin() if is_bearish else trough1_seg[extreme_col].idxmax()
        t2_idx = trough2_seg[extreme_col].idxmin() if is_bearish else trough2_seg[extreme_col].idxmax()
        t1_price = float(df[extreme_col].iloc[t1_idx])
        t2_price = float(df[extreme_col].iloc[t2_idx])

        neckline_fit = fit_trendline([int(t1_idx), int(t2_idx)], [t1_price, t2_price])
        current_idx = len(df) - 1
        neckline_now = neckline_fit.value_at(current_idx)

        formation_start = df["timestamps"].iloc[ls.index].isoformat()
        formation_end = df["timestamps"].iloc[rs.index].isoformat()
        current_price = float(df["close"].iloc[-1])

        head_neckline_at_head = neckline_fit.value_at(head.index)
        measured_move = abs(head.price - head_neckline_at_head)
        invalidation_level = head.price * (1.01 if is_bearish else 0.99)

        t1, t2, t3 = measured_move_targets(direction, neckline_now, measured_move)
        entry_low, entry_high = (
            (neckline_now - atr * 0.3, neckline_now) if is_bearish
            else (neckline_now, neckline_now + atr * 0.3)
        )
        stop_loss = invalidation_level
        rr = risk_reward(neckline_now, stop_loss, t1)
        # Historical anchor (the right shoulder can sit anywhere in the
        # lookback) — resolve against the candles that FOLLOWED the pattern,
        # not today's price.
        status = resolve_forward_status(
            df, rs.index, direction, neckline_now, invalidation_level, atr,
            window_bars=pattern_config.CHART_PATTERN_CONFIRMATION_WINDOW_BARS,
        )

        annotations = ChartAnnotations(
            trendlines=[TrendlineAnnotation(label="neckline", points=[
                ChartPoint(time=df["timestamps"].iloc[t1_idx].isoformat(), price=t1_price),
                ChartPoint(time=df["timestamps"].iloc[t2_idx].isoformat(), price=t2_price),
            ])],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(neckline_now, 8)),
                LevelAnnotation(label="invalidation_level", price=round(invalidation_level, 8)),
            ],
            labels=[
                LabelAnnotation(text="Left Shoulder", time=df["timestamps"].iloc[ls.index].isoformat(), price=ls.price),
                LabelAnnotation(text="Head", time=df["timestamps"].iloc[head.index].isoformat(), price=head.price),
                LabelAnnotation(text="Right Shoulder", time=df["timestamps"].iloc[rs.index].isoformat(), price=rs.price),
                LabelAnnotation(text=pattern_name, time=formation_end, price=head.price),
            ],
        )

        shoulder_symmetry = clamp(100 - abs(ls.price - rs.price) / max(ls.price, rs.price) * 100 * 20)
        confidence = algorithmic_confidence(
            geometry_fit=shoulder_symmetry,
            volume_confirmation=volume_confirmation_score(df, ls.index, rs.index),
            breakout_strength=STATUS_STRENGTH_SCORE[status],
            pattern_size=60.0,
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, formation_start),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=direction, confidence=confidence, status=status,
            formation_start=formation_start, formation_end=formation_end,
            current_price=current_price,
            breakout_level=round(neckline_now, 8),
            invalidation_level=round(invalidation_level, 8),
            entry_zone_low=round(entry_low, 8), entry_zone_high=round(entry_high, 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(t1, 8), target_2=round(t2, 8), target_3=round(t3, 8),
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )
