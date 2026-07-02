import numpy as np
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

    def calculate_cta_trend(
        self,
        df,
        fast_ema_1: int,
        slow_ema_1: int,
        fast_ema_2: int,
        slow_ema_2: int,
        fast_ema_3: int,
        slow_ema_3: int,
        mom_lookback_1: int,
        mom_lookback_2: int,
        vol_lookback: int,
        periods_per_year: int,
        atr_period: int,
    ) -> dict:
        """
        CTA Trend composite — 3 EMA-crossover sub-signals + 2 time-series
        momentum sub-signals + realized-volatility-based exposure sizing.
        Used exclusively by CTATrendStrategy; kept here (not in the strategy
        file) per the "IndicatorService calculates indicators" layer rule.
        """

        close = df["close"]
        high = df["high"]
        low = df["low"]

        def last_ema(period: int) -> float:
            return float(EMAIndicator(close=close, window=period).ema_indicator().iloc[-1])

        f1, s1 = last_ema(fast_ema_1), last_ema(slow_ema_1)
        f2, s2 = last_ema(fast_ema_2), last_ema(slow_ema_2)
        f3, s3 = last_ema(fast_ema_3), last_ema(slow_ema_3)

        ma_signal_1 = 1 if f1 > s1 else -1 if f1 < s1 else 0
        ma_signal_2 = 1 if f2 > s2 else -1 if f2 < s2 else 0
        ma_signal_3 = 1 if f3 > s3 else -1 if f3 < s3 else 0

        # Time-series momentum: sign of the return over each lookback window
        price_now = float(close.iloc[-1])

        def momentum_signal(lookback: int) -> int:
            if len(close) <= lookback:
                return 0
            lagged = float(close.iloc[-1 - lookback])
            ret = (price_now / lagged - 1) if lagged > 0 else 0.0
            return 1 if ret > 0 else -1 if ret < 0 else 0

        mom_signal_1 = momentum_signal(mom_lookback_1)
        mom_signal_2 = momentum_signal(mom_lookback_2)

        composite = (ma_signal_1 + ma_signal_2 + ma_signal_3 + mom_signal_1 + mom_signal_2) / 5

        # Realized volatility (annualized) over the vol lookback window
        recent_closes = close.tail(vol_lookback + 1)
        log_returns = np.log(recent_closes / recent_closes.shift(1)).dropna()
        annualized_vol = (
            float(log_returns.std() * np.sqrt(periods_per_year))
            if len(log_returns) > 1
            else 0.0
        )

        atr_series = AverageTrueRange(high=high, low=low, close=close, window=atr_period)
        atr_val = float(atr_series.average_true_range().iloc[-1])

        return {
            "ma_signal_1": ma_signal_1,
            "ma_signal_2": ma_signal_2,
            "ma_signal_3": ma_signal_3,
            "mom_signal_1": mom_signal_1,
            "mom_signal_2": mom_signal_2,
            "composite": composite,
            "annualized_vol": annualized_vol,
            "atr": atr_val,
            "price": price_now,
        }

    def calculate_atr_at_period(self, df, period: int) -> float:
        """ATR at a caller-specified window (atr14 in calculate_from_dataframe
        is fixed at 14 — Turtle Trading needs a configurable N-period ATR)."""
        atr_series = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=period
        ).average_true_range()
        return float(atr_series.iloc[-1])

    def rolling_channel(self, df, period: int, exclude_current: bool = True) -> tuple[float, float]:
        """Highest high / lowest low over the last `period` candles.
        exclude_current=True looks only at CLOSED candles (drops the last row)
        to avoid look-ahead bias on the in-progress bar."""
        window = df.iloc[:-1] if exclude_current else df
        window = window.tail(period)
        return float(window["high"].max()), float(window["low"].min())

    def calculate_rsi_series(self, df, period: int):
        """Full RSI series (calculate_from_dataframe only returns the latest
        scalar) — needed for divergence detection over a lookback window."""
        return RSIIndicator(close=df["close"], window=period).rsi()
