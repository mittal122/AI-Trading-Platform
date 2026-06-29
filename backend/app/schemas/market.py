from pydantic import BaseModel


class LiveMarketResponse(BaseModel):
    symbol: str
    interval: str
    timestamp: str

    open: float
    high: float
    low: float
    close: float

    volume: float
    amount: float