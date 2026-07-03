import time
from concurrent.futures import ThreadPoolExecutor

import openai

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import (
    AIPatternExplanation, DetectedPattern, PatternDashboardResponse,
    PatternDashboardRow, PatternScanResponse,
)
from backend.app.services.market_service import MarketService
from backend.app.services.pattern.fvg_detector import FVGDetector
from backend.app.services.pattern.pattern_factory import PatternFactory
from backend.app.services.pattern.pattern_utils import now_iso


class PatternScanner:
    """
    Orchestrates the pattern module. Every registered detector runs
    concurrently against a single market-data fetch (detection itself is
    fast, pure-CPU geometry — the fetch dominates, confirmed sub-3s even at
    1000 candles).

    AI explanation is OPT-IN per call (`include_ai=False` by default) —
    it used to auto-generate for every pattern found, but once the detector
    lookback windows were widened (to actually cover the full loaded chart
    history, not just a trailing slice), a single scan could find 3x more
    patterns than before, and AI-explaining all of them serially in batches
    of `PATTERN_AI_MAX_WORKERS` routinely took 50-90s — past the frontend's
    30s timeout, which is why scans were "failing most of the time." The
    fix: `scan()`/`scan_multi_timeframe()` return fast, algorithmic-only
    results by default; `explain_pattern()` generates AI for exactly the one
    pattern a user is actually looking at, on demand (same on-demand design
    already used for the Analysis Tools' AI confluence call).
    """

    def __init__(self):
        self.market = MarketService()
        self.fvg_detector = FVGDetector()
        self._ai_explainer = None
        self._ai_unavailable_reason = None
        # ONE shared pool for the whole scanner instance — a multi-timeframe
        # scan runs several scan() calls concurrently, and each one's AI
        # calls must share this same cap, not each get their own (a fresh
        # per-call pool would let concurrency multiply across timeframes and
        # blow through NVIDIA's rate limit, which is exactly what happened
        # before this was a shared pool).
        self._ai_pool = ThreadPoolExecutor(max_workers=pattern_config.PATTERN_AI_MAX_WORKERS)

    def _get_explainer(self):
        if self._ai_unavailable_reason:
            return None
        if self._ai_explainer is None:
            try:
                from backend.app.services.ai.pattern_explainer import PatternExplainer
                self._ai_explainer = PatternExplainer()
            except RuntimeError as exc:
                self._ai_unavailable_reason = str(exc)
                return None
        return self._ai_explainer

    def scan(
        self, symbol: str, interval: str, limit: int = 300, include_ai: bool = False,
    ) -> PatternScanResponse:
        try:
            market = self.market.get_market_data(symbol=symbol, interval=interval, limit=limit)
        except Exception as exc:
            return PatternScanResponse(
                symbol=symbol, interval=interval, patterns=[], fvgs=[],
                scanned_at=now_iso(), error=str(exc),
            )

        detectors = PatternFactory.all_detectors()
        with ThreadPoolExecutor(max_workers=pattern_config.PATTERN_SCAN_MAX_WORKERS) as pool:
            futures = [pool.submit(self._run_detector, d, market, symbol, interval) for d in detectors]
            fvg_future = pool.submit(self._run_fvg, market, symbol, interval)
            all_patterns: list[DetectedPattern] = []
            for f in futures:
                all_patterns.extend(f.result())
            fvgs = fvg_future.result()

        min_conf = pattern_config.PATTERN_SCAN_MIN_CONFIDENCE
        patterns = [p for p in all_patterns if p.confidence >= min_conf]
        if include_ai:
            patterns = self._attach_ai(patterns)

        return PatternScanResponse(
            symbol=symbol, interval=interval, patterns=patterns, fvgs=fvgs, scanned_at=now_iso(),
        )

    def explain_pattern(self, pattern: DetectedPattern) -> AIPatternExplanation:
        """On-demand AI explanation for exactly one pattern — the fast path
        for a user selecting a single pattern in the UI."""
        explainer = self._get_explainer()
        if explainer is None:
            return AIPatternExplanation(error=self._ai_unavailable_reason or "AI explainer not configured")
        return self._safe_explain(explainer, pattern)

    def scan_multi_timeframe(
        self, symbol: str, intervals: list[str] = None, limit: int = 300, include_ai: bool = False,
    ) -> list[PatternScanResponse]:
        intervals = intervals or pattern_config.PATTERN_SCAN_INTERVALS
        with ThreadPoolExecutor(max_workers=pattern_config.PATTERN_SCAN_MAX_WORKERS) as pool:
            futures = [pool.submit(self.scan, symbol, tf, limit, include_ai) for tf in intervals]
            return [f.result() for f in futures]

    def dashboard(
        self, symbol: str, intervals: list[str] = None, limit: int = 300,
    ) -> PatternDashboardResponse:
        # Dashboard rows never surface AI fields at all (see PatternDashboardRow)
        # — always skip AI generation here regardless of caller preference.
        results = self.scan_multi_timeframe(symbol, intervals, limit, include_ai=False)
        rows = [
            PatternDashboardRow(
                symbol=p.symbol, interval=p.interval, pattern_name=p.pattern_name,
                pattern_type=p.pattern_type, confidence=p.confidence, direction=p.direction,
                current_price=p.current_price, entry_zone_low=p.entry_zone_low,
                entry_zone_high=p.entry_zone_high, stop_loss=p.stop_loss, target_1=p.target_1,
                risk_reward=p.risk_reward, status=p.status, last_updated=p.last_updated,
            )
            for res in results for p in res.patterns
        ]
        rows.sort(key=lambda r: r.confidence, reverse=True)
        return PatternDashboardResponse(rows=rows, scanned_at=now_iso())

    @staticmethod
    def _run_detector(detector, market, symbol, interval) -> list[DetectedPattern]:
        try:
            return detector.detect(market, symbol, interval)
        except Exception:
            return []

    def _run_fvg(self, market, symbol, interval):
        try:
            return self.fvg_detector.detect(market, symbol, interval)
        except Exception:
            return []

    def _attach_ai(self, patterns: list[DetectedPattern]) -> list[DetectedPattern]:
        if not patterns:
            return patterns

        explainer = self._get_explainer()
        if explainer is None:
            reason = self._ai_unavailable_reason or "AI explainer not configured"
            return [p.model_copy(update={"ai": AIPatternExplanation(error=reason)}) for p in patterns]

        futures = [(p, self._ai_pool.submit(self._safe_explain, explainer, p)) for p in patterns]
        return [p.model_copy(update={"ai": f.result()}) for p, f in futures]

    @staticmethod
    def _safe_explain(explainer, pattern, retries: int = 2) -> AIPatternExplanation:
        for attempt in range(retries + 1):
            try:
                return explainer.explain(pattern)
            except openai.RateLimitError as exc:
                if attempt == retries:
                    return AIPatternExplanation(error=str(exc))
                time.sleep(1.5 * (attempt + 1))
            except Exception as exc:
                return AIPatternExplanation(error=str(exc))
        return AIPatternExplanation(error="AI explanation failed after retries")
