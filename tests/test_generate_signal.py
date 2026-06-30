from backend.app.services.market_service import MarketService
from backend.app.services.strategy.rsi_strategy import RSIStrategy

market = MarketService().get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=200,
)

strategy = RSIStrategy()

signal = strategy.generate_signal(
    market=market,
    symbol="BTCUSDT",
    interval="5m",
)

print(signal.model_dump())