from abc import ABC, abstractmethod

from backend.app.schemas.portfolio import PortfolioResponse


class BasePortfolio(ABC):

    @abstractmethod
    def get_state(
        self,
    ) -> PortfolioResponse:
        """
        Return current portfolio state.
        """
        pass