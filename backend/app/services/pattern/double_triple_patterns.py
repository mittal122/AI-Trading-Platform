import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, DetectedPattern, LabelAnnotation, LevelAnnotation,
    PatternDirection, TrendlineAnnotation, ChartPoint,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.base_pattern_detector import BasePatternDetector
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, breakout_strength_score, clamp, make_pattern_id,
    measured_move_targets, now_iso, risk_reward, status_from_breakout,
    volume_confirmation_score,
)
from backend.app.services.pattern.swing_detector import SwingDetector, SwingPoint


class DoubleTriplePatternDetector(BasePatternDetector):
    """
    Double/Triple Top (bearish reversal, swing highs) and Double/Triple
    Bottom (bullish reversal, swing lows) — consecutive swing extremes at
    roughly the same level, separated by a trough/peak deep enough to count
    as a real retracement rather than noise. The neckline (trough/peak level
    between the extremes) is the breakout trigger; a close beyond the
    extremes' own level invalidates the pattern.
    """

    def __init__(self):
        self.swings = SwingDetector()
        self.indicators = IndicatorService()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.DT_LOOKBACK_BARS):].reset_index(drop=True)
        if len(window) < 30:
            return []

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        swings = self.swings.find_swings(window)
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]

        patterns = []
        patterns += self._scan(window, highs, "high", symbol, interval, atr)
        patterns += self._scan(window, lows, "low", symbol, interval, atr)
        return patterns

    def _scan(self, df, extremes: list[SwingPoint], kind: str, symbol, interval, atr) -> list[DetectedPattern]:
        cfg = pattern_config
        results = []
        i = 0
        while i < len(extremes) - 1:
            group = [extremes[i]]
            j = i + 1
            while j < len(extremes) and self._roughly_equal(extremes[i].price, extremes[j].price):
                between_ok = self._valid_retracement(df, group[-1], extremes[j], kind)
                if not between_ok:
                    break
                group.append(extremes[j])
                j += 1
                if len(group) == 3:
                    break

            if len(group) >= 2:
                results.append(self._build(df, group, kind, symbol, interval, atr))
                i = j
            else:
                i += 1

        return results

    @staticmethod
    def _roughly_equal(a: float, b: float) -> bool:
        tol = pattern_config.DT_PEAK_TOLERANCE_PCT / 100
        return abs(a - b) / max(a, b) <= tol

    @staticmethod
    def _valid_retracement(df, a: SwingPoint, b: SwingPoint, kind: str) -> bool:
        cfg = pattern_config
        segment = df.iloc[a.index: b.index + 1]
        if segment.empty:
            return False
        if kind == "high":
            extreme_between = float(segment["low"].min())
            depth_pct = (a.price - extreme_between) / a.price * 100
        else:
            extreme_between = float(segment["high"].max())
            depth_pct = (extreme_between - a.price) / a.price * 100
        return depth_pct >= cfg.DT_MIN_TROUGH_DEPTH_PCT

    def _build(self, df, group: list[SwingPoint], kind: str, symbol, interval, atr) -> DetectedPattern:
        is_top = kind == "high"
        count = len(group)
        pattern_type = ("triple_top" if count == 3 else "double_top") if is_top \
            else ("triple_bottom" if count == 3 else "double_bottom")
        pattern_name = ("Triple Top" if count == 3 else "Double Top") if is_top \
            else ("Triple Bottom" if count == 3 else "Double Bottom")
        direction = PatternDirection.BEARISH if is_top else PatternDirection.BULLISH

        segment = df.iloc[group[0].index: group[-1].index + 1]
        neckline = float(segment["low"].min()) if is_top else float(segment["high"].max())
        extreme_level = sum(s.price for s in group) / count

        formation_start = df["timestamps"].iloc[group[0].index].isoformat()
        formation_end = df["timestamps"].iloc[group[-1].index].isoformat()
        current_price = float(df["close"].iloc[-1])

        invalidation_level = extreme_level * (1.01 if is_top else 0.99)
        measured_move = abs(extreme_level - neckline)
        t1, t2, t3 = measured_move_targets(direction, neckline, measured_move)
        entry_low, entry_high = (neckline - atr * 0.3, neckline) if is_top else (neckline, neckline + atr * 0.3)
        stop_loss = invalidation_level
        rr = risk_reward(neckline, stop_loss, t1)

        status = status_from_breakout(direction, current_price, neckline, invalidation_level, atr)

        neckline_points = [
            ChartPoint(time=df["timestamps"].iloc[group[0].index].isoformat(), price=neckline),
            ChartPoint(time=df["timestamps"].iloc[group[-1].index].isoformat(), price=neckline),
        ]
        annotations = ChartAnnotations(
            trendlines=[TrendlineAnnotation(label="neckline", points=neckline_points)],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(neckline, 8)),
                LevelAnnotation(label="invalidation_level", price=round(invalidation_level, 8)),
            ],
            labels=[LabelAnnotation(text=pattern_name, time=formation_end, price=extreme_level)],
        )
        for s in group:
            annotations.labels.append(LabelAnnotation(
                text="Peak" if is_top else "Trough",
                time=df["timestamps"].iloc[s.index].isoformat(), price=s.price,
            ))

        geometry_fit = clamp(100 - abs(group[0].price - group[-1].price) / extreme_level * 100 * 20)
        confidence = algorithmic_confidence(
            geometry_fit=geometry_fit,
            volume_confirmation=volume_confirmation_score(df, group[0].index, group[-1].index),
            breakout_strength=breakout_strength_score(current_price, neckline, atr),
            pattern_size=clamp((count - 1) * 40 + 20),
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, formation_start),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=direction, confidence=confidence, status=status,
            formation_start=formation_start, formation_end=formation_end,
            current_price=current_price,
            breakout_level=round(neckline, 8),
            invalidation_level=round(invalidation_level, 8),
            entry_zone_low=round(entry_low, 8), entry_zone_high=round(entry_high, 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(t1, 8), target_2=round(t2, 8), target_3=round(t3, 8),
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )
