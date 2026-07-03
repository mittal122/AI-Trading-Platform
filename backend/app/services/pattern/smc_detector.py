import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    ChartAnnotations, DetectedPattern, LabelAnnotation, LevelAnnotation,
    PatternDirection, PatternStatus, ZoneAnnotation,
)
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.pattern_utils import (
    algorithmic_confidence, breakout_strength_score, make_pattern_id, now_iso,
    risk_reward, volume_confirmation_score,
)
from backend.app.services.pattern.swing_detector import SwingDetector, SwingPoint


class SMCDetector:
    """
    Smart Money Concepts: Break of Structure (BOS), Change of Character
    (CHOCH), Order Blocks, and Liquidity Zones (equal highs/lows). Built on
    the shared swing-point sequence — trend direction is inferred from
    whether swings are printing higher-highs/higher-lows or lower-highs/
    lower-lows; a break is classified BOS if it continues that trend, CHOCH
    if it contradicts it (the first sign of a potential reversal).
    """

    def __init__(self):
        self.swings = SwingDetector(lookback=pattern_config.BOS_SWING_LOOKBACK)
        self.indicators = IndicatorService()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        cfg = pattern_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.SMC_LOOKBACK_BARS):].reset_index(drop=True)

        if len(window) < cfg.BOS_SWING_LOOKBACK * 4:
            return []

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        swing_points = self.swings.find_swings(window)
        if len(swing_points) < 4:
            return []

        patterns = self._detect_structure_breaks(window, swing_points, symbol, interval, atr)
        patterns += self._detect_liquidity_zones(window, swing_points, symbol, interval)
        return patterns

    # ------------------------------------------------------------------
    # BOS / CHOCH + Order Blocks
    # ------------------------------------------------------------------

    def _detect_structure_breaks(self, df, swing_points, symbol, interval, atr) -> list[DetectedPattern]:
        highs = [s for s in swing_points if s.kind == "high"]
        lows = [s for s in swing_points if s.kind == "low"]
        if len(highs) < 2 or len(lows) < 2:
            return []

        trend = self._infer_trend(highs, lows)
        close = df["close"].to_numpy()
        n = len(df)
        results = []

        break_idx = self._find_break_index(close, highs[-1].index, highs[-1].price, n, above=True)
        if break_idx is not None:
            results.append(self._build_structure_event(
                df, symbol, interval, atr, break_idx, highs[-1],
                PatternDirection.BULLISH, is_choch=(trend == "DOWN"),
            ))

        break_idx = self._find_break_index(close, lows[-1].index, lows[-1].price, n, above=False)
        if break_idx is not None:
            results.append(self._build_structure_event(
                df, symbol, interval, atr, break_idx, lows[-1],
                PatternDirection.BEARISH, is_choch=(trend == "UP"),
            ))

        return results

    @staticmethod
    def _find_break_index(close, from_index, level, n, above: bool):
        for i in range(from_index + 1, n):
            if (above and close[i] > level) or (not above and close[i] < level):
                return i
        return None

    @staticmethod
    def _infer_trend(highs: list[SwingPoint], lows: list[SwingPoint]) -> str:
        higher_highs = highs[-1].price > highs[-2].price
        higher_lows = lows[-1].price > lows[-2].price
        if higher_highs and higher_lows:
            return "UP"
        if not higher_highs and not higher_lows:
            return "DOWN"
        return "SIDEWAYS"

    def _find_order_block(self, df, ref_index, break_index, is_bullish_break: bool):
        """Last opposite-colored candle before the break — the order block."""
        opens = df["open"].to_numpy()
        close = df["close"].to_numpy()
        for j in range(break_index - 1, ref_index - 1, -1):
            candle_bullish = close[j] >= opens[j]
            if is_bullish_break and not candle_bullish:
                return j
            if not is_bullish_break and candle_bullish:
                return j
        return None

    def _build_structure_event(
        self, df, symbol, interval, atr, break_index, ref_swing: SwingPoint,
        direction: PatternDirection, is_choch: bool,
    ) -> DetectedPattern:
        is_bull = direction == PatternDirection.BULLISH
        pattern_type = "choch" if is_choch else "bos"
        pattern_name = (
            f"Change of Character ({'Bullish' if is_bull else 'Bearish'})" if is_choch
            else f"Break of Structure ({'Bullish' if is_bull else 'Bearish'})"
        )

        ob_index = self._find_order_block(df, ref_swing.index, break_index, is_bull)
        formation_start = df["timestamps"].iloc[ref_swing.index].isoformat()
        formation_end = df["timestamps"].iloc[break_index].isoformat()
        current_price = float(df["close"].iloc[-1])
        break_level = ref_swing.price

        annotations = ChartAnnotations(
            levels=[LevelAnnotation(label="structure_level", price=round(break_level, 8))],
            labels=[LabelAnnotation(text=pattern_name, time=formation_end, price=break_level)],
        )

        entry_low = entry_high = stop_loss = None
        if ob_index is not None:
            ob_high = float(df["high"].iloc[ob_index])
            ob_low = float(df["low"].iloc[ob_index])
            entry_low, entry_high = ob_low, ob_high
            stop_loss = (ob_low - atr * 0.5) if is_bull else (ob_high + atr * 0.5)
            annotations.zones.append(ZoneAnnotation(
                label="order_block_bullish" if is_bull else "order_block_bearish",
                start_time=df["timestamps"].iloc[ob_index].isoformat(),
                end_time=formation_end, top=ob_high, bottom=ob_low, bias=direction,
            ))

        target_1 = target_2 = target_3 = rr = None
        if stop_loss is not None:
            sign = 1 if is_bull else -1
            target_1 = round(break_level + sign * atr * 2, 8)
            target_2 = round(break_level + sign * atr * 3.5, 8)
            target_3 = round(break_level + sign * atr * 5, 8)
            entry_ref = entry_high if is_bull else entry_low
            rr = risk_reward(entry_ref, stop_loss, target_1)

        confidence = algorithmic_confidence(
            geometry_fit=90.0 if ob_index is not None else 60.0,
            volume_confirmation=volume_confirmation_score(df, ref_swing.index, break_index),
            breakout_strength=breakout_strength_score(current_price, break_level, atr),
            pattern_size=70.0,
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, f"{pattern_type}_{'bull' if is_bull else 'bear'}", formation_start),
            pattern_type=pattern_type, pattern_name=pattern_name,
            symbol=symbol, interval=interval,
            direction=direction, confidence=confidence, status=PatternStatus.CONFIRMED,
            formation_start=formation_start, formation_end=formation_end,
            current_price=current_price,
            breakout_level=round(break_level, 8),
            invalidation_level=round(stop_loss, 8) if stop_loss is not None else None,
            entry_zone_low=round(entry_low, 8) if entry_low is not None else None,
            entry_zone_high=round(entry_high, 8) if entry_high is not None else None,
            stop_loss=round(stop_loss, 8) if stop_loss is not None else None,
            target_1=target_1, target_2=target_2, target_3=target_3,
            risk_reward=rr, probability_of_success=confidence,
            annotations=annotations, last_updated=now_iso(),
        )

    # ------------------------------------------------------------------
    # Liquidity zones — clusters of equal highs/lows
    # ------------------------------------------------------------------

    def _detect_liquidity_zones(self, df, swing_points, symbol, interval) -> list[DetectedPattern]:
        current_price = float(df["close"].iloc[-1])
        results = []

        for kind, direction, label in (
            ("high", PatternDirection.BEARISH, "Buy-Side Liquidity"),
            ("low", PatternDirection.BULLISH, "Sell-Side Liquidity"),
        ):
            points = [s for s in swing_points if s.kind == kind]
            for cluster in self._cluster_equal_levels(points):
                results.append(self._build_liquidity_zone(
                    df, symbol, interval, cluster, kind, direction, label, current_price,
                ))

        return results

    @staticmethod
    def _build_liquidity_zone(df, symbol, interval, cluster, kind, direction, label, current_price) -> DetectedPattern:
        level = sum(s.price for s in cluster) / len(cluster)
        formation_start = df["timestamps"].iloc[cluster[0].index].isoformat()
        formation_end = df["timestamps"].iloc[cluster[-1].index].isoformat()

        swept = (kind == "high" and current_price > level) or (kind == "low" and current_price < level)
        status = PatternStatus.BROKEN if swept else PatternStatus.DEVELOPING

        annotations = ChartAnnotations(
            levels=[LevelAnnotation(label="liquidity_level", price=round(level, 8))],
            labels=[LabelAnnotation(
                text=f"{label} ({len(cluster)}x equal {kind}s)", time=formation_end, price=level,
            )],
        )

        confidence = algorithmic_confidence(
            geometry_fit=min(100.0, len(cluster) * 30.0),
            volume_confirmation=50.0,
            breakout_strength=70.0 if swept else 30.0,
            pattern_size=50.0,
        )

        return DetectedPattern(
            id=make_pattern_id(symbol, interval, f"liquidity_{kind}", formation_start),
            pattern_type=f"liquidity_{kind}", pattern_name=label,
            symbol=symbol, interval=interval,
            direction=direction, confidence=confidence, status=status,
            formation_start=formation_start, formation_end=formation_end,
            current_price=current_price,
            breakout_level=round(level, 8),
            annotations=annotations, last_updated=now_iso(),
        )

    @staticmethod
    def _cluster_equal_levels(points: list[SwingPoint]) -> list[list[SwingPoint]]:
        cfg = pattern_config
        clusters: list[list[SwingPoint]] = []
        used = set()
        for i, p in enumerate(points):
            if i in used:
                continue
            cluster = [p]
            used.add(i)
            tolerance = p.price * cfg.LIQUIDITY_EQUAL_LEVEL_TOLERANCE_PCT / 100
            for j in range(i + 1, len(points)):
                if j not in used and abs(points[j].price - p.price) <= tolerance:
                    cluster.append(points[j])
                    used.add(j)
            if len(cluster) >= 2:
                clusters.append(cluster)
        return clusters
