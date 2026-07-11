"""SMC Auto-Test — a hands-free paper-trading loop over the SMC engine.

Every time a candle of the chosen interval CLOSES, re-run the SMC analysis and:
  - flat  -> enter a paper trade on the current bias / stronger-confluence side
             (if that side's score clears min_score)
  - held  -> hold until the trader's own monitor closes it at SL/TP
             ("hold until target"), UNLESS the opposite side's score now beats
             the current side's by flip_margin — then close immediately and
             open the opposite direction (the dual-direction flip).

All trades are PAPER via ManualPaperTrader (strategy="smc_autotest"), so closed
trades persist to the DB and show up on the Portfolio page automatically.
Session state (event log, stats) is in-memory, same as the paper auto-bot.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.smc_config import smc_config as cfg
from backend.app.schemas.paper import ManualOrder, ManualOrderRequest
from backend.app.services.market_service import MarketService
from backend.app.services.paper.manual_paper_trader import ManualPaperFactory
from backend.app.services.smc.smc_engine import analyze


def decide(
    primary: str,
    long_score: int,
    short_score: int,
    current_side: Optional[str],
    min_score: int,
    flip_margin: int,
) -> tuple[str, Optional[str]]:
    """Pure decision core (unit-tested): what to do after a re-analysis.

    Returns (action, side): ("enter"|"flip", side) / ("hold", current) /
    ("wait", None).
    """
    if current_side is None:
        if primary in ("long", "short"):
            side = primary
        else:
            side = "long" if long_score >= short_score else "short"
        score = long_score if side == "long" else short_score
        if score >= min_score:
            return "enter", side
        return "wait", None

    cur_score = long_score if current_side == "long" else short_score
    opp = "short" if current_side == "long" else "long"
    opp_score = long_score if opp == "long" else short_score
    if opp_score >= min_score and opp_score >= cur_score + flip_margin:
        return "flip", opp
    return "hold", current_side


class SmcAutoTester:
    """One session at a time, server-side (keeps trading if the browser closes)."""

    def __init__(self) -> None:
        self._market = MarketService()
        self._task: Optional[asyncio.Task] = None
        self._reset_session()

    def _reset_session(self) -> None:
        self.symbol = ""
        self.interval = ""
        self.risk_percent = cfg.AUTOTEST_RISK_PCT_DEFAULT
        self.min_score = cfg.AUTOTEST_MIN_SCORE_DEFAULT
        self.flip_margin = cfg.AUTOTEST_FLIP_MARGIN_DEFAULT
        self.started_at: Optional[str] = None
        self._cursor: Optional[str] = None          # last analyzed closed-candle time
        self._order_id: Optional[int] = None
        self._side: Optional[str] = None
        self._events: deque = deque(maxlen=cfg.AUTOTEST_LOG_MAX)
        self._session_closed: list[ManualOrder] = []
        self._last_analysis: Optional[dict] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, symbol: str, interval: str, risk_percent: float,
              min_score: int, flip_margin: int) -> None:
        if self.running:
            raise ValueError("Auto-test already running — stop it first")
        self._reset_session()
        self.symbol = symbol.upper()
        self.interval = interval
        self.risk_percent = risk_percent
        self.min_score = min_score
        self.flip_margin = flip_margin
        self.started_at = _now()
        self._log("START", f"{self.symbol} {interval} · risk {risk_percent}% · "
                           f"min score {min_score} · flip margin {flip_margin}")
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if not self.running:
            raise ValueError("Auto-test is not running")
        self._task.cancel()
        self._task = None
        if self._order_id is not None:
            # Deliberately left open: the trader's own monitor keeps managing
            # it to SL/TP even without the loop.
            self._log("STOP", f"session stopped — open order #{self._order_id} "
                              "left running to its SL/TP")
        else:
            self._log("STOP", "session stopped")

    def status(self) -> dict:
        trader = ManualPaperFactory.get_trader()
        current = None
        if self._order_id is not None:
            current = next(
                (o.model_dump() for o in trader.status().open_orders if o.id == self._order_id),
                None,
            )
        wins = sum(1 for o in self._session_closed if o.realized_pnl > 0)
        return {
            "running": self.running,
            "symbol": self.symbol,
            "interval": self.interval,
            "risk_percent": self.risk_percent,
            "min_score": self.min_score,
            "flip_margin": self.flip_margin,
            "started_at": self.started_at,
            "current_side": self._side if current else None,
            "current_order": current,
            "last_analysis": self._last_analysis,
            "events": list(self._events)[::-1],   # newest first
            "stats": {
                "trades": len(self._session_closed),
                "wins": wins,
                "net_pnl": round(sum(o.realized_pnl for o in self._session_closed), 4),
            },
        }

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        while True:
            try:
                await self._tick()
            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001 — one bad tick never kills the session
                self._log("ERROR", str(exc)[:200])
            await asyncio.sleep(cfg.AUTOTEST_POLL_SECONDS)

    async def _tick(self) -> None:
        self._sync_order_state()

        df = await asyncio.to_thread(
            self._market.get_market_data, self.symbol, self.interval,
            cfg.AUTOTEST_FETCH_CANDLES,
        )
        if df is None or len(df) < cfg.SCAN_MIN_CANDLES:
            return
        # Candle-close gate — last row is the still-forming candle.
        closed_time = df["timestamps"].iloc[-2].isoformat()
        if closed_time == self._cursor:
            return
        self._cursor = closed_time

        res = await asyncio.to_thread(analyze, self.symbol, self.interval, df)
        long_score = res.long_plan.strength_score if res.long_plan else 0
        short_score = res.short_plan.strength_score if res.short_plan else 0
        self._last_analysis = {
            "candle_time": closed_time,
            "primary": res.primary,
            "long_score": long_score,
            "short_score": short_score,
        }

        action, side = decide(res.primary, long_score, short_score,
                              self._side, self.min_score, self.flip_margin)

        if action == "wait":
            self._log("WAIT", f"no side ≥ {self.min_score}", long_score, short_score)
        elif action == "hold":
            self._log("HOLD", f"{self._side} · no reversal", long_score, short_score)
        elif action == "enter":
            await self._enter(res, side, long_score, short_score)
        elif action == "flip":
            await self._flip(res, side, long_score, short_score)

    def _sync_order_state(self) -> None:
        """Detect the trader closing our order at SL/TP behind our back."""
        if self._order_id is None:
            return
        trader = ManualPaperFactory.get_trader()
        if any(o.id == self._order_id for o in trader.status().open_orders):
            return
        closed = next((o for o in trader.status().closed_orders if o.id == self._order_id), None)
        if closed is not None:
            self._session_closed.append(closed)
            label = "TARGET" if closed.exit_reason == "TAKE_PROFIT" else "STOP"
            self._log(label, f"#{closed.id} closed {closed.exit_reason} "
                             f"PnL {closed.realized_pnl:+.2f}")
        else:
            self._log("STOP", f"#{self._order_id} closed (details rotated out of buffer)")
        self._order_id = None
        self._side = None

    async def _enter(self, res, side: str, ls: int, ss: int) -> None:
        plan = res.long_plan if side == "long" else res.short_plan
        if plan is None:
            self._log("WAIT", f"{side} has no trade plan", ls, ss)
            return
        try:
            order = ManualPaperFactory.get_trader().place(ManualOrderRequest(
                symbol=self.symbol, strategy="smc_autotest",
                direction="BUY" if side == "long" else "SELL",
                entry=plan.entry, stop_loss=plan.stop_loss,
                take_profit=plan.take_profit_1,
                risk_percent=self.risk_percent, interval=self.interval,
            ))
        except ValueError as exc:
            self._log("ERROR", f"enter {side} rejected: {exc}", ls, ss)
            return
        self._order_id = order.id
        self._side = side
        self._log("ENTER", f"{side} #{order.id} @ {order.entry} "
                           f"SL {order.stop_loss} TP {order.take_profit}", ls, ss)

    async def _flip(self, res, new_side: str, ls: int, ss: int) -> None:
        trader = ManualPaperFactory.get_trader()
        old_id, old_side = self._order_id, self._side
        try:
            closed = await trader.close_now(old_id, reason="FLIPPED")
            self._session_closed.append(closed)
        except ValueError as exc:
            # Already closed by the monitor between ticks — just resync.
            self._log("HOLD", f"flip aborted: {exc}", ls, ss)
            self._order_id = None
            self._side = None
            self._sync_order_state()
            return
        self._order_id = None
        self._side = None
        self._log("FLIP", f"closed {old_side} #{old_id} "
                          f"PnL {closed.realized_pnl:+.2f} → entering {new_side}", ls, ss)
        await self._enter(res, new_side, ls, ss)

    def _log(self, action: str, detail: str,
             long_score: Optional[int] = None, short_score: Optional[int] = None) -> None:
        self._events.append({
            "time": _now(),
            "action": action,
            "detail": detail,
            "long_score": long_score,
            "short_score": short_score,
        })
        print(f"[SMC autotest] {action}: {detail}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


auto_tester = SmcAutoTester()
