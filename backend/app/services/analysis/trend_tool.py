import pandas as pd

from backend.app.core.analysis_config import analysis_config
from backend.app.schemas.analysis_tool import AnalysisToolResult
from backend.app.schemas.pattern import ChartAnnotations, ChartPoint, PatternDirection, TrendlineAnnotation
from backend.app.services.analysis.base_analysis_tool import BaseAnalysisTool
from backend.app.services.pattern.pattern_utils import now_iso
from backend.app.services.pattern.swing_detector import SwingDetector
from backend.app.services.pattern.trendline import classify_slope, fit_trendline, slope_pct_per_bar


class TrendlineTool(BaseAnalysisTool):
    """
    At-a-glance market trend: a least-squares trendline fit through closing
    prices (direction + how cleanly price tracks it, via R²), cross-checked
    against swing structure (higher-highs/higher-lows vs. lower-highs/
    lower-lows — the same structural read SMCDetector uses for BOS/CHOCH,
    surfaced here as a standalone tool rather than a full SMC breakdown).
    Also draws a channel through the swing highs/lows when there are enough
    swings to fit one.
    """

    key = "trend"
    name = "Trend Line"

    def __init__(self):
        self.swings = SwingDetector()

    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        cfg = analysis_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.TREND_LOOKBACK_BARS):].reset_index(drop=True)
        wn = len(window)
        current_price = float(window["close"].iloc[-1])

        overall_fit = fit_trendline(list(range(wn)), window["close"].tolist())
        slope_pct = slope_pct_per_bar(overall_fit, current_price)
        slope_label = classify_slope(slope_pct)

        swings = self.swings.find_swings(window)
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]

        structure_bias, structure_note = self._structure_trend(highs, lows)
        bias = structure_bias if structure_bias is not None else self._slope_bias(slope_label)

        trendlines = [
            TrendlineAnnotation(
                label="trend_line",
                points=[
                    ChartPoint(
                        time=window["timestamps"].iloc[0].isoformat(),
                        price=round(overall_fit.value_at(0), 8),
                    ),
                    ChartPoint(
                        time=window["timestamps"].iloc[wn - 1].isoformat(),
                        price=round(overall_fit.value_at(wn - 1), 8),
                    ),
                ],
            )
        ]

        channel_note = ""
        if len(highs) >= cfg.TREND_MIN_SWINGS_FOR_CHANNEL and len(lows) >= cfg.TREND_MIN_SWINGS_FOR_CHANNEL:
            resistance_fit = fit_trendline([s.index for s in highs], [s.price for s in highs])
            support_fit = fit_trendline([s.index for s in lows], [s.price for s in lows])
            trendlines.append(TrendlineAnnotation(
                label="trend_resistance",
                points=[
                    ChartPoint(
                        time=window["timestamps"].iloc[highs[0].index].isoformat(),
                        price=round(resistance_fit.value_at(highs[0].index), 8),
                    ),
                    ChartPoint(
                        time=window["timestamps"].iloc[wn - 1].isoformat(),
                        price=round(resistance_fit.value_at(wn - 1), 8),
                    ),
                ],
            ))
            trendlines.append(TrendlineAnnotation(
                label="trend_support",
                points=[
                    ChartPoint(
                        time=window["timestamps"].iloc[lows[0].index].isoformat(),
                        price=round(support_fit.value_at(lows[0].index), 8),
                    ),
                    ChartPoint(
                        time=window["timestamps"].iloc[wn - 1].isoformat(),
                        price=round(support_fit.value_at(wn - 1), 8),
                    ),
                ],
            ))
            channel_note = " Channel drawn from swing highs/lows."

        summary = (
            f"{slope_label.title()} trend — price moving {slope_pct:+.3f}%/bar, "
            f"trendline fit strength {overall_fit.r_squared * 100:.0f}%. {structure_note}{channel_note}"
        )

        return AnalysisToolResult(
            tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
            bias=bias, summary=summary.strip(),
            data={
                "slope_pct_per_bar": round(slope_pct, 4),
                "slope_direction": slope_label,
                "trend_strength_pct": round(overall_fit.r_squared * 100, 1),
                "structure": structure_note,
                "swing_highs_used": len(highs),
                "swing_lows_used": len(lows),
            },
            annotations=ChartAnnotations(trendlines=trendlines),
            last_updated=now_iso(),
        )

    @staticmethod
    def _structure_trend(highs, lows):
        if len(highs) < 2 or len(lows) < 2:
            return None, "Not enough swing points yet for a structural (HH/HL) read — showing slope-based trend only."
        higher_highs = highs[-1].price > highs[-2].price
        higher_lows = lows[-1].price > lows[-2].price
        lower_highs = highs[-1].price < highs[-2].price
        lower_lows = lows[-1].price < lows[-2].price
        if higher_highs and higher_lows:
            return PatternDirection.BULLISH, "Structure: higher highs + higher lows (uptrend)."
        if lower_highs and lower_lows:
            return PatternDirection.BEARISH, "Structure: lower highs + lower lows (downtrend)."
        return PatternDirection.NEUTRAL, "Structure: mixed swings (range/sideways)."

    @staticmethod
    def _slope_bias(slope_label: str) -> PatternDirection:
        if slope_label == "RISING":
            return PatternDirection.BULLISH
        if slope_label == "FALLING":
            return PatternDirection.BEARISH
        return PatternDirection.NEUTRAL
