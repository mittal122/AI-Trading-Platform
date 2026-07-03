from concurrent.futures import ThreadPoolExecutor

from backend.app.core.analysis_config import analysis_config
from backend.app.schemas.analysis_tool import AnalysisScanResponse, AnalysisToolResult
from backend.app.schemas.pattern import ChartAnnotations, PatternDirection
from backend.app.services.analysis.analysis_factory import AnalysisFactory
from backend.app.services.market_service import MarketService
from backend.app.services.pattern.pattern_utils import now_iso


class AnalysisScanner:
    """
    Runs the requested analysis tools concurrently against one market-data
    fetch. Deliberately has NO auto-AI (unlike PatternScanner) — AI here is
    on-demand only via AnalysisExplainer, one call synthesizing confluence
    across whichever tools are enabled, not one call per tool. This keeps
    scans fast (pure algorithmic work, sub-second) regardless of how many
    tools are toggled on.
    """

    def __init__(self):
        self.market = MarketService()

    def scan(self, symbol: str, interval: str, tool_keys: list[str] = None, limit: int = 300) -> AnalysisScanResponse:
        tool_keys = AnalysisFactory.list_tools() if tool_keys is None else tool_keys
        try:
            market = self.market.get_market_data(symbol=symbol, interval=interval, limit=limit)
        except Exception:
            return AnalysisScanResponse(symbol=symbol, interval=interval, tools=[], scanned_at=now_iso())

        with ThreadPoolExecutor(max_workers=analysis_config.ANALYSIS_SCAN_MAX_WORKERS) as pool:
            futures = [
                pool.submit(self._run_tool, key, market, symbol, interval) for key in tool_keys
            ]
            results = [f.result() for f in futures]

        return AnalysisScanResponse(symbol=symbol, interval=interval, tools=results, scanned_at=now_iso())

    @staticmethod
    def _run_tool(key: str, market, symbol: str, interval: str) -> AnalysisToolResult:
        try:
            tool = AnalysisFactory.get_tool(key)
            return tool.analyze(market, symbol, interval)
        except Exception as exc:
            return AnalysisToolResult(
                tool_key=key, tool_name=key, symbol=symbol, interval=interval,
                bias=PatternDirection.NEUTRAL, summary="Tool failed",
                annotations=ChartAnnotations(), last_updated=now_iso(), error=str(exc),
            )
