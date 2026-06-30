from abc import ABC, abstractmethod

from backend.app.schemas.execution import (
    ExecutionResponse,
    OrderSide,
)


class BaseExecution(ABC):

    @abstractmethod
    def execute(
        self,
        side: OrderSide,
        price: float,
        quantity: float,
    ) -> ExecutionResponse:
        """
        Simulate execution.
        """
        pass