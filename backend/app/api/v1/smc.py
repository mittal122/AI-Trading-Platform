"""SMC analysis API.

Public endpoints (open by default, like /patterns) exposing the SMC engine.
The live analysis path fetches an order-flow snapshot (atr=0 band, per §8) and
feeds it into the pipeline so the per-side confluence can use order flow.
"""

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import (
    AcceptSignalRequest, AddWatchRequest, AnalysisRequest, AnalysisResult, AutoTestStartRequest,
    BacktestRequest, BacktestResult, ScannerSettings, SignalOut, WatchItem,
)
from backend.app.services.market_service import MarketService
from backend.app.services.smc.backtest import run_backtest
from backend.app.services.smc.order_flow import fetch_order_flow
from backend.app.services.smc.auto_tester import auto_tester
from backend.app.services.smc.scanner import scanner_service
from backend.app.services.smc.smc_engine import analyze

router = APIRouter(prefix="/smc", tags=["SMC"])

_market = MarketService()


@router.get("/health")
def smc_health() -> dict:
    """Liveness check for the SMC section — confirms the router is registered."""
    return {"status": "ok", "engine": "smc", "phase": "A"}


def _run_analysis(symbol: str, interval: str, limit: int) -> AnalysisResult:
    if interval not in _market.get_supported_intervals():
        raise HTTPException(status_code=400, detail=f"Unsupported interval '{interval}'")
    try:
        df = _market.get_market_data(symbol, interval, limit)
    except Exception as exc:  # noqa: BLE001 — surface a clean 400 on bad symbol/data
        raise HTTPException(status_code=400, detail=f"Market data error: {exc}") from exc

    if df is None or len(df) < smc_config.MIN_CANDLES:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough candles ({0 if df is None else len(df)} < {smc_config.MIN_CANDLES})",
        )

    price = float(df["close"].iloc[-1])
    try:
        order_flow = fetch_order_flow(_market, symbol, atr=0.0, price=price)
    except Exception:  # noqa: BLE001 — order flow is optional; analysis still returns
        order_flow = None

    return analyze(symbol, interval, df, order_flow=order_flow)


@router.post("/analyze", response_model=AnalysisResult)
def smc_analyze(req: AnalysisRequest) -> AnalysisResult:
    """Run the full SMC pipeline; returns candles + all detections + scores +
    verdict + both trade plans + order flow. 400 if fewer than the minimum
    candles are available."""
    return _run_analysis(req.symbol, req.interval, req.limit)


@router.get("/analyze/{symbol}/{interval}", response_model=AnalysisResult)
def smc_analyze_get(
    symbol: str, interval: str,
    limit: int = Query(default=smc_config.DEFAULT_CANDLES, ge=smc_config.MIN_CANDLES, le=2000),
) -> AnalysisResult:
    """Path-parameter form of POST /smc/analyze."""
    return _run_analysis(symbol, interval, limit)


@router.post("/backtest", response_model=BacktestResult)
def smc_backtest(req: BacktestRequest) -> BacktestResult:
    """Walk-forward replay of the SMC strategy over historical candles."""
    if req.capital <= 0:
        raise HTTPException(status_code=400, detail="capital must be > 0")
    if not (0 < req.risk_pct <= 100):
        raise HTTPException(status_code=400, detail="risk_pct must be in (0, 100]")
    if req.interval not in _market.get_supported_intervals():
        raise HTTPException(status_code=400, detail=f"Unsupported interval '{req.interval}'")
    try:
        df = _market.get_market_data(req.symbol, req.interval, req.limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Market data error: {exc}") from exc
    if df is None or len(df) < 100:
        raise HTTPException(status_code=400, detail="Need at least 100 candles to backtest")
    return run_backtest(req.symbol, req.interval, df, req.capital, req.risk_pct,
                        req.max_trades, req.cooldown)


# --------------------------------------------------------------------------- #
# Signal scanner (§13) — single-operator/global watchlist + settings + signals
# --------------------------------------------------------------------------- #
@router.get("/watchlist", response_model=list[WatchItem])
async def smc_watchlist() -> list[WatchItem]:
    return await scanner_service.list_watches()


@router.post("/watchlist", response_model=WatchItem, status_code=status.HTTP_201_CREATED)
async def smc_add_watch(req: AddWatchRequest) -> WatchItem:
    if req.interval not in _market.get_supported_intervals():
        raise HTTPException(status_code=400, detail=f"Unsupported interval '{req.interval}'")
    return await scanner_service.add_watch(req.symbol, req.interval)


@router.patch("/watchlist/{watch_id}")
async def smc_toggle_watch(watch_id: int, active: bool = Query(...)) -> dict:
    if not await scanner_service.set_active(watch_id, active):
        raise HTTPException(status_code=404, detail="Watch not found")
    return {"id": watch_id, "active": active}


@router.delete("/watchlist/{watch_id}")
async def smc_remove_watch(watch_id: int) -> dict:
    if not await scanner_service.remove_watch(watch_id):
        raise HTTPException(status_code=404, detail="Watch not found")
    return {"deleted": watch_id}


@router.get("/scanner/settings", response_model=ScannerSettings)
async def smc_get_settings() -> ScannerSettings:
    return await scanner_service.get_settings()


@router.put("/scanner/settings", response_model=ScannerSettings)
async def smc_update_settings(settings: ScannerSettings) -> ScannerSettings:
    return await scanner_service.update_settings(settings.enabled, settings.max_signals_per_week)


@router.post("/scanner/scan")
async def smc_scan_now() -> dict:
    """Trigger one scan sweep immediately (the scheduler also runs it every 60s)."""
    return await scanner_service.scan_once()


@router.get("/signals", response_model=list[SignalOut])
async def smc_signals(limit: int = Query(default=100, ge=1, le=500)) -> list[SignalOut]:
    return await scanner_service.list_signals(limit)


@router.post("/signals/{signal_id}/accept", response_model=SignalOut)
async def smc_accept_signal(signal_id: int, req: AcceptSignalRequest) -> SignalOut:
    try:
        return await scanner_service.accept(signal_id, req.capital, req.risk_pct)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/signals/{signal_id}/dismiss", response_model=SignalOut)
async def smc_dismiss_signal(signal_id: int) -> SignalOut:
    try:
        return await scanner_service.dismiss(signal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Auto-test — hands-free paper-trading loop (re-analyze every candle close,
# trade the stronger side, flip on reversal)
# --------------------------------------------------------------------------- #

@router.post("/autotest/start")
async def smc_autotest_start(req: AutoTestStartRequest) -> dict:
    if req.interval not in _market.get_supported_intervals():
        raise HTTPException(status_code=400, detail=f"Unsupported interval '{req.interval}'")
    if not (0.1 <= req.risk_percent <= 5.0):
        raise HTTPException(status_code=400, detail="risk_percent must be 0.1-5.0")
    try:
        auto_tester.start(req.symbol, req.interval, req.risk_percent,
                          req.min_score, req.flip_margin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return auto_tester.status()


@router.post("/autotest/stop")
async def smc_autotest_stop() -> dict:
    try:
        auto_tester.stop()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return auto_tester.status()


@router.get("/autotest/status")
async def smc_autotest_status() -> dict:
    return auto_tester.status()
