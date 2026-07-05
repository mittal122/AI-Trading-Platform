"""SMC analysis API.

Public endpoints (open by default, like /patterns) exposing the SMC engine.
The live analysis path fetches an order-flow snapshot (atr=0 band, per §8) and
feeds it into the pipeline so the per-side confluence can use order flow.
"""

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import AnalysisRequest, AnalysisResult
from backend.app.services.market_service import MarketService
from backend.app.services.smc.order_flow import fetch_order_flow
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
    limit: int = Query(default=smc_config.DEFAULT_CANDLES, ge=smc_config.MIN_CANDLES, le=1500),
) -> AnalysisResult:
    """Path-parameter form of POST /smc/analyze."""
    return _run_analysis(symbol, interval, limit)
