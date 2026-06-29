from pydantic import BaseModel


class IndicatorValues(BaseModel):
    price: float

    sma20: float
    ema20: float

    rsi14: float

    macd: float
    signal: float
    histogram: float

    bb_upper: float
    bb_middle: float
    bb_lower: float

    atr14: float

    vwap: float


class IndicatorResponse(BaseModel):
    symbol: str
    interval: str
    indicators: IndicatorValues