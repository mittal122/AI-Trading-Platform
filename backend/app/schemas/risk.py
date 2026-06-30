from enum import Enum

from pydantic import BaseModel


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class RiskResponse(BaseModel):

    direction: Direction

    entry: float

    stop_loss: float

    take_profit: float

    risk_per_unit: float

    reward_per_unit: float

    risk_reward: float