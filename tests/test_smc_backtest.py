"""B1 — SMC backtester (§9).

Metric math in isolation (_metrics) + a live walk-forward integration run with
invariants + determinism.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_backtest.py
"""

import backend.app.core.config  # noqa: F401

import time

from backend.app.schemas.smc import BacktestExitReason, BacktestTrade, Side
from backend.app.services.market_service import MarketService
from backend.app.services.smc.backtest import _metrics, run_backtest


def _t(pnl):
    return BacktestTrade(
        side=Side.LONG, entry=100, stop_loss=95, take_profit=110, qty=1,
        entry_index=0, exit_index=1, entry_time="t", exit_time="t",
        exit_price=100, pnl=pnl, pnl_pct=pnl,
        exit_reason=BacktestExitReason.TAKE_PROFIT if pnl > 0 else BacktestExitReason.STOP_LOSS,
        strength_score=80,
    )


def test_metrics_math():
    trades = [_t(20), _t(-10), _t(30), _t(-20)]
    equity = [100, 120, 110, 140, 120]
    r = _metrics("BTCUSDT", "1h", 500, 100, 120, equity, trades)
    assert r.total_trades == 4 and r.wins == 2 and r.losses == 2
    assert r.win_rate == 50.0
    assert r.avg_win == 25.0 and r.avg_loss == 15.0
    assert abs(r.profit_factor - (50 / 30)) < 1e-9      # gross 50 / 30
    assert abs(r.max_drawdown - (20 / 140 * 100)) < 1e-9  # 140 -> 120
    assert r.total_pnl == 20 and r.roi == 20.0
    # lossless -> profit factor capped at 999
    r2 = _metrics("X", "1h", 100, 100, 150, [100, 120, 150], [_t(20), _t(30)])
    assert r2.profit_factor == 999.0
    print(f"PASS metrics: winrate 50%, PF {r.profit_factor:.2f}, maxDD {r.max_drawdown:.1f}%, lossless->999")


def test_live_integration():
    df = MarketService().get_market_data("BTCUSDT", "1h", 400)
    t0 = time.monotonic()
    r = run_backtest("BTCUSDT", "1h", df, capital=100, risk_pct=2, max_trades=100, cooldown=5)
    elapsed = time.monotonic() - t0

    assert r.total_trades == r.wins + r.losses
    assert r.long_trades + r.short_trades == r.total_trades
    assert 0 <= r.win_rate <= 100
    assert 0 <= r.max_drawdown <= 100
    assert abs(r.final_capital - (r.initial_capital + r.total_pnl)) < 1e-6
    assert len(r.equity_curve) == r.total_trades + 1
    for t in r.trades:
        assert t.exit_index >= t.entry_index
        if t.exit_reason == BacktestExitReason.TAKE_PROFIT:
            assert t.pnl > 0
    assert elapsed < 60, f"backtest too slow: {elapsed:.1f}s"
    print(f"PASS live BTCUSDT/1h/400: {r.total_trades} trades "
          f"({r.long_trades}L/{r.short_trades}S), win {r.win_rate:.0f}%, "
          f"PF {r.profit_factor:.2f}, ROI {r.roi:.2f}%, maxDD {r.max_drawdown:.1f}%, {elapsed:.1f}s")


def test_determinism():
    df = MarketService().get_market_data("ETHUSDT", "1h", 300)
    a = run_backtest("ETHUSDT", "1h", df, 100, 2, 100, 5)
    b = run_backtest("ETHUSDT", "1h", df, 100, 2, 100, 5)
    assert a.total_trades == b.total_trades and abs(a.final_capital - b.final_capital) < 1e-9
    print(f"PASS determinism: identical result on rerun ({a.total_trades} trades)")


if __name__ == "__main__":
    test_metrics_math()
    test_live_integration()
    test_determinism()
    print("B1 OK")
