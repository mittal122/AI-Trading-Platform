from backend.app.core.strategy_config import strategy_config


class DrawdownGuard:
    """
    Tracks peak equity and enforces drawdown limits.
    HALT  — drawdown >= DRAWDOWN_HALT_PCT (10%):   no new trades
    CLOSE_ALL — drawdown >= DRAWDOWN_CLOSE_ALL_PCT (20%): close all + halt
    """

    def __init__(self):
        self.peak_equity: float = 0.0

    def update(self, equity: float) -> None:
        if equity > self.peak_equity:
            self.peak_equity = equity

    def current_drawdown(self, equity: float) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - equity) / self.peak_equity

    def check(self, equity: float) -> tuple[bool, str]:
        """
        Returns (can_open_new_trade, action).
        action: "" | "HALT" | "CLOSE_ALL"
        """
        self.update(equity)
        dd = self.current_drawdown(equity)

        if dd >= strategy_config.DRAWDOWN_CLOSE_ALL_PCT:
            return False, "CLOSE_ALL"

        if dd >= strategy_config.DRAWDOWN_HALT_PCT:
            return False, "HALT"

        return True, ""

    def status(self, equity: float) -> dict:
        self.update(equity)
        dd = self.current_drawdown(equity)
        return {
            "peak_equity": self.peak_equity,
            "current_equity": equity,
            "drawdown_pct": round(dd * 100, 2),
            "halt_threshold_pct": strategy_config.DRAWDOWN_HALT_PCT * 100,
            "close_all_threshold_pct": strategy_config.DRAWDOWN_CLOSE_ALL_PCT * 100,
        }
