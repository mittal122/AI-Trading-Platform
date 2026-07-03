from fastapi import APIRouter, Query

from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.strategy import StrategyResponse
from backend.app.schemas.trading_signal import SignalDirection, TradingSignal
from backend.app.services.market_service import MarketService
from backend.app.services.strategy.strategy_factory import (
    StrategyFactory,
)
from backend.app.services.strategy.eta_estimator import TimeToTargetEstimator
from backend.app.services.strategy.signal_scanner import SignalScanner

eta_estimator = TimeToTargetEstimator()
scanner = SignalScanner()

router = APIRouter(
    prefix="/strategy",
    tags=["Strategy"],
)


@router.get("/available")
def list_available_strategies():
    """Strategy keys the factory can build — single source of truth for the frontend."""
    return {"strategies": StrategyFactory.list_strategies()}


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

    signal = engine.generate_signal(
        market=market,
        symbol=symbol,
        interval=interval,
    )

    if signal.direction != SignalDirection.FLAT:
        eta_candles, eta_display = eta_estimator.estimate(
            entry=signal.entry,
            take_profit=signal.take_profit,
            atr=signal.atr or 0.0,
            interval=interval,
            regime=signal.regime,
        )
        signal = signal.model_copy(update={"eta_candles": eta_candles, "eta_display": eta_display})

    return signal


@router.get(
    "/scan",
    response_model=list[TradingSignal],
)
def scan_all_strategies(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
    limit: int = Query(default=250),
):
    """
    Run every registered strategy against one symbol/interval and return
    each one's signal — so every strategy analyzes the market on its own,
    without opening them one at a time.
    """
    return scanner.scan_all_strategies(symbol=symbol, interval=interval, limit=limit)


@router.get(
    "/multi-timeframe",
    response_model=list[TradingSignal],
)
def scan_multi_timeframe(
    strategy: str = Query(default="rsi"),
    symbol: str = Query(default="BTCUSDT"),
    intervals: str = Query(
        default=None,
        description="Comma-separated intervals, e.g. '1m,5m,15m,1h,4h'. Defaults to the platform's standard scan set.",
    ),
    limit: int = Query(default=250),
):
    """
    Run one strategy across multiple timeframes independently, so signals
    can be compared side by side to see which timeframe it currently suits.
    """
    interval_list = (
        [i.strip() for i in intervals.split(",") if i.strip()]
        if intervals
        else strategy_config.SCAN_DEFAULT_INTERVALS
    )
    return scanner.scan_timeframes(
        strategy=strategy, symbol=symbol, intervals=interval_list, limit=limit
    )