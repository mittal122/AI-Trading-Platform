from backend.app.services.trade.exit_manager import ExitManager


class TradeManager:

    def __init__(self):
        self.exit_manager = ExitManager()
        self.last_exit_reason = ""
        self.last_exit_price = 0.0

    def should_exit(
        self,
        signal,
        portfolio,
        trade,
        atr: float = 0.0,
        high: float = None,
        low: float = None,
    ) -> bool:

        if portfolio.position_quantity <= 0:
            return False

        if trade is None:
            return False

        price = signal.entry
        direction = signal.direction.value

        should_exit, reason, exit_price = self.exit_manager.check_exit(
            price=price,
            signal_direction=direction,
            trade=trade,
            atr=atr,
            high=high,
            low=low,
        )

        if should_exit:
            self.last_exit_reason = reason
            self.last_exit_price = exit_price
            print(f"EXIT | Reason: {reason} | Price: {exit_price:.2f}")

        return should_exit
