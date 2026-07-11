from typing import Optional

from fastapi import APIRouter, Query

from backend.app.schemas.analytics import PortfolioAnalyticsResponse
from backend.app.schemas.backtest import EquityPoint, TradeResult
from backend.app.services.backtest.backtest_factory import BacktestFactory
from backend.app.services.db_service import DatabaseService
from backend.app.services.portfolio.analytics import PortfolioAnalytics

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/analytics", response_model=PortfolioAnalyticsResponse)
def get_portfolio_analytics(
    strategy: str = Query(default="rsi"),
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
    limit: int = Query(default=300),
):
    """SIMULATED analytics — runs a fresh backtest of one strategy and
    reports that run's stats. Not the user's actual trading record; the
    Portfolio page uses /analytics/history below instead."""
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


@router.get("/analytics/history", response_model=PortfolioAnalyticsResponse)
async def get_history_analytics(
    mode: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    strategy: Optional[str] = Query(default=None),
    initial_balance: float = Query(default=10_000.0, gt=0),
):
    """Analytics computed from the REAL recorded trades in the database
    (the same rows /trades/history shows) — win rate, PnL, drawdown, etc.
    reflect what actually happened, not a simulation.

    mode omitted => PAPER + LIVE only (BACKTEST rows are simulations and
    would contaminate a 'real performance' read); pass mode=BACKTEST
    explicitly to analyze those. The equity curve is the initial balance
    plus cumulative realized PnL in exit order (matches the paper account's
    $10,000 default starting balance).
    """
    _, rows = await DatabaseService().get_trade_history(
        symbol=symbol, strategy=strategy, mode=mode, limit=100_000,
    )
    if mode is None:
        rows = [r for r in rows if r.mode != "BACKTEST"]
    rows.sort(key=lambda r: r.exit_timestamp or "")

    trades = [
        TradeResult(
            entry_price=r.entry_price,
            exit_price=r.exit_price,
            quantity=r.quantity,
            pnl=r.pnl,
            return_percent=r.pnl_percent,
            entry_timestamp=r.entry_timestamp or "",
            exit_timestamp=r.exit_timestamp or "",
        )
        for r in rows
    ]

    equity = initial_balance
    curve = [EquityPoint(candle=0, timestamp="", equity=initial_balance)]
    for i, t in enumerate(trades):
        equity += t.pnl
        curve.append(EquityPoint(candle=i + 1, timestamp=t.exit_timestamp, equity=equity))

    return PortfolioAnalytics().compute(
        trades=trades, equity_curve=curve, initial_balance=initial_balance,
    )
