from backend.app.services.market_service import MarketService
from backend.app.services.strategy.cta_trend_strategy import CTATrendStrategy
from backend.app.services.strategy.strategy_factory import StrategyFactory

market = MarketService()
strategy = CTATrendStrategy()

df = market.get_market_data(symbol="BTCUSDT", interval="1h", limit=300)

signal = strategy.generate_signal(market=df, symbol="BTCUSDT", interval="1h")

print("\n========== CTA TREND STRATEGY ==========\n")
print(f"Direction   : {signal.direction.value}")
print(f"Confidence  : {signal.confidence:.1f}")
print(f"Entry       : {signal.entry:.2f}")
print(f"ATR         : {signal.atr:.2f}")
print(f"Stop Loss   : {signal.stop_loss:.2f}")
print(f"Take Profit : {signal.take_profit:.2f}")
print(f"Risk/Reward : {signal.risk_reward:.2f}")
print(f"Regime      : {signal.regime}")
print(f"Reasons     : {signal.reasons}")

assert signal.strategy == "CTA Trend"
assert signal.direction.value in ("BUY", "SELL", "FLAT")
assert signal.entry > 0
if signal.direction.value != "FLAT":
    assert signal.stop_loss != signal.entry
    assert signal.take_profit != signal.entry
    assert 0 <= signal.confidence <= 92
print("\nPASS: direction/entry/stop/target sane")

# Also confirm it's wired into the factory under the expected key
factory_strategy = StrategyFactory.get_strategy("cta_trend")
assert isinstance(factory_strategy, CTATrendStrategy)
print("PASS: StrategyFactory.get_strategy('cta_trend') resolves correctly")

# Insufficient-history path returns a clean FLAT signal, not a crash
short_df = df.tail(50)
flat_signal = strategy.generate_signal(market=short_df, symbol="BTCUSDT", interval="1h")
assert flat_signal.direction.value == "FLAT"
print("PASS: short history correctly returns FLAT instead of erroring")

print("\n========== RESULTS: all checks passed ==========")
