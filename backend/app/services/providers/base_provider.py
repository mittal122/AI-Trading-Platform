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