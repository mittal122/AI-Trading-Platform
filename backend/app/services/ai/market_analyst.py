import json

from backend.app.core.ai_provider_config import MARKET_ANALYST
from backend.app.schemas.ai import MarketAnalysisRequest, MarketAnalysisResponse
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a professional cryptocurrency market analyst with expertise in technical analysis.
Analyze the provided market data and return a JSON object with exactly these fields:
{
  "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "analysis": "<2-3 sentence natural language summary>",
  "key_levels": ["<level description>", ...]
}
Be concise and precise. Base conclusions strictly on provided indicators."""


class MarketAnalyst(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(MARKET_ANALYST)

    def analyze(self, req: MarketAnalysisRequest) -> MarketAnalysisResponse:
        user = f"""
Symbol: {req.symbol} ({req.interval})
Regime: {req.regime}
Price: {req.price:.4f}
RSI(14): {req.rsi:.2f}
MACD: {req.macd:.4f} | Histogram: {req.histogram:.4f}
ATR(14): {req.atr:.4f}
Bollinger Bands: Upper={req.bb_upper:.4f} Lower={req.bb_lower:.4f}
VWAP: {req.vwap:.4f}

Analyze these conditions and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=1024)
        data = self._parse_json(raw)

        return MarketAnalysisResponse(
            symbol=req.symbol,
            regime=req.regime,
            sentiment=data.get("sentiment", "NEUTRAL"),
            analysis=data.get("analysis", raw),
            key_levels=data.get("key_levels", []),
        )

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"sentiment": "NEUTRAL", "analysis": text, "key_levels": []}
