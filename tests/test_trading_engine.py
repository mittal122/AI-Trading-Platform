from backend.app.services.market_service import MarketService
from backend.app.services.trading.simple_trading_engine import (
    SimpleTradingEngine,
)

from backend.app.services.backtest.window import (
    WindowGenerator,
)

market = MarketService().get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=250,
)

engine = SimpleTradingEngine()

for window in WindowGenerator.generate(market):

    state = engine.process(
        market=window,
        symbol="BTCUSDT",
        interval="5m",
    )

print(state.model_dump())