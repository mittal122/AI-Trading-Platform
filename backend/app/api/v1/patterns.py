from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.pattern import AIPatternExplanation, DetectedPattern, PatternDashboardResponse, PatternScanResponse
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
    include_ai: bool = Query(
        default=False,
        description="Auto-generate an AI explanation for every pattern found. Slow with "
                    "many patterns (sequential AI calls) — prefer POST /patterns/explain "
                    "for the one pattern a user actually selects.",
    ),
):
    """
    Every registered pattern detector + FVG, run against one symbol/interval.
    Fast and algorithmic-only by default (sub-second even at 1000 candles) —
    pass include_ai=true to also auto-generate AI for every result found.
    """
    return scanner.scan(symbol=symbol, interval=interval, limit=limit, include_ai=include_ai)


@router.post("/explain", response_model=AIPatternExplanation)
def explain_pattern(pattern: DetectedPattern):
    """On-demand AI explanation for exactly one pattern — call this for whichever
    pattern a user has actually selected, not for every pattern in a scan."""
    try:
        explanation = scanner.explain_pattern(pattern)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {exc}")
    if explanation.error and "not configured" in explanation.error:
        raise HTTPException(status_code=503, detail=explanation.error)
    return explanation


@router.get("/multi-timeframe", response_model=list[PatternScanResponse])
def scan_patterns_multi_timeframe(
    symbol: str = Query(default="BTCUSDT"),
    intervals: str = Query(
        default=None,
        description="Comma-separated intervals, e.g. '1m,5m,15m,1h,4h,1d,1w'. Defaults to the platform's standard scan set.",
    ),
    limit: int = Query(default=300, ge=50, le=1000),
    include_ai: bool = Query(default=False, description="See GET /patterns/scan — same tradeoff, multiplied across timeframes."),
):
    """One symbol, every timeframe analyzed independently — patterns and FVGs per timeframe."""
    interval_list = [i.strip() for i in intervals.split(",") if i.strip()] if intervals else None
    return scanner.scan_multi_timeframe(symbol=symbol, intervals=interval_list, limit=limit, include_ai=include_ai)


@router.get("/dashboard", response_model=PatternDashboardResponse)
def pattern_dashboard(
    symbol: str = Query(default="BTCUSDT"),
    intervals: str = Query(default=None, description="Comma-separated intervals, defaults to the standard scan set."),
    limit: int = Query(default=300, ge=50, le=1000),
):
    """Flattened, confidence-sorted table of every active pattern across timeframes for one symbol."""
    interval_list = [i.strip() for i in intervals.split(",") if i.strip()] if intervals else None
    return scanner.dashboard(symbol=symbol, intervals=interval_list, limit=limit)
