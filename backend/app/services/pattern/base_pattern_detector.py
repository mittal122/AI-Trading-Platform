from abc import ABC, abstractmethod

import pandas as pd

from backend.app.schemas.pattern import DetectedPattern


class BasePatternDetector(ABC):
    """
    Detects zero or more instances of its pattern family from closed
    candles. Pure geometry/statistics — no AI, no trade execution. Mirrors
    the strategy layer's separation rule: this layer only detects
    structure, it never decides what to do about it.
    """

    @abstractmethod
    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[DetectedPattern]:
        pass
