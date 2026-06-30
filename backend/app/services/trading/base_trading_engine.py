from abc import ABC, abstractmethod

import pandas as pd


class BaseTradingEngine(ABC):

    @abstractmethod
    def process(
        self,
        market: pd.DataFrame,
        symbol: str,
        interval: str,
    ):
        """
        Process one historical window.

        The trading engine is responsible for:

        - generating the trading signal
        - calculating position size
        - executing the trade
        - updating the portfolio

        One window in.
        Updated portfolio state out.
        """
        pass