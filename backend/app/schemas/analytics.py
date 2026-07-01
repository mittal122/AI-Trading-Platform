from pydantic import BaseModel


class PortfolioAnalyticsResponse(BaseModel):

    initial_balance: float
    ending_balance: float
    total_return: float

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float

    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    max_drawdown: float
