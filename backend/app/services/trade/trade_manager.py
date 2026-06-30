from backend.app.services.trade.exit_manager import ExitManager


class TradeManager:

    def __init__(self):
        self.exit_manager = ExitManager()
        self.last_exit_reason = ""

    def should_exit(
        self,
        signal,
        portfolio,
        trade,
        atr: float = 0.0,
    ) -> bool:

        if portfolio.position_quantity <= 0:
            return False

        if trade is None:
            return False

        price = signal.entry
        direction = signal.direction.value

        should_exit, reason = self.exit_manager.check_exit(
            price=price,
            signal_direction=direction,
            trade=trade,
            atr=atr,
        )

        if should_exit:
            self.last_exit_reason = reason
            print(f"EXIT | Reason: {reason} | Price: {price:.2f}")

        return should_exit
