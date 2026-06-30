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