from fastapi import APIRouter, Query

from backend.app.schemas.strategy import StrategyResponse
from backend.app.schemas.trading_signal import TradingSignal
from backend.app.services.market_service import MarketService
from backend.app.services.strategy.strategy_factory import (
    StrategyFactory,
)

router = APIRouter(
    prefix="/strategy",
    tags=["Strategy"],
)


@router.get(
    "",
    response_model=StrategyResponse,
)
def run_strategy(
    strategy: str = Query(default="rsi"),
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
):

    engine = StrategyFactory.get_strategy(strategy)

    return engine.analyze(
        symbol=symbol,
        interval=interval,
    )


@router.get(
    "/signal",
    response_model=TradingSignal,
)
def run_strategy_full_signal(
    strategy: str = Query(default="rsi"),
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
    limit: int = Query(default=250),
):
    """
    Return the full TradingSignal — includes regime, quality score/grade,
    ATR, and human-readable explanation (richer than GET /strategy).
    """
    engine = StrategyFactory.get_strategy(strategy)

    market = MarketService().get_market_data(
        symbol=symbol,
        interval=interval,
        limit=limit,
    )

    return engine.generate_signal(
        market=market,
        symbol=symbol,
        interval=interval,
    )