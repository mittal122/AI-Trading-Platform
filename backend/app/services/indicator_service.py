import pandas_ta as pta

from ta.trend import (
    SMAIndicator,
    EMAIndicator,
    MACD,
    ADXIndicator,
)

from ta.momentum import (
    RSIIndicator,
)

from ta.volatility import (
    BollingerBands,
    AverageTrueRange,
)

from ta.volume import (
    VolumeWeightedAveragePrice,
)

from backend.app.core.strategy_config import strategy_config
from backend.app.services.market_service import MarketService


class IndicatorService:

    def __init__(self):
        self.market = MarketService()

    def calculate(
        self,
        symbol: str,
        interval: str,
        limit: int = 250,
    ):

        df = self.market.get_market_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        return self.calculate_from_dataframe(df)

    def calculate_from_dataframe(
        self,
        df,
    ):

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        volume_sma20 = volume.rolling(window=20).mean()

        # -------------------------
        # Moving Averages
        # -------------------------

        sma20 = SMAIndicator(close=close, window=20).sma_indicator()

        ema20 = EMAIndicator(close=close, window=20).ema_indicator()
        ema50 = EMAIndicator(close=close, window=50).ema_indicator()
        ema200 = EMAIndicator(close=close, window=200).ema_indicator()

        # -------------------------
        # RSI
        # -------------------------

        rsi14 = RSIIndicator(close=close, window=14).rsi()

        # -------------------------
        # MACD
        # -------------------------

        macd = MACD(close=close)
        histogram = macd.macd_diff()

        # -------------------------
        # Bollinger Bands
        # -------------------------

        bb = BollingerBands(close=close, window=20)

        bollinger_width = bb.bollinger_hband() - bb.bollinger_lband()

        # -------------------------
        # ATR
        # -------------------------

        atr = AverageTrueRange(high=high, low=low, close=close, window=14)

        # -------------------------
        # ADX
        # -------------------------

        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        plus_di = adx.adx_pos()
        minus_di = adx.adx_neg()

        # -------------------------
        # VWAP
        # -------------------------

        vwap = VolumeWeightedAveragePrice(
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

        # -------------------------
        # Relative Volume
        # -------------------------

        relative_volume = volume.iloc[-1] / volume_sma20.iloc[-1]

        # -------------------------
        # Trend Detection (EMA alignment)
        # -------------------------

        trend = "SIDEWAYS"

        if (
            ema20.iloc[-1] > ema50.iloc[-1]
            and ema50.iloc[-1] > ema200.iloc[-1]
        ):
            trend = "BULLISH"

        elif (
            ema20.iloc[-1] < ema50.iloc[-1]
            and ema50.iloc[-1] < ema200.iloc[-1]
        ):
            trend = "BEARISH"

        # -------------------------
        # EMA Crossover detection (previous values)
        # -------------------------

        prev_ema20 = float(ema20.iloc[-2])
        prev_ema50 = float(ema50.iloc[-2])

        ema20_crossed_above_ema50 = (
            prev_ema20 < prev_ema50
            and ema20.iloc[-1] > ema50.iloc[-1]
        )

        ema20_crossed_below_ema50 = (
            prev_ema20 > prev_ema50
            and ema20.iloc[-1] < ema50.iloc[-1]
        )

        # -------------------------
        # MACD Crossover detection (previous histogram)
        # -------------------------

        prev_histogram = float(histogram.iloc[-2])

        macd_crossed_bullish = (
            prev_histogram < 0
            and histogram.iloc[-1] > 0
        )

        macd_crossed_bearish = (
            prev_histogram > 0
            and histogram.iloc[-1] < 0
        )

        # -------------------------
        # Supertrend
        # -------------------------

        supertrend_result = pta.supertrend(
            high=high,
            low=low,
            close=close,
            length=strategy_config.SUPERTREND_PERIOD,
            multiplier=strategy_config.SUPERTREND_MULTIPLIER,
        )

        st_col = f"SUPERT_{strategy_config.SUPERTREND_PERIOD}_{strategy_config.SUPERTREND_MULTIPLIER}"
        st_dir_col = f"SUPERTd_{strategy_config.SUPERTREND_PERIOD}_{strategy_config.SUPERTREND_MULTIPLIER}"

        supertrend_value = float(supertrend_result[st_col].iloc[-1])
        supertrend_direction = (
            "BULLISH"
            if supertrend_result[st_dir_col].iloc[-1] == 1
            else "BEARISH"
        )

        # -------------------------
        # Return all values
        # -------------------------

        return {

            "price": float(close.iloc[-1]),

            "sma20": float(sma20.iloc[-1]),

            "ema20": float(ema20.iloc[-1]),
            "ema50": float(ema50.iloc[-1]),
            "ema200": float(ema200.iloc[-1]),

            "previous_ema20": prev_ema20,
            "previous_ema50": prev_ema50,

            "ema20_crossed_above_ema50": ema20_crossed_above_ema50,
            "ema20_crossed_below_ema50": ema20_crossed_below_ema50,

            "rsi14": float(rsi14.iloc[-1]),
            "previous_rsi14": float(rsi14.iloc[-2]),

            "macd": float(macd.macd().iloc[-1]),
            "signal": float(macd.macd_signal().iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
            "previous_histogram": prev_histogram,

            "macd_crossed_bullish": macd_crossed_bullish,
            "macd_crossed_bearish": macd_crossed_bearish,

            "bb_upper": float(bb.bollinger_hband().iloc[-1]),
            "bb_middle": float(bb.bollinger_mavg().iloc[-1]),
            "bb_lower": float(bb.bollinger_lband().iloc[-1]),

            "bollinger_width": float(bollinger_width.iloc[-1]),

            "atr14": float(atr.average_true_range().iloc[-1]),

            "vwap": float(vwap.volume_weighted_average_price().iloc[-1]),

            "adx14": float(adx.adx().iloc[-1]),
            "plus_di": float(plus_di.iloc[-1]),
            "minus_di": float(minus_di.iloc[-1]),

            "volume_sma20": float(volume_sma20.iloc[-1]),
            "relative_volume": float(relative_volume),

            "supertrend": supertrend_value,
            "supertrend_direction": supertrend_direction,

            "trend": trend,

        }
