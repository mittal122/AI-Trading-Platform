from backend.app.schemas.strategy import StrategyResponse
from backend.app.schemas.trading_signal import TradingSignal, SignalDirection

from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.entry_filter import EntryFilter
from backend.app.services.strategy.explainer import Explainer
from backend.app.services.strategy.market_regime import MarketRegime
from backend.app.services.strategy.signal_score import SignalScore
from backend.app.services.strategy.trade_decision import TradeDecision
from backend.app.services.strategy.trade_quality import TradeQuality
from backend.app.services.risk.dynamic_atr import DynamicATR


class RSIStrategy(BaseStrategy):

    def __init__(self):

        self.indicators = IndicatorService()
        self.market_regime = MarketRegime()
        self.signal_score = SignalScore()
        self.trade_decision = TradeDecision()
        self.entry_filter = EntryFilter()
        self.dynamic_atr = DynamicATR()
        self.trade_quality = TradeQuality()
        self.explainer = Explainer()

    def analyze(
        self,
        symbol: str,
        interval: str,
    ) -> StrategyResponse:

        df = self.indicators.market.get_market_data(
            symbol=symbol,
            interval=interval,
            limit=250,
        )

        signal = self.generate_signal(
            market=df,
            symbol=symbol,
            interval=interval,
        )

        return StrategyResponse(
            strategy=signal.strategy,
            symbol=signal.symbol,
            interval=signal.interval,
            signal=signal.direction.value,
            confidence=signal.confidence,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_reward=signal.risk_reward,
            reasons=signal.reasons,
        )

    def generate_signal(
        self,
        market,
        symbol: str,
        interval: str,
    ) -> TradingSignal:

        values = self.indicators.calculate_from_dataframe(market)

        price = values["price"]
        atr = values["atr14"]

        # ---------------------------------
        # Step 1: Market Regime
        # ---------------------------------

        regime = self.market_regime.detect(values)

        # ---------------------------------
        # Step 2: Signal Score (adaptive weighted)
        # ---------------------------------

        score = self.signal_score.score(values, regime=regime)

        # ---------------------------------
        # Step 3: Trade Decision
        # ---------------------------------

        decision = self.trade_decision.decide(score)

        # ---------------------------------
        # Step 4: Entry Filter
        # Block low-quality entries
        # ---------------------------------

        direction = SignalDirection.FLAT

        if decision["decision"] == "BUY":

            valid, failed = self.entry_filter.check_buy(values)

            if valid:
                direction = SignalDirection.BUY
            else:
                print(f"Entry blocked [BUY] — failed: {failed}")

        elif decision["decision"] == "SELL":

            valid, failed = self.entry_filter.check_sell(values)

            if valid:
                direction = SignalDirection.SELL
            else:
                print(f"Entry blocked [SELL] — failed: {failed}")

        # ---------------------------------
        # Step 5: Dynamic ATR Stop / TP
        # ---------------------------------

        stop_loss, take_profit = self.dynamic_atr.calculate_levels(
            direction=direction.value,
            price=price,
            atr=atr,
            regime=regime,
        )

        # ---------------------------------
        # Step 6: Risk Reward
        # ---------------------------------

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        risk_reward = reward / risk if risk > 0 else 0.0

        # ---------------------------------
        # Step 7: Reasons
        # ---------------------------------

        reasons = []
        reasons.extend(score["buy_reasons"])
        reasons.extend(score["sell_reasons"])

        if not reasons:
            reasons.append(decision["reason"])

        # ---------------------------------
        # Step 8: Trade Quality Score
        # ---------------------------------

        quality = self.trade_quality.score(
            values=values,
            score=score,
            regime=regime,
            risk_reward=risk_reward,
        )

        # ---------------------------------
        # Step 9: Explanation
        # ---------------------------------

        explanation = self.explainer.explain(
            direction=direction.value,
            score=score,
            regime=regime,
            values=values,
            quality=quality,
        )

        print("\n========== EXPLANATION ==========")
        print(explanation)
        print()

        return TradingSignal(
            strategy="RSI Strategy",
            symbol=symbol,
            interval=interval,
            timestamp=market.iloc[-1]["timestamps"].isoformat(),
            direction=direction,
            confidence=score["confidence"],
            entry=price,
            atr=atr,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            reasons=reasons,
            regime=regime["regime"],
            quality_score=quality["quality_score"],
            quality_grade=quality["quality_grade"],
            explanation=explanation,
        )
