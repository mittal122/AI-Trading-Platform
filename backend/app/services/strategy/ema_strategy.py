from backend.app.schemas.trading_signal import TradingSignal, SignalDirection
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.market_regime import MarketRegime
from backend.app.services.strategy.entry_filter import EntryFilter
from backend.app.services.risk.dynamic_atr import DynamicATR


class EMAStrategy(BaseStrategy):
    """
    EMA Crossover Strategy.
    BUY when EMA20 crosses above EMA50 with trend + volume confirmation.
    SELL when EMA20 crosses below EMA50 with trend + volume confirmation.
    """

    def __init__(self):

        self.indicators = IndicatorService()
        self.market_regime = MarketRegime()
        self.entry_filter = EntryFilter()
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
        # EMA Crossover Signal
        # -------------------------

        direction = SignalDirection.FLAT
        reasons = []

        if values["ema20_crossed_above_ema50"]:

            # Confirm with trend and volume
            valid, failed = self.entry_filter.check_buy(values)

            if valid or values["relative_volume"] > 1.2:

                direction = SignalDirection.BUY
                reasons.append("EMA20 crossed above EMA50.")

                if values["ema50"] > values["ema200"]:
                    reasons.append("EMA50 above EMA200 — major uptrend.")

                if values["relative_volume"] > 1.2:
                    reasons.append("Volume confirms crossover.")

        elif values["ema20_crossed_below_ema50"]:

            valid, failed = self.entry_filter.check_sell(values)

            if valid or values["relative_volume"] > 1.2:

                direction = SignalDirection.SELL
                reasons.append("EMA20 crossed below EMA50.")

                if values["ema50"] < values["ema200"]:
                    reasons.append("EMA50 below EMA200 — major downtrend.")

                if values["relative_volume"] > 1.2:
                    reasons.append("Volume confirms crossover.")

        else:

            # No crossover — check trend alignment as continuation signal
            if (
                values["trend"] == "BULLISH"
                and values["adx14"] > 30
                and values["relative_volume"] > 1.3
            ):

                direction = SignalDirection.BUY
                reasons.append("Strong bull trend with EMA alignment.")

            elif (
                values["trend"] == "BEARISH"
                and values["adx14"] > 30
                and values["relative_volume"] > 1.3
            ):

                direction = SignalDirection.SELL
                reasons.append("Strong bear trend with EMA alignment.")

        # -------------------------
        # Dynamic Stop / TP
        # -------------------------

        stop_loss, take_profit = self.dynamic_atr.calculate_levels(
            direction=direction.value,
            price=price,
            atr=atr,
            regime=regime,
        )

        # -------------------------
        # Risk Reward
        # -------------------------

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        risk_reward = reward / risk if risk > 0 else 0.0

        # -------------------------
        # Confidence
        # -------------------------

        confidence = 65.0 if direction != SignalDirection.FLAT else 0.0

        if values["ema20_crossed_above_ema50"] or values["ema20_crossed_below_ema50"]:
            confidence += 10.0

        if regime["regime"] in ("STRONG_BULL", "STRONG_BEAR"):
            confidence += 10.0

        confidence = min(confidence, 100.0)

        if not reasons:
            reasons.append("No EMA crossover detected. Holding.")

        return TradingSignal(
            strategy="EMA Crossover",
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
