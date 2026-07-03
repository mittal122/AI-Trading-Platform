import json

from backend.app.core.ai_provider_config import PATTERN_EXPLAINER
from backend.app.schemas.pattern import AIPatternExplanation, DetectedPattern, PatternRecommendation
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a professional technical analyst specializing in chart pattern
interpretation. You are given a chart pattern that has ALREADY been detected
algorithmically (geometry, levels, and confidence are computed — not your job to
re-detect anything). Explain it like a seasoned trader would, strictly grounded in
the data given. Return a JSON object with exactly these fields:
{
  "why_detected": "<1-2 sentences: what price action triggered this pattern>",
  "why_valid": "<1-2 sentences: why the geometry/volume support this being real, not noise>",
  "market_psychology": "<1-2 sentences: the psychological dynamic behind this pattern>",
  "buyer_seller_behavior": "<1-2 sentences: what buyers and sellers are doing right now>",
  "strength": "Weak" | "Moderate" | "Strong",
  "reliability_score": <0-100 number, your own qualitative read>,
  "alternative_scenario": "<1-2 sentences: what happens if this pattern fails>",
  "recommendation": "BUY" | "SELL" | "WAIT" | "AVOID",
  "recommendation_reason": "<1-2 sentences justifying the recommendation>"
}
Do not invent price levels beyond what's given. Be concise and concrete."""


class PatternExplainer(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(PATTERN_EXPLAINER)

    def explain(self, pattern: DetectedPattern) -> AIPatternExplanation:
        user = f"""
Pattern: {pattern.pattern_name} ({pattern.pattern_type})
Symbol: {pattern.symbol} | Timeframe: {pattern.interval}
Direction: {pattern.direction.value} | Status: {pattern.status.value}
Algorithmic confidence: {pattern.confidence:.1f}/100
Formation: {pattern.formation_start} to {pattern.formation_end}
Current price: {pattern.current_price}
Breakout level: {pattern.breakout_level}
Invalidation level: {pattern.invalidation_level}
Entry zone: {pattern.entry_zone_low} - {pattern.entry_zone_high}
Stop loss: {pattern.stop_loss}
Targets: T1={pattern.target_1} T2={pattern.target_2} T3={pattern.target_3}
Risk/Reward: {pattern.risk_reward}

Explain this pattern and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=800)
        data = self._parse_json(raw)

        return AIPatternExplanation(
            why_detected=data.get("why_detected", ""),
            why_valid=data.get("why_valid", ""),
            market_psychology=data.get("market_psychology", ""),
            buyer_seller_behavior=data.get("buyer_seller_behavior", ""),
            strength=data.get("strength", ""),
            reliability_score=self._safe_float(data.get("reliability_score")),
            alternative_scenario=data.get("alternative_scenario", ""),
            recommendation=self._safe_recommendation(data.get("recommendation")),
            recommendation_reason=data.get("recommendation_reason", ""),
        )

    @staticmethod
    def _safe_recommendation(value):
        try:
            return PatternRecommendation(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_json(text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {}
