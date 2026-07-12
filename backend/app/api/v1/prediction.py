from fastapi import APIRouter, HTTPException

from backend.app.core.ai import kronos

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

# Created on first request, not at import — instantiating PredictionService
# loads the Kronos model, which must not happen when KRONOS_ENABLED=false.
_prediction_service: PredictionService | None = None


@router.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(
    request: PredictionRequest,
):
    if kronos is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Prediction is disabled on this deployment — "
                "set KRONOS_ENABLED=true (requires torch + the Kronos repo)."
            ),
        )
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service.predict(request)
