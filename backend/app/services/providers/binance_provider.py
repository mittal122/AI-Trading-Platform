import time
from typing import Optional

import pandas as pd
from binance.client import Client

from backend.app.services.providers.base_provider import (
    BaseMarketProvider,
)

# One 24h-ticker snapshot covers every symbol on the exchange (~3,600 rows)
# and feeds the whole market-overview dashboard — cache it briefly so a
# page full of widgets doesn't hammer Binance with identical requests.
_TICKER_CACHE_TTL_SECONDS = 30.0


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
        "1w": Client.KLINE_INTERVAL_1WEEK,
    }

    def __init__(self):
        self.client = Client()
        self._ticker_cache: tuple[float, list[dict]] | None = None

    def get_provider_name(self):
        return "binance"

    # ------------------------------------------------------------------
    # Market-overview data (24h tickers / order book / taker flow / funding)
    # ------------------------------------------------------------------

    def get_tickers_24h(self, quote_asset: str = "USDT") -> list[dict]:
        """Every {base}{quote_asset} pair's 24h stats, briefly cached."""
        now = time.monotonic()
        if self._ticker_cache and now - self._ticker_cache[0] < _TICKER_CACHE_TTL_SECONDS:
            raw = self._ticker_cache[1]
        else:
            raw = self.client.get_ticker()
            self._ticker_cache = (now, raw)

        out = []
        for t in raw:
            symbol = t["symbol"]
            if not symbol.endswith(quote_asset):
                continue
            # Skip leveraged-token noise (UP/DOWN/BULL/BEAR products).
            base = symbol[: -len(quote_asset)]
            if base.endswith(("UP", "DOWN", "BULL", "BEAR")):
                continue
            try:
                out.append({
                    "symbol": symbol,
                    "last_price": float(t["lastPrice"]),
                    "price_change_pct": float(t["priceChangePercent"]),
                    "high": float(t["highPrice"]),
                    "low": float(t["lowPrice"]),
                    "quote_volume": float(t["quoteVolume"]),
                    "trades": int(t["count"]),
                })
            except (KeyError, ValueError):
                continue
        return out

    def get_depth_summary(self, symbol: str, limit: int = 100) -> dict:
        """Order-book pressure: how much resting notional sits on each side
        near the touch, and where the biggest single walls are — a depth
        imbalance is one of the few footprints of large resting interest."""
        ob = self.client.get_order_book(symbol=symbol.upper(), limit=limit)
        bids = [(float(p), float(q)) for p, q in ob["bids"]]
        asks = [(float(p), float(q)) for p, q in ob["asks"]]
        bid_notional = sum(p * q for p, q in bids)
        ask_notional = sum(p * q for p, q in asks)
        total = bid_notional + ask_notional
        biggest_bid = max(bids, key=lambda x: x[0] * x[1], default=(0.0, 0.0))
        biggest_ask = max(asks, key=lambda x: x[0] * x[1], default=(0.0, 0.0))
        return {
            "symbol": symbol.upper(),
            "bid_notional": round(bid_notional, 2),
            "ask_notional": round(ask_notional, 2),
            "bid_ratio": round(bid_notional / total, 4) if total > 0 else 0.5,
            "best_bid": bids[0][0] if bids else 0.0,
            "best_ask": asks[0][0] if asks else 0.0,
            "biggest_bid_wall_price": biggest_bid[0],
            "biggest_bid_wall_notional": round(biggest_bid[0] * biggest_bid[1], 2),
            "biggest_ask_wall_price": biggest_ask[0],
            "biggest_ask_wall_notional": round(biggest_ask[0] * biggest_ask[1], 2),
            "levels": limit,
        }

    def get_buy_pressure(self, symbol: str, interval: str, limit: int = 20) -> dict:
        """Aggressive (taker) buy share of volume over the last N candles —
        the klines already carry taker-buy volume; the standard OHLCV path
        drops it, so this reads the raw klines directly."""
        klines = self.client.get_klines(
            symbol=symbol.upper(), interval=self.INTERVAL_MAP[interval], limit=limit,
        )
        total_vol = sum(float(k[5]) for k in klines)
        taker_buy = sum(float(k[9]) for k in klines)
        recent = [
            round(float(k[9]) / float(k[5]), 4) if float(k[5]) > 0 else 0.5
            for k in klines[-10:]
        ]
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "candles": len(klines),
            "buy_ratio": round(taker_buy / total_vol, 4) if total_vol > 0 else 0.5,
            "recent_ratios": recent,
        }

    def get_funding(self, symbol: str) -> Optional[dict]:
        """Perpetual-futures funding rate + mark price (public fapi endpoint,
        no key). Positive funding = longs paying shorts (crowded long) —
        the classic institutional positioning read. None if the symbol has
        no perp or futures data is unreachable."""
        try:
            mp = self.client.futures_mark_price(symbol=symbol.upper())
            rate = float(mp["lastFundingRate"])
            return {
                "symbol": symbol.upper(),
                "funding_rate": rate,
                "funding_rate_annualized_pct": round(rate * 3 * 365 * 100, 2),
                "mark_price": float(mp["markPrice"]),
                "next_funding_time": int(mp.get("nextFundingTime", 0)),
            }
        except Exception:
            return None

    def get_supported_intervals(self):
        return list(self.INTERVAL_MAP.keys())

    def get_symbols(self):

        exchange = self.client.get_exchange_info()

        symbols = []

        for item in exchange["symbols"]:

            if item["status"] != "TRADING":
                continue

            symbols.append(
                {
                    "symbol": item["symbol"],
                    "base_asset": item["baseAsset"],
                    "quote_asset": item["quoteAsset"],
                }
            )

        return symbols

    def get_market_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
        end_time: Optional[int] = None,
    ) -> pd.DataFrame:

        kwargs = {}
        if end_time is not None:
            kwargs["endTime"] = end_time

        klines = self.client.get_klines(
            symbol=symbol.upper(),
            interval=self.INTERVAL_MAP[interval],
            limit=limit,
            **kwargs,
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

        df[numeric_columns] = df[numeric_columns].astype(float)

        return df