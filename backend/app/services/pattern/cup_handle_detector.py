import numpy as np
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
    measured_move_targets, now_iso, risk_reward, status_from_breakout,
    volume_confirmation_score,
)
from backend.app.services.pattern.swing_detector import SwingDetector

# Cup-scale patterns span many bars — a coarser pivot lookback than the
# default swing detector avoids treating small handle-phase wiggles as the
# cup's actual right rim.
CUP_SWING_LOOKBACK = 8


class CupHandleDetector(BasePatternDetector):
    """
    Cup & Handle / Rounding Bottom — a U-shaped recovery (the "cup") from a
    left rim down to a bottom and back up to a comparable right rim,
    confirmed by fitting a quadratic curve to the closes between the rims
    (a real U has a decent parabola fit with its vertex roughly centered,
    not a sharp V or an edge anomaly). If a shallow pullback follows the
    right rim it's a Handle (Cup & Handle); if price breaks out directly
    from the rim, it's a Rounding Bottom.

    Also detects the bearish mirror — Rounded Top: an inverted-U (dome)
    between two comparable rim LOWS, breaking DOWN through the rim level.
    """

    def __init__(self):
        self.indicators = IndicatorService()
        self.swings = SwingDetector(lookback=CUP_SWING_LOOKBACK)

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.CUP_MAX_BARS - cfg.HANDLE_MAX_BARS):].reset_index(drop=True)
        if len(window) < cfg.CUP_MIN_BARS:
            return []

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        results = []
        cup = self._find_cup(window)
        if cup is not None:
            results.append(self._build(window, cup, symbol, interval, atr))
        dome = self._find_dome(window)
        if dome is not None:
            results.append(self._build_rounded_top(window, dome, symbol, interval, atr))
        return results

    def _find_dome(self, df: pd.DataFrame):
        """Mirror of _find_cup: an inverted-U between two comparable rim
        LOWS with the peak in between — the Rounded Top of the reference
        material (a series of higher highs rolling over into lower highs)."""
        cfg = pattern_config
        close = df["close"].to_numpy()
        top_idx = int(np.argmax(close))
        n = len(df)

        left_search = close[: top_idx + 1]
        if len(left_search) < 3:
            return None
        left_rim_idx = int(np.argmin(left_search))
        left_rim_price = float(close[left_rim_idx])

        tolerance = left_rim_price * cfg.CUP_RIM_TOLERANCE_PCT / 100
        right_search_limit = min(n, top_idx + cfg.CUP_MAX_BARS)
        swing_lows_after = sorted(
            (s for s in self.swings.swing_lows(df) if top_idx < s.index < right_search_limit),
            key=lambda s: s.index,
        )
        right_rim_idx = None
        for s in swing_lows_after:
            if s.price <= left_rim_price + tolerance:
                right_rim_idx = s.index
                break
        if right_rim_idx is None:
            return None

        span = right_rim_idx - left_rim_idx
        if not (cfg.CUP_MIN_BARS <= span <= cfg.CUP_MAX_BARS):
            return None
        if left_rim_idx >= top_idx or right_rim_idx <= top_idx:
            return None

        left_rim = float(close[left_rim_idx])
        right_rim = float(close[right_rim_idx])
        top = float(close[top_idx])
        rim_avg = (left_rim + right_rim) / 2

        rim_diff_pct = abs(left_rim - right_rim) / rim_avg * 100
        if rim_diff_pct > cfg.CUP_RIM_TOLERANCE_PCT:
            return None

        height_pct = (top - rim_avg) / rim_avg * 100
        if not (cfg.CUP_DEPTH_MIN_PCT <= height_pct <= cfg.CUP_DEPTH_MAX_PCT):
            return None

        x = np.arange(left_rim_idx, right_rim_idx + 1)
        y = close[left_rim_idx: right_rim_idx + 1]
        coeffs = np.polyfit(x, y, 2)
        if coeffs[0] >= 0:  # must open DOWNWARD (a dome, not a U)
            return None
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        if r_squared < 0.5:
            return None

        vertex_x = -coeffs[1] / (2 * coeffs[0])
        vertex_position = (vertex_x - left_rim_idx) / span if span > 0 else 0.5
        if not (0.25 <= vertex_position <= 0.75):
            return None

        return {
            "left_rim_idx": left_rim_idx, "right_rim_idx": right_rim_idx, "top_idx": top_idx,
            "left_rim": left_rim, "right_rim": right_rim, "top": top,
            "rim_avg": rim_avg, "height_pct": height_pct, "r_squared": r_squared,
        }

    def _build_rounded_top(self, df, dome: dict, symbol, interval, atr) -> DetectedPattern:
        breakout_level = dome["right_rim"]           # break DOWN through the rim-low level
        invalidation_level = dome["top"]
        end_idx = dome["right_rim_idx"]
        current_price = float(df["close"].iloc[-1])

        measured_move = dome["top"] - dome["rim_avg"]
        t1, t2, t3 = measured_move_targets(PatternDirection.BEARISH, breakout_level, measured_move)
        stop_loss = invalidation_level
        rr = risk_reward(breakout_level, stop_loss, t1)
        status = status_from_breakout(PatternDirection.BEARISH, current_price, breakout_level, invalidation_level, atr)

        formation_start = df["timestamps"].iloc[dome["left_rim_idx"]].isoformat()
        formation_end = df["timestamps"].iloc[end_idx].isoformat()

        step = max(1, (dome["right_rim_idx"] - dome["left_rim_idx"]) // 8)
        curve_points = [
            ChartPoint(time=df["timestamps"].iloc[i].isoformat(), price=float(df["close"].iloc[i]))
            for i in range(dome["left_rim_idx"], dome["right_rim_idx"] + 1, step)
        ]
        annotations = ChartAnnotations(
            trendlines=[TrendlineAnnotation(label="cup_curve", points=curve_points)],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(invalidation_level, 8)),
            ],
            labels=[
                LabelAnnotation(text="Rounded Top", time=formation_end, price=breakout_level),
            ],
        )

        confidence = algorithmic_confidence(
            geometry_fit=clamp(dome["r_squared"] * 100),
            volume_confirmation=volume_confirmation_score(df, dome["left_rim_idx"], end_idx),
            breakout_strength=breakout_strength_score(current_price, breakout_level, atr),
            pattern_size=55.0,
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, "rounded_top", formation_start),
            pattern_type="rounded_top", pattern_name="Rounded Top",
            symbol=symbol, interval=interval,
            direction=PatternDirection.BEARISH, confidence=confidence, status=status,
            formation_start=formation_start, formation_end=formation_end,
            current_price=current_price,
            breakout_level=round(breakout_level, 8),
            invalidation_level=round(invalidation_level, 8),
            entry_zone_low=round(breakout_level - atr * 0.3, 8), entry_zone_high=round(breakout_level, 8),
            stop_loss=round(stop_loss, 8),
            target_1=round(t1, 8), target_2=round(t2, 8), target_3=round(t3, 8),
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )

    def _find_cup(self, df: pd.DataFrame):
        cfg = pattern_config
        close = df["close"].to_numpy()
        bottom_idx = int(np.argmin(close))
        n = len(df)

        left_search = close[: bottom_idx + 1]
        if len(left_search) < 3:
            return None
        left_rim_idx = int(np.argmax(left_search))
        left_rim_price = float(close[left_rim_idx])

        # The right rim must be an actual local peak (a swing high) near the
        # left rim's level — not just the first bar that happens to cross a
        # threshold, and not the highest point in some generous window
        # (which can land inside a later handle swing instead of the cup's
        # own completion point).
        tolerance = left_rim_price * cfg.CUP_RIM_TOLERANCE_PCT / 100
        right_search_limit = min(n, bottom_idx + cfg.CUP_MAX_BARS)
        swing_highs_after = sorted(
            (s for s in self.swings.swing_highs(df) if bottom_idx < s.index < right_search_limit),
            key=lambda s: s.index,
        )
        right_rim_idx = None
        for s in swing_highs_after:
            if s.price >= left_rim_price - tolerance:
                right_rim_idx = s.index
                break
        if right_rim_idx is None:
            return None

        span = right_rim_idx - left_rim_idx
        if not (cfg.CUP_MIN_BARS <= span <= cfg.CUP_MAX_BARS):
            return None
        if left_rim_idx >= bottom_idx or right_rim_idx <= bottom_idx:
            return None

        left_rim = float(close[left_rim_idx])
        right_rim = float(close[right_rim_idx])
        bottom = float(close[bottom_idx])
        rim_avg = (left_rim + right_rim) / 2

        rim_diff_pct = abs(left_rim - right_rim) / rim_avg * 100
        if rim_diff_pct > cfg.CUP_RIM_TOLERANCE_PCT:
            return None

        depth_pct = (rim_avg - bottom) / rim_avg * 100
        if not (cfg.CUP_DEPTH_MIN_PCT <= depth_pct <= cfg.CUP_DEPTH_MAX_PCT):
            return None

        x = np.arange(left_rim_idx, right_rim_idx + 1)
        y = close[left_rim_idx: right_rim_idx + 1]
        coeffs = np.polyfit(x, y, 2)
        if coeffs[0] <= 0:  # must open upward (a U, not an inverted U)
            return None
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        if r_squared < 0.5:
            return None

        vertex_x = -coeffs[1] / (2 * coeffs[0])
        vertex_position = (vertex_x - left_rim_idx) / span if span > 0 else 0.5
        if not (0.25 <= vertex_position <= 0.75):
            return None

        return {
            "left_rim_idx": left_rim_idx, "right_rim_idx": right_rim_idx, "bottom_idx": bottom_idx,
            "left_rim": left_rim, "right_rim": right_rim, "bottom": bottom,
            "rim_avg": rim_avg, "depth_pct": depth_pct, "r_squared": r_squared,
        }

    def _find_handle(self, df: pd.DataFrame, cup: dict):
        cfg = pattern_config
        n = len(df)
        start = cup["right_rim_idx"] + 1  # handle starts AFTER the rim bar, not on it
        end = min(n - 1, start + cfg.HANDLE_MAX_BARS)
        if end - start < 3:
            return None

        segment = df.iloc[start:end + 1]
        handle_low_idx = int(segment["low"].idxmin())
        handle_low = float(df["low"].iloc[handle_low_idx])
        cup_depth = cup["rim_avg"] - cup["bottom"]
        if cup_depth <= 0:
            return None

        retrace_pct = (cup["right_rim"] - handle_low) / cup_depth * 100
        if retrace_pct <= 0 or retrace_pct > cfg.HANDLE_MAX_RETRACE_PCT:
            return None

        return {"low_idx": handle_low_idx, "low": handle_low, "end_idx": end}

    def _build(self, df, cup: dict, symbol, interval, atr) -> DetectedPattern:
        handle = self._find_handle(df, cup)
        has_handle = handle is not None
        pattern_type = "cup_and_handle" if has_handle else "rounding_bottom"
        pattern_name = "Cup and Handle" if has_handle else "Rounding Bottom"

        breakout_level = cup["right_rim"]
        invalidation_level = handle["low"] if has_handle else cup["bottom"]
        end_idx = handle["end_idx"] if has_handle else cup["right_rim_idx"]
        current_price = float(df["close"].iloc[-1])

        measured_move = cup["rim_avg"] - cup["bottom"]
        t1, t2, t3 = measured_move_targets(PatternDirection.BULLISH, breakout_level, measured_move)
        entry_low, entry_high = breakout_level, breakout_level + atr * 0.3
        stop_loss = invalidation_level
        rr = risk_reward(breakout_level, stop_loss, t1)
        status = status_from_breakout(PatternDirection.BULLISH, current_price, breakout_level, invalidation_level, atr)

        formation_start = df["timestamps"].iloc[cup["left_rim_idx"]].isoformat()
        formation_end = df["timestamps"].iloc[end_idx].isoformat()

        curve_points = [
            ChartPoint(time=df["timestamps"].iloc[i].isoformat(), price=float(df["close"].iloc[i]))
            for i in range(cup["left_rim_idx"], cup["right_rim_idx"] + 1, max(1, (cup["right_rim_idx"] - cup["left_rim_idx"]) // 8))
        ]
        annotations = ChartAnnotations(
            trendlines=[TrendlineAnnotation(label="cup_curve", points=curve_points)],
            levels=[
                LevelAnnotation(label="breakout_level", price=round(breakout_level, 8)),
                LevelAnnotation(label="invalidation_level", price=round(invalidation_level, 8)),
            ],
            labels=[
                LabelAnnotation(text="Cup Bottom", time=df["timestamps"].iloc[cup["bottom_idx"]].isoformat(), price=cup["bottom"]),
                LabelAnnotation(text=pattern_name, time=formation_end, price=breakout_level),
            ],
        )
        if has_handle:
            annotations.labels.append(LabelAnnotation(
                text="Handle", time=df["timestamps"].iloc[handle["low_idx"]].isoformat(), price=handle["low"],
            ))

        confidence = algorithmic_confidence(
            geometry_fit=clamp(cup["r_squared"] * 100),
            volume_confirmation=volume_confirmation_score(df, cup["left_rim_idx"], end_idx),
            breakout_strength=breakout_strength_score(current_price, breakout_level, atr),
            pattern_size=clamp(70.0 if has_handle else 55.0),
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, pattern_type, formation_start),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=PatternDirection.BULLISH, confidence=confidence, status=status,
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
