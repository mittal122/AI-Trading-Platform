from typing import Optional

from pydantic import BaseModel


class PaperStartRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "5m"
    strategy: str = "rsi"
    initial_balance: float = 10000.0


# ── Manual one-click paper order (place a trade from a displayed signal) ──────

class ManualOrderRequest(BaseModel):
    symbol: str
    strategy: str = "manual"
    direction: str = "BUY"           # BUY or SELL
    entry: float
    stop_loss: float
    take_profit: float
    risk_percent: float = 1.0
    interval: str = "1m"             # monitoring granularity


class ManualOrder(BaseModel):
    id: int
    symbol: str
    strategy: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    quantity: float
    status: str                      # OPEN or CLOSED
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    opened_at: str
    closed_at: Optional[str] = None


class ManualPaperStatus(BaseModel):
    balance: float
    equity: float
    realized_pnl: float
    open_count: int
    open_orders: list[ManualOrder]
    closed_orders: list[ManualOrder]


class PaperStopResponse(BaseModel):
    stopped: bool
    message: str


class PaperPosition(BaseModel):
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    current_price: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    candles_held: int


class PaperTrade(BaseModel):
    side: str
    price: float
    quantity: float
    pnl: float
    reason: str
    timestamp: str


class PaperStatusResponse(BaseModel):
    is_running: bool
    symbol: str
    interval: str
    strategy: str
    started_at: Optional[str] = None
    initial_balance: float
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    total_return: float
    open_position: Optional[PaperPosition] = None
    trade_count: int
    recent_trades: list[PaperTrade]
    last_signal: Optional[str] = None
    last_price: Optional[float] = None
    candles_processed: int
