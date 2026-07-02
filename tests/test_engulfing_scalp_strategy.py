from backend.app.services.market_service import MarketService
from backend.app.services.strategy.engulfing_scalp_strategy import EngulfingScalpStrategy
from backend.app.services.strategy.strategy_factory import StrategyFactory

market = MarketService()
strategy = EngulfingScalpStrategy()

df = market.get_market_data(symbol="BTCUSDT", interval="1h", limit=300)

signal = strategy.generate_signal(market=df, symbol="BTCUSDT", interval="1h")

print("\n========== ENGULFING SCALP STRATEGY ==========\n")
print(f"Direction   : {signal.direction.value}")
print(f"Confidence  : {signal.confidence:.1f}")
print(f"Entry       : {signal.entry:.2f}")
print(f"Stop Loss   : {signal.stop_loss:.2f}")
print(f"Take Profit : {signal.take_profit:.2f}")
print(f"Risk/Reward : {signal.risk_reward:.2f}")
print(f"Regime      : {signal.regime}")
print(f"Reasons     : {signal.reasons}")

assert signal.strategy == "Engulfing Scalp"
# Long-only strategy — never returns SELL
assert signal.direction.value in ("BUY", "FLAT")
assert signal.entry > 0
if signal.direction.value != "FLAT":
    assert signal.stop_loss < signal.entry
    assert signal.take_profit > signal.entry
    assert 65 <= signal.confidence <= 95
    # SL = range x 2.0, TP = risk x rr_ratio(2.0) -> RR should be exactly 2.0
    assert abs(signal.risk_reward - 2.0) < 0.01
print("\nPASS: long-only, entry/stop/target sane when triggered")

factory_strategy = StrategyFactory.get_strategy("engulfing_scalp")
assert isinstance(factory_strategy, EngulfingScalpStrategy)
print("PASS: StrategyFactory.get_strategy('engulfing_scalp') resolves correctly")

short_df = df.tail(20)
flat_signal = strategy.generate_signal(market=short_df, symbol="BTCUSDT", interval="1h")
assert flat_signal.direction.value == "FLAT"
print("PASS: short history correctly returns FLAT instead of erroring")

print("\n========== RESULTS: all checks passed ==========")
