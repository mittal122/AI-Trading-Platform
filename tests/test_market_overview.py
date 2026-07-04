"""Market-overview data layer — 24h tickers (cached), depth pressure,
taker buy pressure, funding. Live Binance public data, no key needed."""

import time

from backend.app.services.market_service import MarketService

svc = MarketService()

print("\n========== 24H TICKERS + CACHE ==========\n")
t0 = time.time()
tickers = svc.get_tickers_24h()
first_call = time.time() - t0
assert len(tickers) > 100, f"expected hundreds of USDT pairs, got {len(tickers)}"
sample = tickers[0]
for field in ("symbol", "last_price", "price_change_pct", "high", "low", "quote_volume", "trades"):
    assert field in sample, f"missing {field}"
assert all(t["symbol"].endswith("USDT") for t in tickers[:50])
assert not any(t["symbol"].endswith(("UPUSDT", "DOWNUSDT")) for t in tickers), "leveraged tokens must be filtered"
t0 = time.time()
svc.get_tickers_24h()
second_call = time.time() - t0
assert second_call < first_call / 2 or second_call < 0.05, (
    f"second call should hit the cache (first {first_call:.2f}s, second {second_call:.2f}s)"
)
print(f"PASS: {len(tickers)} USDT tickers; cache works ({first_call:.2f}s -> {second_call:.3f}s)")

print("\n========== DEPTH PRESSURE ==========\n")
depth = svc.get_depth_summary("BTCUSDT", limit=100)
assert 0.0 <= depth["bid_ratio"] <= 1.0
assert depth["best_bid"] < depth["best_ask"], "book must not be crossed"
assert depth["biggest_bid_wall_notional"] > 0 and depth["biggest_ask_wall_notional"] > 0
print(f"PASS: bid_ratio={depth['bid_ratio']}, best bid/ask {depth['best_bid']}/{depth['best_ask']}")

print("\n========== TAKER BUY PRESSURE ==========\n")
bp = svc.get_buy_pressure("BTCUSDT", "5m", limit=20)
assert 0.0 <= bp["buy_ratio"] <= 1.0
assert len(bp["recent_ratios"]) == 10
assert all(0.0 <= r <= 1.0 for r in bp["recent_ratios"])
print(f"PASS: buy_ratio={bp['buy_ratio']} over {bp['candles']} candles")

print("\n========== FUNDING ==========\n")
funding = svc.get_funding("BTCUSDT")
if funding is None:
    print("SKIP: futures data unreachable in this environment (endpoint degrades to null by design)")
else:
    assert -0.05 < funding["funding_rate"] < 0.05, "funding rate should be a small fraction"
    assert funding["mark_price"] > 0
    print(f"PASS: funding_rate={funding['funding_rate']} ({funding['funding_rate_annualized_pct']}% annualized)")

# A symbol with no perp market must degrade to None, not raise.
no_perp = svc.get_funding("ZZZNOPERPUSDT")
assert no_perp is None
print("PASS: unknown symbol degrades to None")

print("\n========== RESULTS: all checks passed ==========")
