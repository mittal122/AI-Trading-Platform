from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.analysis_tool import AnalysisExplainRequest, AnalysisExplainResponse, AnalysisScanResponse
from backend.app.services.analysis.analysis_factory import AnalysisFactory
from backend.app.services.analysis.analysis_scanner import AnalysisScanner

router = APIRouter(prefix="/analysis", tags=["Analysis Tools"])

scanner = AnalysisScanner()


@router.get("/available")
def list_available_tools():
    """Registered analysis tool keys — single source of truth for the frontend toggle bar."""
    return {"tools": AnalysisFactory.list_tools()}


@router.get("/scan", response_model=AnalysisScanResponse)
def scan_analysis_tools(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    tools: str = Query(default=None, description="Comma-separated tool keys. Defaults to all registered tools."),
    limit: int = Query(default=300, ge=50, le=2000),
):
    """
    Every requested tool computed algorithmically — no AI, fast (sub-second),
    safe to call on every toggle/timeframe change.
    """
    tool_keys = [t.strip() for t in tools.split(",") if t.strip()] if tools else None
    return scanner.scan(symbol=symbol, interval=interval, tool_keys=tool_keys, limit=limit)


@router.post("/explain", response_model=AnalysisExplainResponse)
def explain_analysis(req: AnalysisExplainRequest):
    """
    On-demand only — one AI call synthesizing confluence across whichever
    tools are enabled, not one call per tool. Triggered by a user action
    (e.g. clicking "AI Analysis"), never automatically.
    """
    result = scanner.scan(symbol=req.symbol, interval=req.interval, tool_keys=req.tool_keys, limit=req.limit)

    try:
        from backend.app.services.ai.analysis_explainer import AnalysisExplainer
        explainer = AnalysisExplainer()
        explanation = explainer.explain(req.symbol, req.interval, result.tools)
    except RuntimeError as exc:
        # Config-not-set message (e.g. NVIDIA_API_KEY missing) — safe/useful.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="AI analysis failed")

    return AnalysisExplainResponse(
        symbol=req.symbol, interval=req.interval, tool_keys=req.tool_keys,
        explanation=explanation, tools=result.tools,
    )
