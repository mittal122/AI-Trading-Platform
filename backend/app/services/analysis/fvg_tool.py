import pandas as pd

from backend.app.schemas.analysis_tool import AnalysisToolResult
from backend.app.schemas.pattern import ChartAnnotations, PatternDirection, ZoneAnnotation
from backend.app.services.analysis.base_analysis_tool import BaseAnalysisTool
from backend.app.services.pattern.fvg_detector import FVGDetector
from backend.app.services.pattern.pattern_utils import now_iso


class FVGTool(BaseAnalysisTool):
    """
    Wraps the existing FVGDetector (built for the Pattern module) as a
    standalone toggleable analysis tool — same detection logic, exposed
    through the Analysis Tools system (toggle button, chart zones, help
    panel, AI confluence) instead of only the passive count on the
    Patterns page.
    """

    key = "fvg"
    name = "Fair Value Gaps"

    def __init__(self):
        self.detector = FVGDetector()

    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        gaps = self.detector.detect(df, symbol, interval)
        unfilled = [g for g in gaps if not g.filled]
        bullish_unfilled = [g for g in unfilled if g.type.value == "BULLISH"]
        bearish_unfilled = [g for g in unfilled if g.type.value == "BEARISH"]

        bias = PatternDirection.NEUTRAL
        if len(bullish_unfilled) > len(bearish_unfilled):
            bias = PatternDirection.BULLISH
        elif len(bearish_unfilled) > len(bullish_unfilled):
            bias = PatternDirection.BEARISH

        last_time = df["timestamps"].iloc[-1].isoformat()
        annotations = ChartAnnotations(
            zones=[
                ZoneAnnotation(
                    label=f"fvg_{g.type.value.lower()}_unfilled",
                    start_time=g.formed_at, end_time=last_time,
                    top=g.top, bottom=g.bottom,
                    bias=PatternDirection.BULLISH if g.type.value == "BULLISH" else PatternDirection.BEARISH,
                )
                for g in unfilled  # only unfilled drawn — filled gaps are stale, keeps the chart readable
            ],
        )

        summary = (
            f"{len(unfilled)} unfilled FVG(s) ({len(bullish_unfilled)} bullish, "
            f"{len(bearish_unfilled)} bearish) of {len(gaps)} total detected."
        )

        return AnalysisToolResult(
            tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
            bias=bias, summary=summary,
            data={
                "total_gaps": len(gaps), "unfilled_count": len(unfilled),
                "bullish_unfilled": len(bullish_unfilled), "bearish_unfilled": len(bearish_unfilled),
                "gaps": [g.model_dump() for g in unfilled[:20]],
            },
            annotations=annotations, last_updated=now_iso(),
        )
