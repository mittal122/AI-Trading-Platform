import numpy as np
import pandas as pd

from backend.app.core.analysis_config import analysis_config
from backend.app.schemas.analysis_tool import AnalysisToolResult
from backend.app.schemas.pattern import (
    ChartAnnotations, ChartPoint, LevelAnnotation, PatternDirection, TrendlineAnnotation,
)
from backend.app.services.analysis.base_analysis_tool import BaseAnalysisTool
from backend.app.services.pattern.pattern_utils import now_iso
from backend.app.services.pattern.swing_detector import SwingDetector


class VWAPTool(BaseAnalysisTool):
    """
    Daily VWAP (anchored to the start of the current UTC day) + an
    automatically anchored VWAP (anchored to the most recent significant
    swing point — no manual anchor drawing), both with volume-weighted
    standard-deviation bands. Bias: price above/below the daily VWAP, the
    standard institutional "fair value" reference for the session.
    """

    key = "vwap"
    name = "VWAP"

    def __init__(self):
        self.swings = SwingDetector()

    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        cfg = analysis_config
        n = len(df)
        window = df.iloc[max(0, n - cfg.VWAP_LOOKBACK_BARS):].reset_index(drop=True)
        current_price = float(window["close"].iloc[-1])

        daily_anchor = self._daily_anchor_index(window)
        daily_series, d_u1, d_l1, d_u2, d_l2 = self._compute_vwap(window, daily_anchor)

        swing_anchor = self._swing_anchor_index(window)
        anchored_series, a_u1, a_l1, a_u2, a_l2 = self._compute_vwap(window, swing_anchor)

        daily_now = float(daily_series.iloc[-1])
        anchored_now = float(anchored_series.iloc[-1])
        bias = PatternDirection.BULLISH if current_price > daily_now else PatternDirection.BEARISH

        annotations = ChartAnnotations(
            trendlines=[
                TrendlineAnnotation(label="daily_vwap", points=self._to_points(window, daily_series)),
                TrendlineAnnotation(label="anchored_vwap", points=self._to_points(window, anchored_series)),
            ],
            levels=[
                LevelAnnotation(label="daily_vwap_+1std", price=round(d_u1, 8)),
                LevelAnnotation(label="daily_vwap_-1std", price=round(d_l1, 8)),
                LevelAnnotation(label="daily_vwap_+2std", price=round(d_u2, 8)),
                LevelAnnotation(label="daily_vwap_-2std", price=round(d_l2, 8)),
            ],
        )

        summary = f"Price {'above' if current_price > daily_now else 'below'} daily VWAP (${daily_now:.2f})."

        return AnalysisToolResult(
            tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
            bias=bias, summary=summary,
            data={
                "daily_vwap": round(daily_now, 8), "anchored_vwap": round(anchored_now, 8),
                "daily_upper_1std": round(d_u1, 8), "daily_lower_1std": round(d_l1, 8),
                "daily_upper_2std": round(d_u2, 8), "daily_lower_2std": round(d_l2, 8),
                "anchored_upper_1std": round(a_u1, 8), "anchored_lower_1std": round(a_l1, 8),
            },
            annotations=annotations, last_updated=now_iso(),
        )

    @staticmethod
    def _daily_anchor_index(df: pd.DataFrame) -> int:
        last_date = df["timestamps"].iloc[-1].date()
        for i in range(len(df)):
            if df["timestamps"].iloc[i].date() == last_date:
                return i
        return 0

    def _swing_anchor_index(self, df: pd.DataFrame) -> int:
        swings = self.swings.find_swings(df)
        return swings[-1].index if swings else 0

    @staticmethod
    def _compute_vwap(df: pd.DataFrame, anchor_idx: int):
        segment = df.iloc[anchor_idx:]
        typical_price = (segment["high"] + segment["low"] + segment["close"]) / 3
        volume = segment["volume"]
        cum_vol = volume.cumsum().replace(0, np.nan)
        vwap = (typical_price * volume).cumsum() / cum_vol

        variance = ((typical_price - vwap) ** 2 * volume).cumsum() / cum_vol
        stddev = np.sqrt(variance)

        cfg = analysis_config
        upper1 = float((vwap + stddev * cfg.VWAP_STDDEV_MULTIPLIER_1).iloc[-1])
        lower1 = float((vwap - stddev * cfg.VWAP_STDDEV_MULTIPLIER_1).iloc[-1])
        upper2 = float((vwap + stddev * cfg.VWAP_STDDEV_MULTIPLIER_2).iloc[-1])
        lower2 = float((vwap - stddev * cfg.VWAP_STDDEV_MULTIPLIER_2).iloc[-1])

        full_series = pd.Series(index=df.index, dtype=float)
        full_series.loc[segment.index] = vwap
        return full_series, upper1, lower1, upper2, lower2

    @staticmethod
    def _to_points(df: pd.DataFrame, series: pd.Series) -> list[ChartPoint]:
        valid = series.dropna()
        step = max(1, len(valid) // 100)
        return [
            ChartPoint(time=df["timestamps"].iloc[i].isoformat(), price=float(valid.iloc[j]))
            for j, i in enumerate(valid.index) if j % step == 0
        ]
