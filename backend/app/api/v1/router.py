from fastapi import APIRouter

from backend.app.api.v1.indicator import (
    router as indicator_router,
)
from backend.app.api.v1.market import (
    router as market_router,
)
from backend.app.api.v1.strategy import (
    router as strategy_router,
)

from backend.app.api.v1.prediction import (
    router as prediction_router,
)

api_router = APIRouter()

api_router.include_router(
    prediction_router
)

api_router.include_router(
    market_router
)

api_router.include_router(
    indicator_router
)   
api_router.include_router(
    strategy_router
)