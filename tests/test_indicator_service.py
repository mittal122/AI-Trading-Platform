from backend.app.services.market_service import MarketService
from backend.app.services.indicator_service import IndicatorService


market = MarketService()
indicator = IndicatorService()

df = market.get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=250,
)

values = indicator.calculate_from_dataframe(df)

print("\n========== INDICATORS ==========\n")

for key, value in values.items():
    print(f"{key:<20} : {value}")