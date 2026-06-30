from backend.app.schemas.trading_signal import TradingSignal, SignalDirection
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.market_regime import MarketRegime
from backend.app.services.risk.dynamic_atr import DynamicATR


class MACDStrategy(BaseStrategy):
    """
    MACD Crossover Strategy.
    BUY when MACD line crosses above signal line (histogram flips positive).
    SELL when MACD line crosses below signal line (histogram flips negative).
    Requires trend alignment and ADX confirmation.
    """

    def __init__(self):

        self.indicators = IndicatorService()
        self.market_regime = MarketRegime()
        self.dynamic_atr = DynamicATR()

    def generate_signal(
        self,
        market,
        symbol: str,
        interval: str,
    ) -> TradingSignal:

        values = self.indicators.calculate_from_dataframe(market)

        price = values["price"]
        atr = values["atr14"]

        regime = self.market_regime.detect(values)

        # -------------------------
        # MACD Crossover Signal
        # -------------------------

        direction = SignalDirection.FLAT
        reasons = []
        confidence = 0.0

        if values["macd_crossed_bullish"]:

            if values["trend"] != "BEARISH":

                direction = SignalDirection.BUY
                confidence = 60.0
                reasons.append("MACD crossed above signal line.")

                if values["trend"] == "BULLISH":
                    confidence += 15.0
                    reasons.append("MACD crossover aligned with bull trend.")

                if values["adx14"] > 25:
                    confidence += 10.0
                    reasons.append(f"Strong trend confirmed (ADX={values['adx14']:.1f}).")

                if values["price"] > values["vwap"]:
                    confidence += 5.0
                    reasons.append("Price above VWAP.")

        elif values["macd_crossed_bearish"]:

            if values["trend"] != "BULLISH":

                direction = SignalDirection.SELL
                confidence = 60.0
                reasons.append("MACD crossed below signal line.")

                if values["trend"] == "BEARISH":
                    confidence += 15.0
                    reasons.append("MACD crossover aligned with bear trend.")

                if values["adx14"] > 25:
                    confidence += 10.0
                    reasons.append(f"Strong trend confirmed (ADX={values['adx14']:.1f}).")

                if values["price"] < values["vwap"]:
                    confidence += 5.0
                    reasons.append("Price below VWAP.")

        else:

            # No fresh crossover — report current momentum direction
            if values["histogram"] > 0:
                reasons.append("MACD histogram positive — bullish momentum.")
            else:
                reasons.append("MACD histogram negative — bearish momentum.")

            reasons.append("No fresh MACD crossover detected.")

        # Regime confirmation bonus
        if regime["regime"] in ("STRONG_BULL",) and direction == SignalDirection.BUY:
            confidence += 10.0
        elif regime["regime"] in ("STRONG_BEAR",) and direction == SignalDirection.SELL:
            confidence += 10.0
        elif regime["regime"] == "SIDEWAYS":
            confidence *= 0.7  # Reduce confidence in ranging markets

        confidence = min(confidence, 100.0)

        # -------------------------
        # Dynamic Stop / TP
        # -------------------------

        stop_loss, take_profit = self.dynamic_atr.calculate_levels(
            direction=direction.value,
            price=price,
            atr=atr,
            regime=regime,
        )

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        risk_reward = reward / risk if risk > 0 else 0.0

        return TradingSignal(
            strategy="MACD Crossover",
            symbol=symbol,
            interval=interval,
            timestamp=market.iloc[-1]["timestamps"].isoformat(),
            direction=direction,
            confidence=confidence,
            entry=price,
            atr=atr,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            reasons=reasons,
            regime=regime["regime"],
        )
