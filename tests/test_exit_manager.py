from backend.app.services.trade.exit_manager import ExitManager
from backend.app.services.trade.trade_state import TradeState

exit_manager = ExitManager()

trade = TradeState(
    entry_price=60000.0,
    stop_loss=59500.0,
    take_profit=61500.0,
    quantity=0.01,
    entry_timestamp="2024-01-01T00:00:00",
    peak_price=60000.0,
    atr_at_entry=300.0,
)

test_cases = [
    (60200.0, "FLAT",  "Normal hold"),
    (60600.0, "BUY",   "Price rising (trailing activates)"),
    (60900.0, "BUY",   "Continued rise"),
    (61600.0, "BUY",   "Above take profit"),
    (59400.0, "FLAT",  "Stop loss hit"),
    (60000.0, "SELL",  "Signal reversal"),
]

print("\n========== EXIT MANAGER ==========\n")

for price, direction, label in test_cases:
    # Reset trade for each test
    t = TradeState(
        entry_price=60000.0,
        stop_loss=59500.0,
        take_profit=61500.0,
        quantity=0.01,
        entry_timestamp="2024-01-01T00:00:00",
        peak_price=60000.0,
        atr_at_entry=300.0,
    )
    should_exit, reason, exit_price = exit_manager.check_exit(
        price=price,
        signal_direction=direction,
        trade=t,
        atr=300.0,
    )
    print(f"{label:<35} price={price}  exit={should_exit}  reason={reason}  fill={exit_price}")
