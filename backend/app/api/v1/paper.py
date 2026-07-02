import asyncio

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from backend.app.core.rate_limit import limiter, tier_rate_limit
from backend.app.schemas.paper import (
    ManualOrder,
    ManualOrderRequest,
    ManualPaperStatus,
    PaperStartRequest,
    PaperStatusResponse,
    PaperStopResponse,
)
from backend.app.services.paper.manual_paper_trader import ManualPaperFactory
from backend.app.services.paper.paper_trading_engine import PaperFactory

router = APIRouter(prefix="/paper", tags=["paper"])


@router.post("/start", response_model=PaperStatusResponse)
@limiter.limit(tier_rate_limit)
async def start_paper_trading(request: Request, req: PaperStartRequest) -> PaperStatusResponse:
    engine = PaperFactory.get_engine()
    try:
        engine.start(req)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return engine.status()


@router.post("/stop", response_model=PaperStopResponse)
def stop_paper_trading() -> PaperStopResponse:
    engine = PaperFactory.get_engine()
    if not engine.is_running:
        return PaperStopResponse(stopped=False, message="Paper trading not running")
    engine.stop()
    return PaperStopResponse(stopped=True, message="Paper trading stopped")


@router.get("/status", response_model=PaperStatusResponse)
def get_paper_status() -> PaperStatusResponse:
    engine = PaperFactory.get_engine()
    return engine.status()


@router.post("/order", response_model=ManualOrder)
@limiter.limit(tier_rate_limit)
async def place_manual_order(request: Request, req: ManualOrderRequest) -> ManualOrder:
    """One-click paper trade — open a virtual position from an explicit
    entry/stop_loss/take_profit. Auto-closes at SL or TP."""
    trader = ManualPaperFactory.get_trader()
    try:
        return trader.place(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders", response_model=ManualPaperStatus)
def get_manual_orders() -> ManualPaperStatus:
    return ManualPaperFactory.get_trader().status()


@router.websocket("/ws")
async def paper_status_ws(websocket: WebSocket) -> None:
    """Push live paper-trading status every 2s while the socket is open."""
    await websocket.accept()
    engine = PaperFactory.get_engine()
    try:
        while True:
            await websocket.send_json(engine.status().model_dump())
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()
