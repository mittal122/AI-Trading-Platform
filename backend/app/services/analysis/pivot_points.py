import pandas as pd

from backend.app.core.analysis_config import analysis_config
from backend.app.schemas.analysis_tool import AnalysisToolResult
from backend.app.schemas.pattern import ChartAnnotations, LevelAnnotation, PatternDirection
from backend.app.services.analysis.base_analysis_tool import BaseAnalysisTool
from backend.app.services.market_service import MarketService
from backend.app.services.pattern.pattern_utils import now_iso


class PivotPointsTool(BaseAnalysisTool):
    """
    5 pivot-point systems (Classic, Fibonacci, Camarilla, Woodie, DeMark),
    all computed from the prior FULL daily period's O/H/L/C — the
    professional convention regardless of the chart's own interval (daily
    pivots are shown on any intraday timeframe, not recomputed per-bar).
    Only the Classic set is drawn on the chart by default (7 levels); all 5
    systems' full data is returned for the info panel.
    """

    key = "pivot_points"
    name = "Pivot Points"

    def __init__(self):
        self.market = MarketService()

    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        current_price = float(df["close"].iloc[-1])

        try:
            daily = self.market.get_market_data(
                symbol=symbol, interval=analysis_config.PIVOT_ANCHOR_INTERVAL, limit=3,
            )
        except Exception as exc:
            return AnalysisToolResult(
                tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
                bias=PatternDirection.NEUTRAL, summary="Pivot data unavailable",
                annotations=ChartAnnotations(), last_updated=now_iso(), error=str(exc),
            )

        # last row may be today's still-forming candle — use the last fully closed one
        prior = daily.iloc[-2] if len(daily) >= 2 else daily.iloc[-1]
        o, h, l, c = float(prior["open"]), float(prior["high"]), float(prior["low"]), float(prior["close"])

        systems = {
            "classic": self._classic(h, l, c),
            "fibonacci": self._fibonacci(h, l, c),
            "camarilla": self._camarilla(h, l, c),
            "woodie": self._woodie(h, l, c),
            "demark": self._demark(o, h, l, c),
        }

        classic = systems["classic"]
        bias = (
            PatternDirection.BULLISH if current_price > classic["pp"]
            else PatternDirection.BEARISH if current_price < classic["pp"]
            else PatternDirection.NEUTRAL
        )

        annotations = ChartAnnotations(
            levels=[LevelAnnotation(label=f"classic_{k}", price=round(v, 8)) for k, v in classic.items()],
        )

        summary = f"Price {'above' if bias == PatternDirection.BULLISH else 'below'} classic pivot (${classic['pp']:.2f})."

        return AnalysisToolResult(
            tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
            bias=bias, summary=summary, data=systems,
            annotations=annotations, last_updated=now_iso(),
        )

    @staticmethod
    def _classic(h, l, c) -> dict:
        pp = (h + l + c) / 3
        return {
            "pp": pp, "r1": 2 * pp - l, "s1": 2 * pp - h,
            "r2": pp + (h - l), "s2": pp - (h - l),
            "r3": h + 2 * (pp - l), "s3": l - 2 * (h - pp),
        }

    @staticmethod
    def _fibonacci(h, l, c) -> dict:
        pp = (h + l + c) / 3
        rng = h - l
        return {
            "pp": pp, "r1": pp + 0.382 * rng, "s1": pp - 0.382 * rng,
            "r2": pp + 0.618 * rng, "s2": pp - 0.618 * rng,
            "r3": pp + 1.0 * rng, "s3": pp - 1.0 * rng,
        }

    @staticmethod
    def _camarilla(h, l, c) -> dict:
        rng = h - l
        return {
            "pp": (h + l + c) / 3,
            "r1": c + rng * 1.1 / 12, "s1": c - rng * 1.1 / 12,
            "r2": c + rng * 1.1 / 6, "s2": c - rng * 1.1 / 6,
            "r3": c + rng * 1.1 / 4, "s3": c - rng * 1.1 / 4,
            "r4": c + rng * 1.1 / 2, "s4": c - rng * 1.1 / 2,
        }

    @staticmethod
    def _woodie(h, l, c) -> dict:
        pp = (h + l + 2 * c) / 4
        return {"pp": pp, "r1": 2 * pp - l, "s1": 2 * pp - h, "r2": pp + (h - l), "s2": pp - (h - l)}

    @staticmethod
    def _demark(o, h, l, c) -> dict:
        if c < o:
            x = h + 2 * l + c
        elif c > o:
            x = 2 * h + l + c
        else:
            x = h + l + 2 * c
        pp = x / 4
        return {"pp": pp, "r1": x / 2 - l, "s1": x / 2 - h}
