from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.api.deps import require_admin
from backend.app.core.rate_limit import limiter, tier_rate_limit
from backend.app.schemas.live_trading import (
    LiveStartRequest,
    LiveStatusResponse,
    LiveStopResponse,
)
from backend.app.services.db_service import DatabaseService
from backend.app.services.trading.live_trading_engine import LiveTradingFactory

router = APIRouter(prefix="/trading", tags=["live-trading"])


# Starting/stopping REAL-money trading is admin-gated (open on localhost,
# locked when ADMIN_API_TOKEN is set) — anonymous callers must never be able
# to open live positions on a deployed instance.
@router.post("/start", response_model=LiveStatusResponse, dependencies=[Depends(require_admin)])
@limiter.limit(tier_rate_limit)
async def start_live_trading(request: Request, req: LiveStartRequest) -> LiveStatusResponse:
    engine = LiveTradingFactory.get_engine()
    api_key = api_secret = None
    if not req.dry_run:
        creds = await DatabaseService().get_exchange_credentials()
        if creds:
            api_key, api_secret = creds
    try:
        engine.start(req, api_key=api_key, api_secret=api_secret)
    except RuntimeError as e:
        # RuntimeError here carries an intentional operator message
        # ("already running" / "halted by emergency stop") — safe to surface.
        raise HTTPException(status_code=409, detail=str(e))
    return engine.status()


@router.post("/stop", response_model=LiveStopResponse, dependencies=[Depends(require_admin)])
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
