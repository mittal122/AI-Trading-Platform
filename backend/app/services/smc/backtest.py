"""Backtesting engine (§9).

Replays the exact live strategy walk-forward over historical candles — same
analyze() (minus order flow, so no look-ahead), same firing rules — and simulates
fills, stops, targets and time exits. Reports win rate, profit factor, drawdown,
ROI and an equity curve. No fees/funding/slippage (per doc).

Faithfulness details:
  * one position at a time; stop-and-target-in-the-same-bar assumes the stop
    first (conservative);
  * entries are limit orders at the zone — the engine waits up to
    BT_FILL_SCAN_BARS for price to trade into the entry, else abandons;
  * signals whose entry is >BT_MAX_ENTRY_DIST_PCT from price are skipped.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import (
    BacktestExitReason, BacktestResult, BacktestTrade, Side,
)
from backend.app.services.smc.smc_engine import analyze

cfg = smc_config


def run_backtest(
    symbol: str, interval: str, df: pd.DataFrame,
    capital: float, risk_pct: float, max_trades: int, cooldown: int,
) -> BacktestResult:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    times = [t.isoformat() for t in df["timestamps"]]
    n = len(df)
    max_hold = cfg.BT_MAX_HOLD.get(interval, 100)

    initial_capital = capital
    equity = [capital]
    trades: list[BacktestTrade] = []
    open_trade: dict | None = None
    last_signal_bar = -10**9

    def close_trade(exit_index, exit_price, reason):
        nonlocal capital, open_trade
        t = open_trade
        is_long = t["side"] == Side.LONG
        pnl = (exit_price - t["entry"]) * t["qty"] if is_long else (t["entry"] - exit_price) * t["qty"]
        invested = t["entry"] * t["qty"]
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0.0
        capital += pnl
        trades.append(BacktestTrade(
            side=t["side"], entry=t["entry"], stop_loss=t["sl"], take_profit=t["tp"],
            qty=t["qty"], entry_index=t["entry_index"], exit_index=exit_index,
            entry_time=times[t["entry_index"]], exit_time=times[exit_index],
            exit_price=exit_price, pnl=pnl, pnl_pct=pnl_pct, exit_reason=reason,
            strength_score=t["strength"],
        ))
        equity.append(capital)
        open_trade = None

    i = cfg.BT_WARMUP
    while i < n:
        if open_trade is not None:
            t = open_trade
            is_long = t["side"] == Side.LONG
            hit_sl = lows[i] <= t["sl"] if is_long else highs[i] >= t["sl"]
            hit_tp = highs[i] >= t["tp"] if is_long else lows[i] <= t["tp"]
            if hit_sl and hit_tp:
                close_trade(i, t["sl"], BacktestExitReason.STOP_LOSS)   # conservative
            elif hit_sl:
                close_trade(i, t["sl"], BacktestExitReason.STOP_LOSS)
            elif hit_tp:
                close_trade(i, t["tp"], BacktestExitReason.TAKE_PROFIT)
            elif i - t["entry_index"] >= max_hold:
                close_trade(i, float(closes[i]), BacktestExitReason.TIME_EXIT)
            i += 1
            continue

        # Flat — look for a new signal.
        if capital <= 0 or len(trades) >= max_trades or (i - last_signal_bar) < cooldown:
            i += 1
            continue

        window = df.iloc[max(0, i - cfg.BT_ANALYSIS_WINDOW + 1):i + 1]
        res = analyze(symbol, interval, window)   # no order flow -> walk-forward safe
        if res.primary not in ("long", "short"):
            i += 1
            continue

        plan = res.long_plan if res.primary == "long" else res.short_plan
        price = float(closes[i])
        if abs(plan.entry - price) / price * 100 > cfg.BT_MAX_ENTRY_DIST_PCT:
            i += 1
            continue

        is_long = plan.side == Side.LONG
        fill_index = None
        for j in range(i + 1, min(n, i + 1 + cfg.BT_FILL_SCAN_BARS)):
            if (is_long and lows[j] <= plan.entry) or (not is_long and highs[j] >= plan.entry):
                fill_index = j
                break
        last_signal_bar = i
        if fill_index is None:
            i += 1
            continue   # never filled -> abandoned

        risk_dollars = capital * risk_pct / 100.0
        risk_per_unit = abs(plan.entry - plan.stop_loss)
        qty = risk_dollars / risk_per_unit if risk_per_unit > 0 else 0.0
        open_trade = {
            "side": plan.side, "entry": plan.entry, "sl": plan.stop_loss,
            "tp": plan.take_profit_1, "qty": qty, "entry_index": fill_index,
            "strength": plan.strength_score,
        }
        i = fill_index   # jump to the fill bar; management resumes there

    if open_trade is not None:
        close_trade(n - 1, float(closes[n - 1]), BacktestExitReason.END_OF_DATA)

    return _metrics(symbol, interval, n, initial_capital, capital, equity, trades)


def _metrics(symbol, interval, n, initial_capital, capital, equity, trades) -> BacktestResult:
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = sum(-t.pnl for t in losses)
    total = len(trades)

    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    else:
        profit_factor = 999.0 if gross_win > 0 else 0.0

    peak = equity[0]
    max_dd = 0.0
    for e in equity:
        peak = max(peak, e)
        if peak > 0:
            max_dd = max(max_dd, (peak - e) / peak * 100)

    total_pnl = capital - initial_capital
    return BacktestResult(
        symbol=symbol.upper(), interval=interval, candles=n,
        initial_capital=initial_capital, final_capital=capital,
        total_trades=total, wins=len(wins), losses=len(losses),
        long_trades=sum(1 for t in trades if t.side == Side.LONG),
        short_trades=sum(1 for t in trades if t.side == Side.SHORT),
        win_rate=(len(wins) / total * 100) if total else 0.0,
        avg_win=(gross_win / len(wins)) if wins else 0.0,
        avg_loss=(gross_loss / len(losses)) if losses else 0.0,
        profit_factor=profit_factor,
        max_drawdown=max_dd,
        total_pnl=total_pnl,
        roi=(total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0,
        equity_curve=equity,
        trades=trades,
    )
