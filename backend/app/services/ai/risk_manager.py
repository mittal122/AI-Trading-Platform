import json
from typing import Optional

from backend.app.core.ai_provider_config import RISK_MANAGER
from backend.app.schemas.ai import RiskReviewRequest, RiskReviewResponse
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a portfolio risk manager for an algorithmic crypto trading system.
Review the open position and return JSON with exactly these fields:
{
  "action": "HOLD" | "REDUCE" | "CLOSE" | "TIGHTEN_STOP",
  "reasoning": "<1-2 sentence explanation>",
  "suggested_stop": <price or null>,
  "suggested_size_pct": <0.0-1.0 or null>
}
Prioritize capital preservation. Return JSON only."""


class AIRiskManager(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(RISK_MANAGER)

    def review(self, req: RiskReviewRequest) -> RiskReviewResponse:
        pnl_pct = (
            ((req.current_price - req.entry_price) / req.entry_price * 100)
            if req.direction == "BUY"
            else ((req.entry_price - req.current_price) / req.entry_price * 100)
        )
        exposure_pct = (req.position_size * req.current_price / req.equity * 100) if req.equity > 0 else 0

        user = f"""
Open Position:
  Symbol: {req.symbol}
  Direction: {req.direction}
  Entry: {req.entry_price:.4f}
  Current: {req.current_price:.4f}
  P&L: {pnl_pct:.2f}%
  Stop Loss: {req.stop_loss:.4f}
  Take Profit: {req.take_profit:.4f}
  Position Size: {req.position_size:.4f} units
  Exposure: {exposure_pct:.2f}% of equity
  Unrealized P&L: ${req.unrealized_pnl:.2f}
  Equity: ${req.equity:.2f}
  Candles Held: {req.candles_held}

Review risk and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=1024)
        data = self._parse_json(raw)

        suggested_stop: Optional[float] = data.get("suggested_stop")
        suggested_size: Optional[float] = data.get("suggested_size_pct")

        return RiskReviewResponse(
            action=data.get("action", "HOLD"),
            reasoning=data.get("reasoning", raw),
            suggested_stop=float(suggested_stop) if suggested_stop is not None else None,
            suggested_size_pct=float(suggested_size) if suggested_size is not None else None,
        )

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"action": "HOLD", "reasoning": text, "suggested_stop": None, "suggested_size_pct": None}
