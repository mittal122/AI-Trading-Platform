from backend.app.services.market_service import MarketService
from backend.app.services.strategy.turtle_strategy import TurtleStrategy
from backend.app.services.strategy.strategy_factory import StrategyFactory

market = MarketService()
strategy = TurtleStrategy()

df = market.get_market_data(symbol="BTCUSDT", interval="1h", limit=300)

signal = strategy.generate_signal(market=df, symbol="BTCUSDT", interval="1h")

print("\n========== TURTLE TRADING STRATEGY ==========\n")
print(f"Direction   : {signal.direction.value}")
print(f"Confidence  : {signal.confidence:.1f}")
print(f"Entry       : {signal.entry:.2f}")
print(f"N (ATR)     : {signal.atr:.2f}")
print(f"Stop Loss   : {signal.stop_loss:.2f}")
print(f"Take Profit : {signal.take_profit:.2f}")
print(f"Risk/Reward : {signal.risk_reward:.2f}")
print(f"Regime      : {signal.regime}")
print(f"Reasons     : {signal.reasons}")

assert signal.strategy == "Turtle Trading"
assert signal.direction.value in ("BUY", "SELL", "FLAT")
assert signal.entry > 0
if signal.direction.value != "FLAT":
    assert signal.stop_loss != signal.entry
    assert signal.take_profit != signal.entry
    # Turtle uses fixed 2N/4N stop/target — risk_reward should be exactly 2.0
    assert abs(signal.risk_reward - 2.0) < 0.01
print("\nPASS: direction/entry/stop/target sane, RR matches 2N/4N ratio")

factory_strategy = StrategyFactory.get_strategy("turtle")
assert isinstance(factory_strategy, TurtleStrategy)
print("PASS: StrategyFactory.get_strategy('turtle') resolves correctly")

short_df = df.tail(20)
flat_signal = strategy.generate_signal(market=short_df, symbol="BTCUSDT", interval="1h")
assert flat_signal.direction.value == "FLAT"
print("PASS: short history correctly returns FLAT instead of erroring")

print("\n========== RESULTS: all checks passed ==========")
