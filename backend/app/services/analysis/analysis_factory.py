from backend.app.services.analysis.atr_tool import ATRTool
from backend.app.services.analysis.fvg_tool import FVGTool
from backend.app.services.analysis.moving_averages import MovingAveragesTool
from backend.app.services.analysis.pivot_points import PivotPointsTool
from backend.app.services.analysis.support_resistance import SupportResistanceTool
from backend.app.services.analysis.vwap_tool import VWAPTool


class AnalysisFactory:

    TOOLS = {
        "support_resistance": SupportResistanceTool,
        "moving_averages": MovingAveragesTool,
        "vwap": VWAPTool,
        "pivot_points": PivotPointsTool,
        "atr": ATRTool,
        "fvg": FVGTool,
    }

    @staticmethod
    def get_tool(key: str):
        key = key.lower()
        if key not in AnalysisFactory.TOOLS:
            raise ValueError(f"Unknown analysis tool: {key}. Available: {list(AnalysisFactory.TOOLS.keys())}")
        return AnalysisFactory.TOOLS[key]()

    @staticmethod
    def list_tools() -> list[str]:
        return list(AnalysisFactory.TOOLS.keys())

    @staticmethod
    def all_tools() -> list:
        return [cls() for cls in AnalysisFactory.TOOLS.values()]
