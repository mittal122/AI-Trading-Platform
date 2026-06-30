from backend.app.services.market_service import MarketService
from backend.app.services.strategy.ema_strategy import EMAStrategy

market = MarketService()
strategy = EMAStrategy()

df = market.get_market_data(symbol="BTCUSDT", interval="1h", limit=250)

signal = strategy.generate_signal(market=df, symbol="BTCUSDT", interval="1h")

print("\n========== EMA STRATEGY ==========\n")
print(f"Direction   : {signal.direction.value}")
print(f"Confidence  : {signal.confidence:.1f}")
print(f"Entry       : {signal.entry:.2f}")
print(f"Stop Loss   : {signal.stop_loss:.2f}")
print(f"Take Profit : {signal.take_profit:.2f}")
print(f"Risk/Reward : {signal.risk_reward:.2f}")
print(f"Regime      : {signal.regime}")
print(f"Reasons     : {signal.reasons}")
