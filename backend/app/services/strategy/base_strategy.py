from abc import ABC, abstractmethod

import pandas as pd

from backend.app.schemas.trading_signal import TradingSignal


class BaseStrategy(ABC):

    @abstractmethod
    def generate_signal(
        self,
        market: pd.DataFrame,
        symbol: str,
        interval: str,
    ) -> TradingSignal:
        """Generate a trading signal from closed historical candles."""
        pass