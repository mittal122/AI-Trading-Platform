from backend.app.services.market_service import MarketService
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.market_regime import MarketRegime
from backend.app.services.strategy.signal_score import SignalScore
from backend.app.services.strategy.trade_quality import TradeQuality

market = MarketService()
indicator = IndicatorService()
regime_engine = MarketRegime()
signal_score = SignalScore()
trade_quality = TradeQuality()

df = market.get_market_data(symbol="BTCUSDT", interval="5m", limit=250)
values = indicator.calculate_from_dataframe(df)
regime = regime_engine.detect(values)
score = signal_score.score(values, regime=regime)

quality = trade_quality.score(
    values=values,
    score=score,
    regime=regime,
    risk_reward=2.0,
)

print("\n========== TRADE QUALITY ==========\n")
for key, value in quality.items():
    print(f"{key:<20} : {value}")
