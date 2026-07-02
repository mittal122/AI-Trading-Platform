from typing import Optional

from pydantic import BaseModel


class MarketAnalysisRequest(BaseModel):
    symbol: str
    interval: str
    regime: str
    price: float
    rsi: float
    macd: float
    histogram: float
    atr: float
    bb_upper: float
    bb_lower: float
    vwap: float


class MarketAnalysisResponse(BaseModel):
    symbol: str
    regime: str
    sentiment: str
    analysis: str
    key_levels: list[str]


class StrategySelectionRequest(BaseModel):
    regime: str
    volatility: str = "NORMAL"
    available_strategies: list[str] = [
        "rsi", "ema", "macd", "breakout", "supertrend", "cta_trend", "turtle", "engulfing_scalp",
    ]
    recent_performance: dict[str, float] = {}


class StrategySelectionResponse(BaseModel):
    recommended_strategy: str
    reasoning: str
    confidence: float
    alternatives: list[str]


class TradeValidationRequest(BaseModel):
    symbol: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    regime: str
    reasons: list[str]
    quality_grade: Optional[str] = None


class TradeValidationResponse(BaseModel):
    decision: str
    reason: str
    risk_flags: list[str]
    confidence: float


class RiskReviewRequest(BaseModel):
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    unrealized_pnl: float
    equity: float
    candles_held: int = 0


class RiskReviewResponse(BaseModel):
    action: str
    reasoning: str
    suggested_stop: Optional[float] = None
    suggested_size_pct: Optional[float] = None


class SentimentRequest(BaseModel):
    symbol: str
    headlines: list[str]


class SentimentResponse(BaseModel):
    symbol: str
    sentiment: str
    score: float
    summary: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


class BacktestExplainRequest(BaseModel):
    strategy: str
    symbol: str
    interval: str
    total_return: float
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    expectancy: float


class BacktestExplainResponse(BaseModel):
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    suggestion: str
