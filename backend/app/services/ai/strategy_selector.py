import json

from backend.app.core.ai_provider_config import STRATEGY_SELECTOR
from backend.app.schemas.ai import StrategySelectionRequest, StrategySelectionResponse
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a quantitative trading strategist. Given market regime and strategy performance data,
select the best strategy and return JSON with exactly these fields:
{
  "recommended_strategy": "<strategy_key>",
  "reasoning": "<1-2 sentence explanation>",
  "confidence": <0.0-1.0>,
  "alternatives": ["<strategy_key>", ...]
}
Only recommend strategies from the available list. Return JSON only."""


class StrategySelector(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(STRATEGY_SELECTOR)

    def select(self, req: StrategySelectionRequest) -> StrategySelectionResponse:
        perf_lines = (
            "\n".join(f"  {k}: {v:.2f}% return" for k, v in req.recent_performance.items())
            if req.recent_performance
            else "  No recent performance data"
        )
        user = f"""
Market Regime: {req.regime}
Volatility: {req.volatility}
Available strategies: {", ".join(req.available_strategies)}
Recent performance:
{perf_lines}

Select the best strategy and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=1024)
        data = self._parse_json(raw)

        default = req.available_strategies[0] if req.available_strategies else "rsi"
        return StrategySelectionResponse(
            recommended_strategy=data.get("recommended_strategy", default),
            reasoning=data.get("reasoning", raw),
            confidence=float(data.get("confidence", 0.5)),
            alternatives=data.get("alternatives", []),
        )

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {}
