"""Automated SMC signal scanner (§13).

A background scanner that runs the same SMC engine over a watchlist and stores
high-confluence *fired* setups as actionable signals. Single-operator/global
(no per-user scoping) — matches this app's paper/live engines.

Signal creation rules (§13.2):
  1. the side must have FIRED (confluence >= 70, no vetoes);
  2. scanner settings must be enabled;
  3. weekly cap: at most max_signals_per_week per rolling 7 days;
  4. dedup: no live (new/accepted) signal for the same symbol+interval+side in
     the last SCAN_DEDUP_HOURS.

Candle-close gating: a watch is only re-analyzed once a new candle has closed
since its cursor — never mid-candle.
"""

import json
from datetime import datetime, timedelta, timezone

from backend.app.core.smc_config import smc_config
from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import SmcSignal
from backend.app.db.repository.smc_repo import SmcScannerRepository
from backend.app.schemas.paper import ManualOrderRequest
from backend.app.schemas.smc import ScannerSettings, SignalOut, Side, WatchItem
from backend.app.services.market_service import MarketService
from backend.app.services.paper.manual_paper_trader import ManualPaperFactory
from backend.app.services.smc.smc_engine import analyze

cfg = smc_config


def _watch_out(w) -> WatchItem:
    return WatchItem(id=w.id, symbol=w.symbol, interval=w.interval,
                     active=bool(w.active), last_scanned_candle_time=w.last_scanned_candle_time)


def _signal_out(s) -> SignalOut:
    return SignalOut(
        id=s.id, symbol=s.symbol, interval=s.interval, side=Side(s.side),
        entry=s.entry, stop_loss=s.stop_loss, take_profit_1=s.take_profit_1,
        take_profit_2=s.take_profit_2, score=s.score, reason_note=s.reason_note,
        candle_time=s.candle_time, status=s.status, paired_trade_id=s.paired_trade_id,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )


