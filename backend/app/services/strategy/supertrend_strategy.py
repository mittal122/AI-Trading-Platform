from backend.app.schemas.trading_signal import TradingSignal, SignalDirection
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.market_regime import MarketRegime
from backend.app.services.risk.dynamic_atr import DynamicATR


class SupertrendStrategy(BaseStrategy):
    """
    Supertrend Strategy.
    BUY when Supertrend flips to BULLISH (price closes above Supertrend line).
    SELL when Supertrend flips to BEARISH (price closes below Supertrend line).
    Confirms with ADX and volume.
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
        # Supertrend Signal
        # -------------------------

        st_direction = values["supertrend_direction"]
        st_value = values["supertrend"]

        direction = SignalDirection.FLAT
        reasons = []
        confidence = 0.0

        distance_pct = abs(price - st_value) / price * 100

        if st_direction == "BULLISH":

            direction = SignalDirection.BUY
            confidence = 60.0
            reasons.append(
                f"Supertrend bullish (price {distance_pct:.2f}% above supertrend line)."
            )

            # Confirmation checks
            if values["trend"] == "BULLISH":
                confidence += 15.0
                reasons.append("EMA trend aligns with Supertrend direction.")

            if values["adx14"] > 25:
                confidence += 10.0
                reasons.append(f"Strong directional trend (ADX={values['adx14']:.1f}).")

            if values["relative_volume"] > 1.2:
                confidence += 5.0
                reasons.append("Above-average volume.")

            if values["price"] > values["vwap"]:
                confidence += 5.0
                reasons.append("Price above VWAP.")

            if regime["regime"] in ("STRONG_BULL", "WEAK_BULL"):
                confidence += 5.0
                reasons.append(f"Regime confirms: {regime['regime']}.")

        elif st_direction == "BEARISH":

            direction = SignalDirection.SELL
            confidence = 60.0
            reasons.append(
                f"Supertrend bearish (price {distance_pct:.2f}% below supertrend line)."
            )

            if values["trend"] == "BEARISH":
                confidence += 15.0
                reasons.append("EMA trend aligns with Supertrend direction.")

            if values["adx14"] > 25:
                confidence += 10.0
                reasons.append(f"Strong directional trend (ADX={values['adx14']:.1f}).")

            if values["relative_volume"] > 1.2:
                confidence += 5.0
                reasons.append("Above-average volume.")

            if values["price"] < values["vwap"]:
                confidence += 5.0
                reasons.append("Price below VWAP.")

            if regime["regime"] in ("STRONG_BEAR", "WEAK_BEAR"):
                confidence += 5.0
                reasons.append(f"Regime confirms: {regime['regime']}.")

        # Sideways dampener
        if regime["regime"] == "SIDEWAYS":
            confidence *= 0.75
            reasons.append("Sideways regime — reduced confidence.")

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
            strategy="Supertrend",
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
