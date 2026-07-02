import openai
from fastapi import APIRouter, HTTPException, Request

from backend.app.core.rate_limit import limiter, tier_rate_limit
from backend.app.schemas.ai import (
    BacktestExplainRequest,
    BacktestExplainResponse,
    ChatRequest,
    ChatResponse,
    MarketAnalysisRequest,
    MarketAnalysisResponse,
    RiskReviewRequest,
    RiskReviewResponse,
    SentimentRequest,
    SentimentResponse,
    StrategySelectionRequest,
    StrategySelectionResponse,
    TradeValidationRequest,
    TradeValidationResponse,
)
from backend.app.services.ai.ai_factory import AIFactory

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_service(factory_method):
    try:
        return factory_method()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


def _call(method, *args):
    """Run an AI service call, translating NIM/openai-SDK errors into a
    clean HTTPException instead of letting them crash as a raw 500."""
    try:
        return method(*args)
    except openai.NotFoundError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"NIM rejected the model slug (404 — model not found or your API key "
                f"lacks access to it). Check the model on build.nvidia.com and override "
                f"the matching *_MODEL env var if the slug is wrong. Raw: {e}"
            ),
        )
    except openai.AuthenticationError as e:
        raise HTTPException(
            status_code=502,
            detail=f"NVIDIA NIM rejected the API key (401). Check NVIDIA_API_KEY. Raw: {e}",
        )
    except openai.RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited by NVIDIA NIM — try again shortly. Raw: {e}",
        )
    except openai.APIConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach NVIDIA NIM ({e}).",
        )
    except openai.APIStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"NVIDIA NIM returned an error (HTTP {e.status_code}): {e}",
        )


@router.post("/analyze", response_model=MarketAnalysisResponse)
@limiter.limit(tier_rate_limit)
def analyze_market(request: Request, req: MarketAnalysisRequest) -> MarketAnalysisResponse:
    service = _get_service(AIFactory.get_market_analyst)
    return _call(service.analyze, req)


@router.post("/select-strategy", response_model=StrategySelectionResponse)
@limiter.limit(tier_rate_limit)
def select_strategy(request: Request, req: StrategySelectionRequest) -> StrategySelectionResponse:
    service = _get_service(AIFactory.get_strategy_selector)
    return _call(service.select, req)


@router.post("/validate-trade", response_model=TradeValidationResponse)
@limiter.limit(tier_rate_limit)
def validate_trade(request: Request, req: TradeValidationRequest) -> TradeValidationResponse:
    service = _get_service(AIFactory.get_trade_validator)
    return _call(service.validate, req)


@router.post("/review-risk", response_model=RiskReviewResponse)
@limiter.limit(tier_rate_limit)
def review_risk(request: Request, req: RiskReviewRequest) -> RiskReviewResponse:
    service = _get_service(AIFactory.get_risk_manager)
    return _call(service.review, req)


@router.post("/sentiment", response_model=SentimentResponse)
@limiter.limit(tier_rate_limit)
def analyze_sentiment(request: Request, req: SentimentRequest) -> SentimentResponse:
    service = _get_service(AIFactory.get_sentiment_analyzer)
    return _call(service.analyze, req)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(tier_rate_limit)
def chat(request: Request, req: ChatRequest) -> ChatResponse:
    service = _get_service(AIFactory.get_chat_assistant)
    return _call(service.chat, req)


@router.post("/explain-backtest", response_model=BacktestExplainResponse)
@limiter.limit(tier_rate_limit)
def explain_backtest(request: Request, req: BacktestExplainRequest) -> BacktestExplainResponse:
    service = _get_service(AIFactory.get_backtest_explainer)
    return _call(service.explain, req)
