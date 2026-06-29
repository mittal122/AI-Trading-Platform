from fastapi import APIRouter

from backend.app.api.v1.prediction import router as prediction_router

api_router = APIRouter()

api_router.include_router(
    prediction_router
)