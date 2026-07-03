from fastapi import APIRouter, Query

from backend.app.schemas.pattern import PatternDashboardResponse, PatternScanResponse
from backend.app.services.pattern.pattern_factory import PatternFactory
from backend.app.services.pattern.pattern_scanner import PatternScanner

router = APIRouter(prefix="/patterns", tags=["Patterns"])

scanner = PatternScanner()


@router.get("/available")
def list_available_detectors():
    """Registered pattern-detector families — single source of truth for the frontend."""
    return {"detectors": PatternFactory.list_detectors()}


@router.get("/scan", response_model=PatternScanResponse)
def scan_patterns(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    limit: int = Query(default=300, ge=50, le=1000),
):
    """
    Every registered pattern detector + FVG, run against one symbol/interval.
    Each detected pattern that clears the confidence floor gets an
    AI-generated explanation attached automatically.
    """
    return scanner.scan(symbol=symbol, interval=interval, limit=limit)


@router.get("/multi-timeframe", response_model=list[PatternScanResponse])
def scan_patterns_multi_timeframe(
    symbol: str = Query(default="BTCUSDT"),
    intervals: str = Query(
        default=None,
        description="Comma-separated intervals, e.g. '1m,5m,15m,1h,4h,1d,1w'. Defaults to the platform's standard scan set.",
    ),
    limit: int = Query(default=300, ge=50, le=1000),
):
    """One symbol, every timeframe analyzed independently — patterns and FVGs per timeframe."""
    interval_list = [i.strip() for i in intervals.split(",") if i.strip()] if intervals else None
    return scanner.scan_multi_timeframe(symbol=symbol, intervals=interval_list, limit=limit)


@router.get("/dashboard", response_model=PatternDashboardResponse)
def pattern_dashboard(
    symbol: str = Query(default="BTCUSDT"),
    intervals: str = Query(default=None, description="Comma-separated intervals, defaults to the standard scan set."),
    limit: int = Query(default=300, ge=50, le=1000),
):
    """Flattened, confidence-sorted table of every active pattern across timeframes for one symbol."""
    interval_list = [i.strip() for i in intervals.split(",") if i.strip()] if intervals else None
    return scanner.dashboard(symbol=symbol, intervals=interval_list, limit=limit)
