import pandas as pd
import pandas_ta as pta
from ta.trend import EMAIndicator, SMAIndicator

from backend.app.core.analysis_config import analysis_config
from backend.app.schemas.analysis_tool import AnalysisToolResult
from backend.app.schemas.pattern import ChartAnnotations, ChartPoint, LabelAnnotation, PatternDirection, TrendlineAnnotation
from backend.app.services.analysis.base_analysis_tool import BaseAnalysisTool
from backend.app.services.pattern.pattern_utils import now_iso

# Lines actually drawn on the chart — all periods/types are still returned in
# `data` for the info panel, but drawing all 12 (3 types x 4 periods) would
# make the chart unreadable.
CHART_LINES = [("ema", 20), ("ema", 50), ("sma", 50), ("sma", 200)]


class MovingAveragesTool(BaseAnalysisTool):
    """
    EMA/SMA/WMA at 20/50/100/200, Golden Cross (SMA50 crosses above SMA200)
    / Death Cross (crosses below) — the standard convention uses SMA, not
    EMA, for these two specifically. Trend bias from price vs. the EMA stack
    ordering (20 > 50 > 200 = bullish, reversed = bearish).
    """

    key = "moving_averages"
    name = "Moving Averages"

    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        cfg = analysis_config
        close = df["close"]
        current_price = float(close.iloc[-1])

        series = {}
        for period in cfg.MA_PERIODS:
            series[("ema", period)] = EMAIndicator(close, window=period).ema_indicator()
            series[("sma", period)] = SMAIndicator(close, window=period).sma_indicator()
            series[("wma", period)] = pta.wma(close, length=period)

        data = {
            f"{kind}{period}": round(float(s.iloc[-1]), 8) if not pd.isna(s.iloc[-1]) else None
            for (kind, period), s in series.items()
        }

        golden_cross, death_cross = self._detect_cross(
            series[("sma", cfg.MA_GOLDEN_DEATH_FAST)], series[("sma", cfg.MA_GOLDEN_DEATH_SLOW)],
        )

        ema20, ema50, ema200 = data.get("ema20"), data.get("ema50"), data.get("ema200")
        bias = PatternDirection.NEUTRAL
        if ema20 and ema50 and ema200:
            if ema20 > ema50 > ema200:
                bias = PatternDirection.BULLISH
            elif ema20 < ema50 < ema200:
                bias = PatternDirection.BEARISH

        annotations = ChartAnnotations(
            trendlines=[
                TrendlineAnnotation(
                    label=f"{kind}{period}",
                    points=self._to_points(df, series[(kind, period)]),
                )
                for kind, period in CHART_LINES
            ],
        )
        if golden_cross:
            annotations.labels.append(LabelAnnotation(
                text="Golden Cross", time=df["timestamps"].iloc[-1].isoformat(), price=current_price,
            ))
        if death_cross:
            annotations.labels.append(LabelAnnotation(
                text="Death Cross", time=df["timestamps"].iloc[-1].isoformat(), price=current_price,
            ))

        summary = f"Trend bias {bias.value}."
        if golden_cross:
            summary += " Golden Cross just triggered (SMA50 > SMA200)."
        if death_cross:
            summary += " Death Cross just triggered (SMA50 < SMA200)."

        data["golden_cross"] = golden_cross
        data["death_cross"] = death_cross

        return AnalysisToolResult(
            tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
            bias=bias, summary=summary, data=data,
            annotations=annotations, last_updated=now_iso(),
        )

    @staticmethod
    def _detect_cross(fast: pd.Series, slow: pd.Series) -> tuple[bool, bool]:
        if len(fast) < 2 or pd.isna(fast.iloc[-2]) or pd.isna(slow.iloc[-2]):
            return False, False
        prev_fast, prev_slow = fast.iloc[-2], slow.iloc[-2]
        curr_fast, curr_slow = fast.iloc[-1], slow.iloc[-1]
        golden = prev_fast <= prev_slow and curr_fast > curr_slow
        death = prev_fast >= prev_slow and curr_fast < curr_slow
        return bool(golden), bool(death)

    @staticmethod
    def _to_points(df: pd.DataFrame, series: pd.Series) -> list[ChartPoint]:
        valid = series.dropna()
        step = max(1, len(valid) // 100)  # thin out for chart performance
        return [
            ChartPoint(time=df["timestamps"].iloc[i].isoformat(), price=float(valid.iloc[j]))
            for j, i in enumerate(valid.index) if j % step == 0
        ]
