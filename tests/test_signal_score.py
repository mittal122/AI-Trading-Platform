from backend.app.services.market_service import MarketService
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.signal_score import SignalScore

market = MarketService()
indicator = IndicatorService()
score_engine = SignalScore()

df = market.get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=250,
)

values = indicator.calculate_from_dataframe(df)

result = score_engine.score(values)

print("\n========== SIGNAL SCORE ==========\n")

for key, value in result.items():
    print(f"{key:<15} : {value}")