from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SignalDirection(str, Enum):

    BUY = "BUY"

    SELL = "SELL"

    FLAT = "FLAT"


class TradingSignal(BaseModel):

    strategy: str

    symbol: str

    interval: str

    timestamp: str

    direction: SignalDirection

    confidence: float

    entry: float

    stop_loss: float

    take_profit: float

    risk_reward: float

    reasons: list[str]

    # Phase 2 additions — optional for backward compatibility
    atr: Optional[float] = None

    regime: Optional[str] = None

    quality_score: Optional[float] = None

    quality_grade: Optional[str] = None

    explanation: Optional[str] = None

    # Estimated candles/time to reach take_profit — ATR-velocity heuristic,
    # helps a user judge whether this strategy suits this timeframe.
    eta_candles: Optional[int] = None

    eta_display: Optional[str] = None

    # Set only when this signal came from a batch scan and this particular
    # strategy/timeframe failed to compute — the rest of the batch still returns.
    error: Optional[str] = None