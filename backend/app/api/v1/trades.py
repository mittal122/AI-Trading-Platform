from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import require_admin
from backend.app.schemas.trade_history import (
    BacktestHistoryResponse,
    BacktestRunItem,
    DeleteResponse,
    SaveTradeRequest,
    TradeHistoryItem,
    TradeHistoryResponse,
)
from backend.app.services.db_service import DatabaseService
from backend.app.services.backtest.backtest_factory import BacktestFactory
from backend.app.services.portfolio.analytics import PortfolioAnalytics
from backend.app.core.time_utils import trade_duration_display

router = APIRouter(prefix="/trades", tags=["trades"])

_db = DatabaseService()


@router.get("/history", response_model=TradeHistoryResponse)
async def get_trade_history(
    symbol: str | None = Query(default=None),
    strategy: str | None = Query(default=None),
    mode: str | None = Query(default=None, description="PAPER, LIVE, or BACKTEST"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TradeHistoryResponse:
    total, trades = await _db.get_trade_history(
        symbol=symbol,
        strategy=strategy,
        mode=mode,
        limit=limit,
        offset=offset,
    )
    return TradeHistoryResponse(
        total=total,
        limit=limit,
        offset=offset,
        trades=[
            TradeHistoryItem(
                id=t.id,
                symbol=t.symbol,
                strategy=t.strategy,
                direction=t.direction,
                mode=t.mode,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                quantity=t.quantity,
                pnl=t.pnl,
                pnl_percent=t.pnl_percent,
                exit_reason=t.exit_reason,
                entry_timestamp=t.entry_timestamp,
                exit_timestamp=t.exit_timestamp,
                created_at=t.created_at.isoformat(),
                duration_display=trade_duration_display(t.entry_timestamp, t.exit_timestamp),
            )
            for t in trades
        ],
    )


@router.post("/record", response_model=TradeHistoryItem, include_in_schema=False)
async def record_trade(req: SaveTradeRequest) -> TradeHistoryItem:
    """Internal endpoint — paper/live engines call this to persist closed trades."""
    trade = await _db.save_trade(
        symbol=req.symbol,
        strategy=req.strategy,
        mode=req.mode,
        entry_price=req.entry_price,
        exit_price=req.exit_price,
        quantity=req.quantity,
        pnl=req.pnl,
        exit_reason=req.exit_reason,
        entry_timestamp=req.entry_timestamp,
        direction=req.direction,
    )
    return TradeHistoryItem(
        id=trade.id,
        symbol=trade.symbol,
        strategy=trade.strategy,
        direction=trade.direction,
        mode=trade.mode,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        quantity=trade.quantity,
        pnl=trade.pnl,
        pnl_percent=trade.pnl_percent,
        exit_reason=trade.exit_reason,
        entry_timestamp=trade.entry_timestamp,
        exit_timestamp=trade.exit_timestamp,
        created_at=trade.created_at.isoformat(),
    )


def _to_backtest_item(r) -> BacktestRunItem:
    return BacktestRunItem(
        id=r.id,
        strategy=r.strategy,
        symbol=r.symbol,
        interval=r.interval,
        limit=r.limit,
        initial_balance=r.initial_balance,
        final_balance=r.final_balance,
        total_return=r.total_return,
        total_trades=r.total_trades,
        win_rate=r.win_rate,
        profit_factor=r.profit_factor,
        sharpe_ratio=r.sharpe_ratio,
        max_drawdown=r.max_drawdown,
        winning_trades=r.winning_trades,
        losing_trades=r.losing_trades,
        avg_win=r.avg_win,
        avg_loss=r.avg_loss,
        expectancy=r.expectancy,
        sortino_ratio=r.sortino_ratio,
        calmar_ratio=r.calmar_ratio,
        avg_candles_to_win=r.avg_candles_to_win,
        avg_time_to_win_display=r.avg_time_to_win_display,
        created_at=r.created_at.isoformat(),
    )


@router.get("/backtest-history", response_model=BacktestHistoryResponse)
async def get_backtest_history(
    strategy: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> BacktestHistoryResponse:
    total, runs = await _db.get_backtest_history(
        strategy=strategy, symbol=symbol, limit=limit, offset=offset
    )
    return BacktestHistoryResponse(
        total=total,
        limit=limit,
        offset=offset,
        runs=[_to_backtest_item(r) for r in runs],
    )


@router.delete("/backtest-history/{run_id}", response_model=DeleteResponse)
async def delete_backtest_run(run_id: int) -> DeleteResponse:
    ok = await _db.delete_backtest_run(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return DeleteResponse(deleted=1)


@router.delete("/backtest-history", response_model=DeleteResponse, dependencies=[Depends(require_admin)])
async def delete_all_backtest_runs() -> DeleteResponse:
    # Mass delete is admin-gated — anonymous "wipe all history" on a deployed
    # instance would be a trivial destructive action otherwise.
    count = await _db.delete_all_backtest_runs()
    return DeleteResponse(deleted=count)


@router.post("/backtest-record", response_model=BacktestRunItem)
async def run_and_record_backtest(
    strategy: str = Query(default="rsi"),
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
    limit: int = Query(default=300),
) -> BacktestRunItem:
    """Run a backtest and persist the result to the database."""
    engine = BacktestFactory.get_engine()
    result = engine.run(strategy=strategy, symbol=symbol, interval=interval, limit=limit)

    analytics = PortfolioAnalytics()
    report = analytics.compute(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_balance=result.initial_balance,
    )

    run = await _db.save_backtest_run(
        strategy=strategy,
        symbol=symbol,
        interval=interval,
        limit=limit,
        initial_balance=report.initial_balance,
        final_balance=report.ending_balance,
        total_return=report.total_return,
        total_trades=report.total_trades,
        win_rate=report.win_rate,
        profit_factor=report.profit_factor,
        sharpe_ratio=report.sharpe_ratio,
        max_drawdown=report.max_drawdown,
        winning_trades=report.winning_trades,
        losing_trades=report.losing_trades,
        avg_win=report.avg_win,
        avg_loss=report.avg_loss,
        expectancy=report.expectancy,
        sortino_ratio=report.sortino_ratio,
        calmar_ratio=report.calmar_ratio,
        avg_candles_to_win=result.avg_candles_to_win,
        avg_time_to_win_display=result.avg_time_to_win_display,
    )

    return _to_backtest_item(run)
