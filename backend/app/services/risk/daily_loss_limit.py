from datetime import date

from backend.app.core.strategy_config import strategy_config


class DailyLossLimit:
    """
    Tracks daily realized PnL.
    If daily loss exceeds DAILY_LOSS_LIMIT_PCT of day-start equity, halts trading for the day.
    Resets automatically on new calendar day.
    """

    def __init__(self):
        self.current_date: date | None = None
        self.day_start_equity: float = 0.0
        self.daily_realized_pnl: float = 0.0

    def _reset_if_new_day(self, equity: float) -> None:
        today = date.today()
        if self.current_date != today:
            self.current_date = today
            self.day_start_equity = equity
            self.daily_realized_pnl = 0.0

    def record_pnl(self, pnl: float) -> None:
        self.daily_realized_pnl += pnl

    def can_trade(self, equity: float) -> bool:
        self._reset_if_new_day(equity)
        if self.day_start_equity <= 0:
            return True
        daily_loss = -self.daily_realized_pnl
        limit = self.day_start_equity * strategy_config.DAILY_LOSS_LIMIT_PCT
        return daily_loss < limit

    def daily_loss_pct(self) -> float:
        if self.day_start_equity <= 0:
            return 0.0
        return (-self.daily_realized_pnl / self.day_start_equity) * 100

    def status(self, equity: float) -> dict:
        self._reset_if_new_day(equity)
        return {
            "date": str(self.current_date),
            "day_start_equity": self.day_start_equity,
            "daily_realized_pnl": round(self.daily_realized_pnl, 4),
            "daily_loss_pct": round(self.daily_loss_pct(), 2),
            "limit_pct": strategy_config.DAILY_LOSS_LIMIT_PCT * 100,
            "can_trade": self.can_trade(equity),
        }
