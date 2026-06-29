from fastapi import APIRouter

from backend.app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
)

from backend.app.services.prediction_service import (
    PredictionService,
)

router = APIRouter(
    prefix="/prediction",
    tags=["Prediction"],
)

prediction_service = PredictionService()


@router.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(
    request: PredictionRequest,
):

    return prediction_service.predict(request)