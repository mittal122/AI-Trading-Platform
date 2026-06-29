from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice

from backend.app.services.market_service import MarketService


class IndicatorService:

    def __init__(self):
        self.market = MarketService()

    def calculate(
        self,
        symbol: str,
        interval: str,
        limit: int = 200,
    ):

        df = self.market.get_market_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        sma20 = SMAIndicator(
            close=close,
            window=20,
        ).sma_indicator()

        ema20 = EMAIndicator(
            close=close,
            window=20,
        ).ema_indicator()

        rsi14 = RSIIndicator(
            close=close,
            window=14,
        ).rsi()

        macd = MACD(close)

        bb = BollingerBands(
            close,
            window=20,
        )

        atr = AverageTrueRange(
            high=high,
            low=low,
            close=close,
            window=14,
        )

        vwap = VolumeWeightedAveragePrice(
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

        return {
            "price": float(close.iloc[-1]),
            "sma20": float(sma20.iloc[-1]),
            "ema20": float(ema20.iloc[-1]),
            "rsi14": float(rsi14.iloc[-1]),
            "macd": float(macd.macd().iloc[-1]),
            "signal": float(macd.macd_signal().iloc[-1]),
            "histogram": float(macd.macd_diff().iloc[-1]),
            "bb_upper": float(bb.bollinger_hband().iloc[-1]),
            "bb_middle": float(bb.bollinger_mavg().iloc[-1]),
            "bb_lower": float(bb.bollinger_lband().iloc[-1]),
            "atr14": float(atr.average_true_range().iloc[-1]),
            "vwap": float(vwap.volume_weighted_average_price().iloc[-1]),
        }