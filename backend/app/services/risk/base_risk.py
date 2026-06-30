from abc import ABC, abstractmethod

from backend.app.schemas.risk import (
    Direction,
    RiskResponse,
)


class BaseRisk(ABC):

    @abstractmethod
    def calculate(
        self,
        direction: Direction,
        entry: float,
        atr: float,
    ) -> RiskResponse:
        """
        Calculate stop loss and take profit.
        """
        pass