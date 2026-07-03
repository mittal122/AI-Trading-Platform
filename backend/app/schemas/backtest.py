from typing import Optional

from pydantic import BaseModel


class TradeResult(BaseModel):

    entry_price: float

    exit_price: float

    quantity: float

    pnl: float

    return_percent: float

    # Duration tracking — how long the trade actually took to resolve
    entry_timestamp: str = ""

    exit_timestamp: str = ""

    candles_held: int = 0

    exit_reason: str = ""


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

    # How long winning trades took to reach target — the empirical answer to
    # "does this strategy suit this timeframe" (candles_held x interval length)
    avg_candles_to_win: Optional[float] = None

    avg_time_to_win_display: Optional[str] = None
