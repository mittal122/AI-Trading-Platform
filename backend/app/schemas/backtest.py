from pydantic import BaseModel


class TradeResult(BaseModel):

    entry_price: float

    exit_price: float

    quantity: float

    pnl: float

    return_percent: float


class EquityPoint(BaseModel):

    candle: int

    timestamp: str

    equity: float


class BacktestResult(BaseModel):

    initial_balance: float

    ending_balance: float

    total_return: float

    total_trades: int

    winning_trades: int

    losing_trades: int

    win_rate: float

    trades: list[TradeResult]

    equity_curve: list[EquityPoint]