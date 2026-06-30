from backend.app.schemas.trading_signal import TradingSignal, SignalDirection
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.market_regime import MarketRegime
from backend.app.services.risk.dynamic_atr import DynamicATR
from backend.app.core.strategy_config import strategy_config


class BreakoutStrategy(BaseStrategy):
    """
    Bollinger Band Breakout Strategy.
    BUY when price closes above upper band with volume spike.
    SELL when price closes below lower band with volume spike.
    Filters: regime not SIDEWAYS, relative volume > 1.3.
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
        # Breakout Detection
        # -------------------------

        direction = SignalDirection.FLAT
        reasons = []
        confidence = 0.0

        bb_upper = values["bb_upper"]
        bb_lower = values["bb_lower"]
        bb_width = values["bollinger_width"]
        rel_vol = values["relative_volume"]

        # Avoid breakout signals in sideways unless high volatility
        sideways_filter = regime["regime"] != "SIDEWAYS"

        # Bullish Breakout: price above upper band
        if price > bb_upper and sideways_filter:

            direction = SignalDirection.BUY
            confidence = 65.0
            reasons.append("Price broke above Bollinger upper band.")

            if rel_vol > 1.3:
                confidence += 15.0
                reasons.append(f"Volume spike confirms breakout ({rel_vol:.2f}x avg).")

            if values["trend"] == "BULLISH":
                confidence += 10.0
                reasons.append("Breakout aligned with bull trend.")

            if values["adx14"] > 25:
                confidence += 5.0
                reasons.append(f"Trend strength supports breakout (ADX={values['adx14']:.1f}).")

            if regime["regime"] in ("STRONG_BULL", "WEAK_BULL"):
                confidence += 5.0

        # Bearish Breakout: price below lower band
        elif price < bb_lower and sideways_filter:

            direction = SignalDirection.SELL
            confidence = 65.0
            reasons.append("Price broke below Bollinger lower band.")

            if rel_vol > 1.3:
                confidence += 15.0
                reasons.append(f"Volume spike confirms breakdown ({rel_vol:.2f}x avg).")

            if values["trend"] == "BEARISH":
                confidence += 10.0
                reasons.append("Breakdown aligned with bear trend.")

            if values["adx14"] > 25:
                confidence += 5.0
                reasons.append(f"Trend strength supports breakdown (ADX={values['adx14']:.1f}).")

            if regime["regime"] in ("STRONG_BEAR", "WEAK_BEAR"):
                confidence += 5.0

        else:

            bb_pct = (price - bb_lower) / bb_width * 100 if bb_width > 0 else 50

            reasons.append(
                f"Price inside Bollinger Bands ({bb_pct:.0f}% of band). No breakout."
            )

            if regime["regime"] == "SIDEWAYS":
                reasons.append("Sideways regime — breakout signals filtered.")

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
            strategy="Bollinger Breakout",
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
