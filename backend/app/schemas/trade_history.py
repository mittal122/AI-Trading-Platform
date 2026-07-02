from typing import Optional

from pydantic import BaseModel


class TradeHistoryItem(BaseModel):
    id: int
    symbol: str
    strategy: str
    direction: str
    mode: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    exit_reason: str
    entry_timestamp: str
    exit_timestamp: str
    created_at: str

    model_config = {"from_attributes": True}


class TradeHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    trades: list[TradeHistoryItem]


class BacktestRunItem(BaseModel):
    id: int
    strategy: str
    symbol: str
    interval: str
    limit: int
    initial_balance: float
    final_balance: float
    total_return: float
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    created_at: str

    model_config = {"from_attributes": True}


class BacktestHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    runs: list[BacktestRunItem]


class DeleteResponse(BaseModel):
    deleted: int


class SaveTradeRequest(BaseModel):
    symbol: str
    strategy: str
    direction: str = "BUY"
    mode: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    exit_reason: str = ""
    entry_timestamp: str = ""
    exit_timestamp: str = ""
