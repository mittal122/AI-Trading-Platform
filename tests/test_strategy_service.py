from backend.app.services.strategy.strategy_factory import (
    StrategyFactory,
)

strategy = StrategyFactory.get_strategy("rsi")

response = strategy.analyze(
    symbol="BTCUSDT",
    interval="5m",
)

print(response.model_dump())