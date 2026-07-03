import math

import pandas as pd

from backend.app.core.analysis_config import analysis_config
from backend.app.schemas.analysis_tool import AnalysisToolResult
from backend.app.schemas.pattern import ChartAnnotations, LevelAnnotation, PatternDirection
from backend.app.services.analysis.base_analysis_tool import BaseAnalysisTool
from backend.app.services.pattern.pattern_utils import now_iso
from backend.app.services.pattern.swing_detector import SwingDetector


class SupportResistanceTool(BaseAnalysisTool):
    """
    Swing highs/lows clustered into levels (tolerance-based — several nearby
    touches count as one level, not several), plus psychological round-number
    levels near the current price. Bias leans toward whichever side (nearest
    support vs. nearest resistance) price currently sits closer to.
    """

    key = "support_resistance"
    name = "Support & Resistance"

    def __init__(self):
        self.swings = SwingDetector()

    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        cfg = analysis_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.SR_LOOKBACK_BARS):].reset_index(drop=True)
        current_price = float(window["close"].iloc[-1])

        swings = self.swings.find_swings(window)
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]

        resistance_levels = self._cluster(highs, window, "resistance")
        support_levels = self._cluster(lows, window, "support")
        psychological = self._psychological_levels(current_price)

        all_levels = resistance_levels + support_levels
        nearest_resistance = min(
            (l for l in resistance_levels if l["price"] > current_price),
            key=lambda l: l["price"], default=None,
        )
        nearest_support = max(
            (l for l in support_levels if l["price"] < current_price),
            key=lambda l: l["price"], default=None,
        )

        bias = PatternDirection.NEUTRAL
        if nearest_support and nearest_resistance:
            dist_to_support = current_price - nearest_support["price"]
            dist_to_resistance = nearest_resistance["price"] - current_price
            bias = PatternDirection.BULLISH if dist_to_support < dist_to_resistance else PatternDirection.BEARISH

        annotations = ChartAnnotations(
            levels=[
                LevelAnnotation(label=f"resistance (touched {l['touches']}x)", price=l["price"])
                for l in resistance_levels
            ] + [
                LevelAnnotation(label=f"support (touched {l['touches']}x)", price=l["price"])
                for l in support_levels
            ] + [
                LevelAnnotation(label="psychological", price=p) for p in psychological
            ],
        )

        summary = (
            f"{len(support_levels)} support and {len(resistance_levels)} resistance level(s) detected. "
            + (f"Nearest support ${nearest_support['price']:.2f}, " if nearest_support else "")
            + (f"nearest resistance ${nearest_resistance['price']:.2f}." if nearest_resistance else "")
        )

        return AnalysisToolResult(
            tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
            bias=bias, summary=summary,
            data={
                "resistance_levels": resistance_levels,
                "support_levels": support_levels,
                "psychological_levels": psychological,
                "nearest_support": nearest_support,
                "nearest_resistance": nearest_resistance,
            },
            annotations=annotations, last_updated=now_iso(),
        )

    @staticmethod
    def _cluster(points, df, label: str) -> list[dict]:
        cfg = analysis_config
        clusters: list[list] = []
        used = set()
        for i, p in enumerate(points):
            if i in used:
                continue
            cluster = [p]
            used.add(i)
            tolerance = p.price * cfg.SR_LEVEL_TOLERANCE_PCT / 100
            for j in range(i + 1, len(points)):
                if j not in used and abs(points[j].price - p.price) <= tolerance:
                    cluster.append(points[j])
                    used.add(j)
            if len(cluster) >= cfg.SR_MIN_TOUCHES:
                clusters.append(cluster)

        results = []
        for cluster in clusters:
            avg_price = sum(s.price for s in cluster) / len(cluster)
            last_idx = max(s.index for s in cluster)
            results.append({
                "price": round(avg_price, 8),
                "touches": len(cluster),
                "type": label,
                "last_touched_at": df["timestamps"].iloc[last_idx].isoformat(),
            })
        results.sort(key=lambda l: l["price"])
        return results

    @staticmethod
    def _psychological_levels(price: float) -> list[float]:
        cfg = analysis_config
        if price <= 0:
            return []
        magnitude_exp = math.floor(math.log10(price)) - cfg.SR_PSYCHOLOGICAL_ROUND_DIGITS
        step = 10 ** max(magnitude_exp, 0)
        base = math.floor(price / step) * step
        levels = [base + step * i for i in range(-2, 3)]
        return [round(lv, 8) for lv in levels if lv > 0]
