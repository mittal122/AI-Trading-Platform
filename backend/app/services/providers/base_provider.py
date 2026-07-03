from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseMarketProvider(ABC):

    @abstractmethod
    def get_market_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
        end_time: Optional[int] = None,
    ) -> pd.DataFrame:
        """end_time: unix ms — when given, return the `limit` candles ending
        at or before this timestamp instead of the most recent ones. Powers
        backward pagination (e.g. a chart loading older history on scroll)."""
        pass

    @abstractmethod
    def get_symbols(self):
        pass

    @abstractmethod
    def get_supported_intervals(self):
        pass

    @abstractmethod
    def get_provider_name(self):
        pass