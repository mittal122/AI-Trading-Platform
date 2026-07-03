from typing import Any, Optional

from pydantic import BaseModel

from backend.app.schemas.pattern import ChartAnnotations, PatternDirection


class AnalysisToolResult(BaseModel):
    tool_key: str
    tool_name: str
    symbol: str
    interval: str
    bias: PatternDirection
    summary: str
    data: dict[str, Any] = {}
    annotations: ChartAnnotations
    last_updated: str
    error: Optional[str] = None


class AnalysisScanResponse(BaseModel):
    symbol: str
    interval: str
    tools: list[AnalysisToolResult]
    scanned_at: str


class AIToolExplanation(BaseModel):
    confidence_score: Optional[float] = None
    market_bias: Optional[str] = None
    reasoning: str = ""
    expected_behavior: str = ""
    entry_suggestion: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    probability_of_success: Optional[float] = None
    risk_analysis: str = ""
    confluence_notes: str = ""
    error: Optional[str] = None


class AnalysisExplainRequest(BaseModel):
    symbol: str
    interval: str
    tool_keys: list[str]
    limit: int = 300


class AnalysisExplainResponse(BaseModel):
    symbol: str
    interval: str
    tool_keys: list[str]
    explanation: AIToolExplanation
    tools: list[AnalysisToolResult]
