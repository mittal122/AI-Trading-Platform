from backend.app.schemas.strategy import StrategyResponse
from backend.app.services.indicator_service import IndicatorService

from backend.app.services.strategy.base_strategy import (
    BaseStrategy,
)


class RSIStrategy(BaseStrategy):

    def __init__(self):

        self.indicators = IndicatorService()

    def analyze(
        self,
        symbol: str,
        interval: str,
    ) -> StrategyResponse:

        values = self.indicators.calculate(
            symbol=symbol,
            interval=interval,
        )

        price = values["price"]
        rsi = values["rsi14"]

        signal = "HOLD"
        confidence = 50.0
        reasons = []

        if rsi < 30:

            signal = "BUY"
            confidence = 90.0
            reasons.append("RSI indicates oversold market.")

        elif rsi > 70:

            signal = "SELL"
            confidence = 90.0
            reasons.append("RSI indicates overbought market.")

        else:

            reasons.append("RSI is in the neutral zone.")

        stop_loss = price * 0.99
        take_profit = price * 1.02

        return StrategyResponse(
            strategy="RSI Strategy",
            symbol=symbol,
            interval=interval,
            signal=signal,
            confidence=confidence,
            entry=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=2.0,
            reasons=reasons,
        )