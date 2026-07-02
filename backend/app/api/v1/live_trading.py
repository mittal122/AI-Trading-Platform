from fastapi import APIRouter, HTTPException, Request

from backend.app.core.rate_limit import limiter, tier_rate_limit
from backend.app.schemas.live_trading import (
    LiveStartRequest,
    LiveStatusResponse,
    LiveStopResponse,
)
from backend.app.services.trading.live_trading_engine import LiveTradingFactory

router = APIRouter(prefix="/trading", tags=["live-trading"])


@router.post("/start", response_model=LiveStatusResponse)
@limiter.limit(tier_rate_limit)
async def start_live_trading(request: Request, req: LiveStartRequest) -> LiveStatusResponse:
    engine = LiveTradingFactory.get_engine()
    try:
        engine.start(req)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return engine.status()


@router.post("/stop", response_model=LiveStopResponse)
async def stop_live_trading(emergency: bool = False) -> LiveStopResponse:
    engine = LiveTradingFactory.get_engine()
    if not engine.is_running and not emergency:
        return LiveStopResponse(
            stopped=False,
            emergency=False,
            orders_cancelled=0,
            message="Live trading not running",
        )
    result = await engine.stop(emergency=emergency)
    return LiveStopResponse(
        stopped=True,
        emergency=emergency,
        orders_cancelled=result["orders_cancelled"],
        message="Emergency stop executed" if emergency else "Live trading stopped",
    )


@router.get("/status", response_model=LiveStatusResponse)
def get_live_status() -> LiveStatusResponse:
    return LiveTradingFactory.get_engine().status()
