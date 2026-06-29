from backend.app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    CandlePrediction,
)

from backend.app.services.market_service import MarketService
from backend.app.core.ai import kronos


class PredictionService:

    def __init__(self):
        self.market_service = MarketService()

    def predict(self, request: PredictionRequest) -> PredictionResponse:

        market_df = self.market_service.get_market_data(
            symbol=request.symbol,
            interval=request.interval,
            limit=request.lookback,
        )

        prediction_df = kronos.predictor.predict(
            df=market_df[
                [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "amount",
                ]
            ],
            x_timestamp=market_df["timestamps"],
            y_timestamp=kronos.create_future_timestamps(
                market_df["timestamps"],
                request.prediction_length,
            ),
            pred_len=request.prediction_length,
        )

        candles = []

        for timestamp, row in prediction_df.iterrows():

            candles.append(
                CandlePrediction(
                    timestamp=str(timestamp),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    amount=float(row["amount"]),
                )
            )

        return PredictionResponse(
            symbol=request.symbol,
            interval=request.interval,
            current_price=float(market_df.iloc[-1]["close"]),
            predictions=candles,
        )