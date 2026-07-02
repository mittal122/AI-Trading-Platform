from typing import Optional

from pydantic import BaseModel

from backend.app.schemas.paper import PaperPosition


class LiveStartRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "5m"
    strategy: str = "rsi"
    initial_balance: float = 10000.0
    dry_run: bool = True  # must explicitly set False for real orders


class LiveOrder(BaseModel):
    order_id: str
    side: str
    symbol: str
    quantity: float
    requested_price: float
    executed_price: float
    fee: float
    status: str
    timestamp: str
    is_dry_run: bool


class LiveStopResponse(BaseModel):
    stopped: bool
    emergency: bool
    orders_cancelled: int
    message: str


class LiveStatusResponse(BaseModel):
    is_running: bool
    emergency_stopped: bool
    dry_run: bool
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
    order_count: int
    recent_orders: list[LiveOrder]
    last_signal: Optional[str] = None
    last_price: Optional[float] = None
    candles_processed: int
