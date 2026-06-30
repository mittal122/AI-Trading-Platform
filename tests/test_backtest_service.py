from backend.app.services.backtest.backtest_factory import (
    BacktestFactory,
)

engine = BacktestFactory.get_engine()

result = engine.run(
    strategy="rsi",
    symbol="BTCUSDT",
    interval="5m",
    limit=300,
)

print(result.model_dump())