import pandas as pd
from binance.client import Client

from backend.app.services.providers.base_provider import (
    BaseMarketProvider,
)

class BinanceProvider(BaseMarketProvider):

    INTERVAL_MAP = {
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "3m": Client.KLINE_INTERVAL_3MINUTE,
        "5m": Client.KLINE_INTERVAL_5MINUTE,
        "15m": Client.KLINE_INTERVAL_15MINUTE,
        "30m": Client.KLINE_INTERVAL_30MINUTE,
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "1d": Client.KLINE_INTERVAL_1DAY,
    }

    def __init__(self):
        self.client = Client()

    def get_market_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
    ) -> pd.DataFrame:

        klines = self.client.get_klines(
    symbol=symbol.upper(),
    interval=self.INTERVAL_MAP[interval],
    limit=limit,
)

        df = pd.DataFrame(
            klines,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )

        df = df[
            [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_asset_volume",
            ]
        ]

        df.rename(
            columns={
                "open_time": "timestamps",
                "quote_asset_volume": "amount",
            },
            inplace=True,
        )

        df["timestamps"] = pd.to_datetime(
            df["timestamps"],
            unit="ms",
        )

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
        ]

        df[numeric_columns] = df[
            numeric_columns
        ].astype(float)

        return df