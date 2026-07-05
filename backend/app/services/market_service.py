from typing import Optional

from backend.app.services.providers.provider_factory import (
    ProviderFactory,
)


class MarketService:

    def __init__(
        self,
        provider: str = "binance",
    ):
        self.provider = ProviderFactory.get_provider(
            provider
        )

    def get_market_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
        end_time: Optional[int] = None,
    ):
        return self.provider.get_market_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
            end_time=end_time,
        )

    def get_symbols(self):
        return self.provider.get_symbols()

    def get_tickers_24h(self, quote_asset: str = "USDT"):
        return self.provider.get_tickers_24h(quote_asset=quote_asset)

    def get_depth_summary(self, symbol: str, limit: int = 100):
        return self.provider.get_depth_summary(symbol=symbol, limit=limit)

    def get_buy_pressure(self, symbol: str, interval: str, limit: int = 20):
        return self.provider.get_buy_pressure(symbol=symbol, interval=interval, limit=limit)

    def get_raw_order_book(self, symbol: str, limit: int = 100):
        return self.provider.get_raw_order_book(symbol=symbol, limit=limit)

    def get_agg_trades(self, symbol: str, limit: int = 500):
        return self.provider.get_agg_trades(symbol=symbol, limit=limit)

    def get_volume_scan(self, symbol: str, interval: str, window: int = 20):
        return self.provider.get_volume_scan(symbol=symbol, interval=interval, window=window)

    def get_funding(self, symbol: str):
        return self.provider.get_funding(symbol=symbol)

    def get_supported_intervals(self):
        return self.provider.get_supported_intervals()

    def get_provider_name(self):
        return self.provider.get_provider_name()