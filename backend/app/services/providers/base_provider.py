from abc import ABC, abstractmethod

import pandas as pd


class BaseMarketProvider(ABC):

    @abstractmethod
    def get_market_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
    ) -> pd.DataFrame:
        """
        Return market candles as a pandas DataFrame.
        """
        pass