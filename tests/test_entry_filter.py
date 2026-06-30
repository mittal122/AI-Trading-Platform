from backend.app.services.market_service import MarketService
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.entry_filter import EntryFilter

market = MarketService()
indicator = IndicatorService()
entry_filter = EntryFilter()

df = market.get_market_data(symbol="BTCUSDT", interval="5m", limit=250)
values = indicator.calculate_from_dataframe(df)

buy_valid, buy_failed = entry_filter.check_buy(values)
sell_valid, sell_failed = entry_filter.check_sell(values)

print("\n========== ENTRY FILTER ==========\n")
print(f"BUY  valid : {buy_valid}  | failed: {buy_failed}")
print(f"SELL valid : {sell_valid} | failed: {sell_failed}")
