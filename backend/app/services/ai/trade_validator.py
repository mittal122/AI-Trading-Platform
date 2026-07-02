import json

from backend.app.core.ai_provider_config import TRADE_VALIDATOR
from backend.app.schemas.ai import TradeValidationRequest, TradeValidationResponse
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a risk-focused trade validator for an algorithmic trading system.
Critically evaluate the proposed trade and return JSON with exactly these fields:
{
  "decision": "APPROVE" | "REJECT",
  "reason": "<1-2 sentence explanation>",
  "risk_flags": ["<flag>", ...],
  "confidence": <0.0-1.0>
}
Be conservative. Reject if risk/reward is unfavorable, contradicting indicators, or poor regime fit.
Return JSON only."""


class TradeValidator(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(TRADE_VALIDATOR)

    def validate(self, req: TradeValidationRequest) -> TradeValidationResponse:
        user = f"""
Trade Signal:
  Symbol: {req.symbol}
  Direction: {req.direction}
  Entry: {req.entry:.4f}
  Stop Loss: {req.stop_loss:.4f}
  Take Profit: {req.take_profit:.4f}
  Risk/Reward: {req.risk_reward:.2f}
  Signal Confidence: {req.confidence:.2f}
  Market Regime: {req.regime}
  Quality Grade: {req.quality_grade or "N/A"}

Signal reasons:
{chr(10).join(f"  - {r}" for r in req.reasons)}

Validate this trade and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=1024)
        data = self._parse_json(raw)

        return TradeValidationResponse(
            decision=data.get("decision", "REJECT"),
            reason=data.get("reason", raw),
            risk_flags=data.get("risk_flags", []),
            confidence=float(data.get("confidence", 0.5)),
        )

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"decision": "REJECT", "reason": text, "risk_flags": [], "confidence": 0.5}
