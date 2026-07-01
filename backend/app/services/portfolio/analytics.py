import math

from backend.app.schemas.analytics import PortfolioAnalyticsResponse
from backend.app.schemas.backtest import EquityPoint, TradeResult


class PortfolioAnalytics:

    def __init__(self, risk_free_rate: float = 0.0):
        self.risk_free_rate = risk_free_rate

    def compute(
        self,
        trades: list[TradeResult],
        equity_curve: list[EquityPoint],
        initial_balance: float,
    ) -> PortfolioAnalyticsResponse:

        n = len(trades)
        ending_balance = equity_curve[-1].equity if equity_curve else initial_balance
        total_return = ((ending_balance - initial_balance) / initial_balance) * 100

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]

        win_rate = (len(wins) / n * 100) if n > 0 else 0.0
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
        avg_loss = abs(sum(t.pnl for t in losses) / len(losses)) if losses else 0.0

        gross_wins = sum(t.pnl for t in wins)
        gross_losses = abs(sum(t.pnl for t in losses))
        profit_factor = (
            gross_wins / gross_losses if gross_losses > 0 else float("inf")
        )

        wr = win_rate / 100
        expectancy = (wr * avg_win) - ((1 - wr) * avg_loss) if n > 0 else 0.0

        returns = [t.return_percent / 100 for t in trades]
        sharpe = self._sharpe(returns)
        sortino = self._sortino(returns)

        max_dd = self._max_drawdown(equity_curve)
        calmar = (total_return / 100) / max_dd if max_dd > 0 else 0.0

        return PortfolioAnalyticsResponse(
            initial_balance=initial_balance,
            ending_balance=round(ending_balance, 4),
            total_return=round(total_return, 4),
            total_trades=n,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=round(win_rate, 2),
            avg_win=round(avg_win, 4),
            avg_loss=round(avg_loss, 4),
            profit_factor=round(profit_factor, 4),
            expectancy=round(expectancy, 4),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            calmar_ratio=round(calmar, 4),
            max_drawdown=round(max_dd * 100, 4),
        )

    def _sharpe(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std_r = math.sqrt(variance)
        if std_r == 0:
            return 0.0
        return (mean_r - self.risk_free_rate) / std_r * math.sqrt(len(returns))

    def _sortino(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        downside = [r for r in returns if r < 0]
        if not downside:
            return 0.0
        downside_variance = sum(r**2 for r in downside) / len(downside)
        downside_std = math.sqrt(downside_variance)
        if downside_std == 0:
            return 0.0
        return (mean_r - self.risk_free_rate) / downside_std * math.sqrt(len(returns))

    def _max_drawdown(self, equity_curve: list[EquityPoint]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0].equity
        max_dd = 0.0
        for point in equity_curve:
            if point.equity > peak:
                peak = point.equity
            dd = (peak - point.equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd
