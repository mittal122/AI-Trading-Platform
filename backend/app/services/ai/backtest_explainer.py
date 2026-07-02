import json

from backend.app.core.ai_provider_config import BACKTEST_EXPLAINER
from backend.app.schemas.ai import BacktestExplainRequest, BacktestExplainResponse
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are a quantitative trading coach explaining backtest results to a strategy developer.
Analyze the provided backtest metrics and return JSON with exactly these fields:
{
  "summary": "<2-3 sentence plain-English summary of how the strategy performed>",
  "strengths": ["<what worked well>", ...],
  "weaknesses": ["<what didn't work / risk concerns>", ...],
  "suggestion": "<1-2 sentence concrete next step to improve the strategy>"
}
Judge Sharpe/Sortino/Calmar by standard quant thresholds (>1 acceptable, >2 good, >3 excellent).
Be direct — do not sugarcoat a poor result. Return JSON only."""


class BacktestExplainer(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(BACKTEST_EXPLAINER)

    def explain(self, req: BacktestExplainRequest) -> BacktestExplainResponse:
        user = f"""
Strategy: {req.strategy} | Symbol: {req.symbol} | Interval: {req.interval}

Total Return: {req.total_return:.2f}%
Total Trades: {req.total_trades}
Win Rate: {req.win_rate:.2f}%
Profit Factor: {req.profit_factor:.2f}
Expectancy: ${req.expectancy:.4f} per trade

Sharpe Ratio: {req.sharpe_ratio:.3f}
Sortino Ratio: {req.sortino_ratio:.3f}
Calmar Ratio: {req.calmar_ratio:.3f}
Max Drawdown: {req.max_drawdown:.2f}%

Explain this backtest and return JSON only.
""".strip()

        raw = self._call(_SYSTEM, user, max_tokens=1024)
        data = self._parse_json(raw)

        return BacktestExplainResponse(
            summary=data.get("summary", raw),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            suggestion=data.get("suggestion", ""),
        )

    def _parse_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"summary": text, "strengths": [], "weaknesses": [], "suggestion": ""}
