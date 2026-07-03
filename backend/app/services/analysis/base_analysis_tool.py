from abc import ABC, abstractmethod

import pandas as pd

from backend.app.schemas.analysis_tool import AnalysisToolResult


class BaseAnalysisTool(ABC):
    """
    Every analysis tool computes its data + chart annotations from closed
    candles, algorithmically — no AI here (mirrors the pattern/strategy
    layers' separation rule). AI interpretation is a separate, on-demand
    layer (`AnalysisExplainer`) that reads the already-computed results.
    """

    key: str
    name: str

    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        pass
