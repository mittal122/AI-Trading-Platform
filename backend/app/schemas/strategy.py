from pydantic import BaseModel


class StrategyResponse(BaseModel):

    strategy: str

    symbol: str
    interval: str

    signal: str

    confidence: float

    entry: float
    stop_loss: float
    take_profit: float

    risk_reward: float

    reasons: list[str]