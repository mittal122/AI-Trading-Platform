from backend.app.services.market_service import MarketService
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.market_regime import MarketRegime
from backend.app.services.risk.dynamic_atr import DynamicATR

market = MarketService()
indicator = IndicatorService()
regime_engine = MarketRegime()
dynamic_atr = DynamicATR()

df = market.get_market_data(symbol="BTCUSDT", interval="5m", limit=250)
values = indicator.calculate_from_dataframe(df)
regime = regime_engine.detect(values)

price = values["price"]
atr = values["atr14"]

sl_buy, tp_buy = dynamic_atr.calculate_levels("BUY", price, atr, regime)
sl_sell, tp_sell = dynamic_atr.calculate_levels("SELL", price, atr, regime)

print("\n========== DYNAMIC ATR ==========\n")
print(f"Price  : {price:.2f}")
print(f"ATR14  : {atr:.4f}")
print(f"Regime : {regime['regime']}")
print(f"Vol    : {regime['volatility']}")
print()
print(f"BUY  SL={sl_buy:.2f}  TP={tp_buy:.2f}")
print(f"SELL SL={sl_sell:.2f}  TP={tp_sell:.2f}")
