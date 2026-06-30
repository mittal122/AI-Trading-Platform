from abc import ABC, abstractmethod

from backend.app.schemas.position import PositionResponse


class BasePosition(ABC):

    @abstractmethod
    def calculate(
        self,
        account_equity: float,
        entry: float,
        stop_loss: float,
        risk_percent: float,
    ) -> PositionResponse:
        """
        Calculate the position size.
        """
        pass