from fastapi import APIRouter, Query

from backend.app.schemas.analytics import PortfolioAnalyticsResponse
from backend.app.services.backtest.backtest_factory import BacktestFactory
from backend.app.services.portfolio.analytics import PortfolioAnalytics

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/analytics", response_model=PortfolioAnalyticsResponse)
def get_portfolio_analytics(
    strategy: str = Query(default="rsi"),
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
    limit: int = Query(default=300),
):
    engine = BacktestFactory.get_engine()
    result = engine.run(
        strategy=strategy,
        symbol=symbol,
        interval=interval,
        limit=limit,
    )

    analytics = PortfolioAnalytics()
    return analytics.compute(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_balance=result.initial_balance,
    )
