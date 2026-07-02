import json

from backend.app.core.ai_provider_config import SENTIMENT_ANALYZER
from backend.app.schemas.ai import SentimentRequest, SentimentResponse
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a crypto market sentiment analyst.
Analyze the provided news headlines for a given asset and return JSON with exactly these fields:
{
  "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "score": <-1.0 to 1.0>,
  "summary": "<1 sentence summary of overall sentiment>"
}
Score: 1.0 = very bullish, -1.0 = very bearish, 0.0 = neutral.
Return JSON only."""


class SentimentAnalyzer(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(SENTIMENT_ANALYZER)

    def analyze(self, req: SentimentRequest) -> SentimentResponse:
        headlines_text = "\n".join(f"  - {h}" for h in req.headlines)
        user = f"""
Asset: {req.symbol}

News headlines:
{headlines_text}

Analyze sentiment and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=512)
        data = self._parse_json(raw)

        return SentimentResponse(
            symbol=req.symbol,
            sentiment=data.get("sentiment", "NEUTRAL"),
            score=float(data.get("score", 0.0)),
            summary=data.get("summary", raw),
        )

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"sentiment": "NEUTRAL", "score": 0.0, "summary": text}
