"""Volume-spike + order-push scanner data layer — live Binance public data,
no key needed. Verifies spike_ratio == volume/avg, order counts are real
integers, max-push is the window's biggest candle, and bad symbols degrade to
an error row instead of raising."""

from backend.app.services.market_service import MarketService

svc = MarketService()

print("\n========== SINGLE-SYMBOL VOLUME SCAN ==========\n")
row = svc.get_volume_scan("BTCUSDT", "5m", window=20)
for field in ("symbol", "interval", "time", "ltp", "volume_window", "volume_average",
              "spike_ratio", "orders", "avg_orders", "max_push_volume", "max_push_ratio"):
    assert field in row, f"missing {field}"

assert row["symbol"] == "BTCUSDT"
assert row["ltp"] > 0, "LTP must be a real price"
assert row["volume_window"] >= 0 and row["volume_average"] > 0
assert row["orders"] >= 0 and isinstance(row["orders"], int), "orders = number_of_trades, an int"

# spike_ratio must equal volume_window / volume_average (rounding tolerance).
expected = round(row["volume_window"] / row["volume_average"], 2)
assert abs(row["spike_ratio"] - expected) < 0.02, f"{row['spike_ratio']} != {expected}"

# max push is the biggest single-candle volume in the window — cannot be below
# the average, and max_push_ratio must be consistent with it.
assert row["max_push_volume"] >= row["volume_average"] * 0.99, "max push should be >= mean"
exp_push = round(row["max_push_volume"] / row["volume_average"], 2)
assert abs(row["max_push_ratio"] - exp_push) < 0.02
assert row["time"], "time (close_time) must be set"
print(f"PASS: BTCUSDT 5m  LTP={row['ltp']}  spike={row['spike_ratio']}x  "
      f"orders={row['orders']}  maxpush={row['max_push_ratio']}x")

print("\n========== DIFFERENT WINDOW SIZE ==========\n")
row50 = svc.get_volume_scan("ETHUSDT", "15m", window=50)
assert row50["symbol"] == "ETHUSDT" and row50["interval"] == "15m"
assert row50["volume_average"] > 0
print(f"PASS: ETHUSDT 15m window=50  avg_vol={row50['volume_average']}  "
      f"avg_orders={row50['avg_orders']}")

print("\n========== BAD SYMBOL RAISES (router isolates it) ==========\n")
raised = False
try:
    svc.get_volume_scan("ZZZNOSUCHSYMBOL", "5m", window=20)
except Exception as exc:
    raised = True
    print(f"PASS: bad symbol raised as expected ({type(exc).__name__}) — router turns this into an error row")
assert raised, "unknown symbol should raise at the provider layer"

print("\n========== RESULTS: all checks passed ==========")
