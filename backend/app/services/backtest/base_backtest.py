from abc import ABC, abstractmethod

from backend.app.schemas.backtest import BacktestResult


class BaseBacktest(ABC):

    @abstractmethod
    def run(self) -> BacktestResult:
        """
        Run a strategy backtest.
        """
        pass