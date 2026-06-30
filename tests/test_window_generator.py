from backend.app.services.market_service import (
    MarketService,
)

from backend.app.services.backtest.window import (
    WindowGenerator,
)

service = MarketService()

market = service.get_market_data(
    symbol="BTCUSDT",
    interval="5m",
    limit=220,
)

count = 0

for window in WindowGenerator.generate(
    market,
):

    count += 1

print("Windows:", count)

print()

print("First Window Size:")

print(len(window))