from backend.app.services.market_service import MarketService
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.market_regime import MarketRegime

market = MarketService()
indicator = IndicatorService()
regime_engine = MarketRegime()

df = market.get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=250,
)

values = indicator.calculate_from_dataframe(df)

result = regime_engine.detect(values)

print("\n========== MARKET REGIME RESULT ==========\n")

for key, value in result.items():
    print(f"{key:<20} : {value}")

print()
print("Regime Classification Logic:")
print(f"  ADX14          : {values['adx14']:.2f}")
print(f"  Trend          : {values['trend']}")
print(f"  ATR14          : {values['atr14']:.4f}")
print(f"  Price          : {values['price']:.2f}")
print(f"  ATR%           : {(values['atr14'] / values['price'] * 100):.2f}%")
print(f"  BB Width       : {values['bollinger_width']:.4f}")
print(f"  BB Width%      : {(values['bollinger_width'] / values['price'] * 100):.2f}%")
