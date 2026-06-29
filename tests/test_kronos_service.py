from backend.app.core.ai import kronos
from backend.app.services.market_service import MarketService


market = MarketService()

kronos.load()

df = market.get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=400,
)

prediction = kronos.predict(
    df=df,
    pred_len=24,
)

print(prediction.head())