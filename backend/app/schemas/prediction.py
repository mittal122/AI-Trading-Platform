from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):

    symbol: str = Field(
        default="BTCUSDT",
        description="Trading Symbol",
    )

    interval: str = Field(
        default="5m",
        description="Market Interval",
    )

    lookback: int = Field(
        default=400,
        ge=50,
        le=512,
    )

    prediction_length: int = Field(
        default=24,
        ge=1,
        le=120,
    )


class CandlePrediction(BaseModel):

    timestamp: str

    open: float

    high: float

    low: float

    close: float

    volume: float

    amount: float


class PredictionResponse(BaseModel):

    symbol: str

    interval: str

    current_price: float

    predictions: list[CandlePrediction]