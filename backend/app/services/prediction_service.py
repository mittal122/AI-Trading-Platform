from backend.app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    CandlePrediction,
)

from backend.app.services.market_service import MarketService
from backend.app.core.ai import kronos


class PredictionService:
    """
    Orchestrates the complete prediction pipeline.

    Flow:
    Client Request
        ↓
    Fetch Market Data
        ↓
    Run Kronos Prediction
        ↓
    Build API Response
    """

    def __init__(self):
        self.market = MarketService()

        # Load Kronos automatically if it has not been loaded yet.
        if not kronos.is_loaded():
            kronos.load()

    def predict(
        self,
        request: PredictionRequest,
    ) -> PredictionResponse:

        # Fetch historical market data
        market_df = self.market.get_market_data(
            symbol=request.symbol,
            interval=request.interval,
            limit=request.lookback,
        )

        # Generate AI prediction
        prediction_df = kronos.predict(
            df=market_df,
            pred_len=request.prediction_length,
        )

        candles = []

        for timestamp, row in prediction_df.iterrows():

            candles.append(
                CandlePrediction(
                    timestamp=timestamp.isoformat(),
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
            current_price=float(
                market_df.iloc[-1]["close"]
            ),
            predictions=candles,
        )