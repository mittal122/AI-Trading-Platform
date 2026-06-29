from binance.client import Client
import pandas as pd


class MarketService:

    def __init__(self):
        self.client = Client()

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

    def get_market_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
    ):

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
                "trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )

        df["timestamps"] = pd.to_datetime(df["open_time"], unit="ms")

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_asset_volume",
        ]

        for column in numeric_columns:
            df[column] = df[column].astype(float)

        return pd.DataFrame(
            {
                "timestamps": df["timestamps"],
                "open": df["open"],
                "high": df["high"],
                "low": df["low"],
                "close": df["close"],
                "volume": df["volume"],
                "amount": df["quote_asset_volume"],
            }
        )