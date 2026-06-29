from backend.app.services.market_service import MarketService

service = MarketService()

df = service.get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=10,
)

print(df.head())
print()
print(df.dtypes)