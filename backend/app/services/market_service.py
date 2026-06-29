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
    ):

        return self.provider.get_market_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )