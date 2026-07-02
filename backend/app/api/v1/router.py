from fastapi import APIRouter

from backend.app.api.v1.ai import router as ai_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.billing import router as billing_router
from backend.app.api.v1.indicator import router as indicator_router
from backend.app.api.v1.live_trading import router as live_trading_router
from backend.app.api.v1.market import router as market_router
from backend.app.api.v1.paper import router as paper_router
from backend.app.api.v1.portfolio import router as portfolio_router
from backend.app.api.v1.prediction import router as prediction_router
from backend.app.api.v1.strategy import router as strategy_router
from backend.app.api.v1.trades import router as trades_router

api_router = APIRouter()

api_router.include_router(prediction_router)
api_router.include_router(market_router)
api_router.include_router(indicator_router)
api_router.include_router(strategy_router)
api_router.include_router(portfolio_router)
api_router.include_router(ai_router)
api_router.include_router(paper_router)
api_router.include_router(live_trading_router)
api_router.include_router(trades_router)
api_router.include_router(auth_router)
api_router.include_router(billing_router)