from backend.app.schemas.prediction import PredictionRequest
from backend.app.services.prediction_service import PredictionService

service = PredictionService()

request = PredictionRequest(
    symbol="BTCUSDT",
    interval="5m",
    lookback=400,
    prediction_length=24,
)

response = service.predict(request)

print(response.model_dump())