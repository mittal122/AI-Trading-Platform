from backend.app.services.market_service import MarketService
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.signal_score import SignalScore
from backend.app.services.strategy.trade_decision import TradeDecision

market = MarketService()
indicator = IndicatorService()

score_engine = SignalScore()
decision_engine = TradeDecision()

df = market.get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=250,
)

values = indicator.calculate_from_dataframe(df)

score = score_engine.score(values)

decision = decision_engine.decide(score)

print("\n========== DECISION ==========\n")

for key, value in decision.items():
    print(f"{key:<15}: {value}")