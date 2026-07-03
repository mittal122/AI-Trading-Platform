import json
import re

from backend.app.core.ai_provider_config import ANALYSIS_EXPLAINER
from backend.app.schemas.analysis_tool import AIToolExplanation, AnalysisToolResult
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a professional technical analyst. You are given the ALREADY-COMPUTED
output of one or more chart analysis tools (support/resistance, moving averages, VWAP,
pivot points, ATR, etc.) for one symbol/timeframe — your job is to synthesize them into
one coherent read, especially where they agree or disagree with each other (confluence).
You do not recompute anything, only interpret what's given. Return a JSON object with
exactly these fields:
{
  "confidence_score": <0-100 number>,
  "market_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "reasoning": "<2-4 sentences synthesizing the enabled tools>",
  "expected_behavior": "<1-2 sentences: what price is likely to do next>",
  "entry_suggestion": <price number or null>,
  "stop_loss": <price number or null>,
  "take_profit": <price number or null>,
  "probability_of_success": <0-100 number or null>,
  "risk_analysis": "<1-2 sentences>",
  "confluence_notes": "<1-2 sentences: where the enabled tools agree/disagree>"
}
Ground every number strictly in the levels/values actually given — never invent a price
level that isn't derivable from the tool data provided. Output ONLY that JSON object —
no markdown fences, no extra keys, no duplicate keys, every string properly closed."""


class AnalysisExplainer(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(ANALYSIS_EXPLAINER)

    def explain(self, symbol: str, interval: str, tools: list[AnalysisToolResult]) -> AIToolExplanation:
        tool_blocks = "\n\n".join(
            f"Tool: {t.tool_name} ({t.tool_key})\nBias: {t.bias.value}\nSummary: {t.summary}\nData: {json.dumps(t.data, default=str)}"
            for t in tools if not t.error
        )
        user = f"""
Symbol: {symbol} | Timeframe: {interval}
Enabled tools ({len(tools)}):

{tool_blocks}

Synthesize these into one read and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=900)
        data = self._parse_json(raw)

        return AIToolExplanation(
            confidence_score=self._safe_float(data.get("confidence_score")),
            market_bias=data.get("market_bias"),
            reasoning=data.get("reasoning", ""),
            expected_behavior=data.get("expected_behavior", ""),
            entry_suggestion=self._safe_float(data.get("entry_suggestion")),
            stop_loss=self._safe_float(data.get("stop_loss")),
            take_profit=self._safe_float(data.get("take_profit")),
            probability_of_success=self._safe_float(data.get("probability_of_success")),
            risk_analysis=data.get("risk_analysis", ""),
            confluence_notes=data.get("confluence_notes", ""),
        )

    @staticmethod
    def _safe_float(value):
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_json(text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        blob = text[start:end] if start != -1 and end > start else ""

        if blob:
            try:
                return json.loads(blob)
            except json.JSONDecodeError:
                pass

        # LLMs occasionally emit near-JSON with a dropped quote or a stray
        # duplicate key (seen live: `"market_bias": "BULLISH,` missing its
        # closing quote) — salvage individual "key": value pairs by regex
        # instead of discarding the whole response over one glitched field.
        result: dict = {}
        for match in re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', blob):
            result.setdefault(match.group(1), match.group(2))
        for match in re.finditer(r'"(\w+)"\s*:\s*(-?\d+(?:\.\d+)?)', blob):
            result.setdefault(match.group(1), float(match.group(2)))
        return result
