from pydantic import BaseModel


class HistoricalCandle(BaseModel):
    timestamp: str

    open: float
    high: float
    low: float
    close: float

    volume: float
    amount: float


class HistoricalMarketResponse(BaseModel):
    symbol: str
    interval: str

    candles: list[HistoricalCandle]