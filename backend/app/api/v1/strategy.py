from fastapi import APIRouter, Query

from backend.app.schemas.strategy import StrategyResponse
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