class SmcScannerService:
    def __init__(self):
        self._market = MarketService()

    # ----- watchlist / settings -----
    async def list_watches(self) -> list[WatchItem]:
        async with AsyncSessionLocal() as s:
            return [_watch_out(w) for w in await SmcScannerRepository(s).list_watches()]

    async def add_watch(self, symbol: str, interval: str) -> WatchItem:
        async with AsyncSessionLocal() as s:
            return _watch_out(await SmcScannerRepository(s).add_watch(symbol, interval))

    async def set_active(self, watch_id: int, active: bool) -> bool:
        async with AsyncSessionLocal() as s:
            return await SmcScannerRepository(s).set_active(watch_id, active) is not None

    async def remove_watch(self, watch_id: int) -> bool:
        async with AsyncSessionLocal() as s:
            return await SmcScannerRepository(s).remove_watch(watch_id)

    async def get_settings(self) -> ScannerSettings:
        async with AsyncSessionLocal() as s:
            row = await SmcScannerRepository(s).get_settings()
            return ScannerSettings(enabled=bool(row.enabled), max_signals_per_week=row.max_signals_per_week)

    async def update_settings(self, enabled: bool, max_per_week: int) -> ScannerSettings:
        clamped = max(cfg.SCAN_MAX_PER_WEEK_MIN, min(cfg.SCAN_MAX_PER_WEEK_MAX, max_per_week))
        async with AsyncSessionLocal() as s:
            row = await SmcScannerRepository(s).update_settings(enabled, clamped)
            return ScannerSettings(enabled=bool(row.enabled), max_signals_per_week=row.max_signals_per_week)

    async def list_signals(self, limit: int = 100) -> list[SignalOut]:
        async with AsyncSessionLocal() as s:
            return [_signal_out(x) for x in await SmcScannerRepository(s).list_signals(limit)]

    # ----- the scan itself -----
    async def scan_once(self) -> dict:
        """One sweep over the active watchlist. Returns a summary."""
        scanned = created = skipped = 0
        async with AsyncSessionLocal() as s:
            repo = SmcScannerRepository(s)
            settings = await repo.get_settings()
            watches = await repo.list_watches(active_only=True)

        for w in watches:
            try:
                did_scan, made = await self._scan_watch(w, settings)
                scanned += 1 if did_scan else 0
                created += 1 if made else 0
            except Exception as exc:  # noqa: BLE001 — one bad watch never kills the sweep
                skipped += 1
                print(f"[SMC scanner] {w.symbol}/{w.interval} failed: {exc}")
        return {"active_watches": len(watches), "scanned": scanned,
                "signals_created": created, "errors": skipped, "enabled": bool(settings.enabled)}

    async def _scan_watch(self, w, settings) -> tuple[bool, bool]:
        df = self._market.get_market_data(w.symbol, w.interval, cfg.SCAN_FETCH_CANDLES)
        if df is None or len(df) < cfg.SCAN_MIN_CANDLES:
            return False, False

        # Candle-close gate: the last row is the still-forming candle; the last
        # CLOSED candle is the one before it.
        closed_time = df["timestamps"].iloc[-2].isoformat()
        if w.last_scanned_candle_time == closed_time:
            return False, False   # no new candle since last scan

        res = analyze(w.symbol, w.interval, df)   # no order flow -> walk-forward safe

        async with AsyncSessionLocal() as s:
            repo = SmcScannerRepository(s)
            await repo.update_cursor(w.id, closed_time)

            if res.primary not in ("long", "short") or not settings.enabled:
                return True, False

            plan = res.long_plan if res.primary == "long" else res.short_plan
            side = res.primary

            # weekly cap
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            if await repo.count_signals_since(week_ago) >= settings.max_signals_per_week:
                return True, False
            # dedup
            if await repo.has_live_duplicate(w.symbol, w.interval, side, cfg.SCAN_DEDUP_HOURS):
                return True, False

            signal = SmcSignal(
                symbol=w.symbol, interval=w.interval, side=side,
                entry=plan.entry, stop_loss=plan.stop_loss,
                take_profit_1=plan.take_profit_1, take_profit_2=plan.take_profit_2,
                score=plan.strength_score,
                reason_note="; ".join(res.reasons[:6]),
                score_breakdown_json=json.dumps(
                    [{"name": c.name, "raw": c.raw, "contribution": c.contribution}
                     for c in res.verdict.breakdown.components]) if res.verdict else "",
                candle_time=res.candles[-1].time,
                status="new",
            )
            await repo.save_signal(signal)
            return True, True

    # ----- lifecycle -----
    async def accept(self, signal_id: int, capital: float, risk_pct: float) -> SignalOut:
        async with AsyncSessionLocal() as s:
            repo = SmcScannerRepository(s)
            sig = await repo.get_signal(signal_id)
            if sig is None:
                raise ValueError("Signal not found")
            if sig.status != "new":
                raise ValueError("Signal is no longer pending")

            direction = "BUY" if sig.side == "long" else "SELL"
            order = ManualPaperFactory.get_trader().place(ManualOrderRequest(
                symbol=sig.symbol, strategy="smc_scanner", direction=direction,
                entry=sig.entry, stop_loss=sig.stop_loss, take_profit=sig.take_profit_1,
                risk_percent=risk_pct, interval=sig.interval,
            ))
            sig.status = "accepted"
            sig.paired_trade_id = order.id
            await repo.update_signal(sig)
            return _signal_out(sig)

    async def dismiss(self, signal_id: int) -> SignalOut:
        async with AsyncSessionLocal() as s:
            repo = SmcScannerRepository(s)
            sig = await repo.get_signal(signal_id)
            if sig is None:
                raise ValueError("Signal not found")
            if sig.status != "new":
                raise ValueError("Signal is no longer pending")
            sig.status = "dismissed"
            await repo.update_signal(sig)
            return _signal_out(sig)


scanner_service = SmcScannerService()
