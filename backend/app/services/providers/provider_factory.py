from backend.app.services.providers.binance_provider import (
    BinanceProvider,
)


class ProviderFactory:

    @staticmethod
    def get_provider(
        provider: str = "binance",
    ):

        provider = provider.lower()

        providers = {
            "binance": BinanceProvider,
        }

        if provider not in providers:
            raise ValueError(
                f"Unknown provider: {provider}"
            )

        return providers[provider]()