"""
Manual paper trader — one-click "place this signal as a paper trade".

Unlike PaperTradingEngine (auto-bot that generates its own signals), this opens
a single virtual position from an explicit entry/stop_loss/take_profit and then
monitors live price, closing automatically when SL or TP is hit.

Flow:
  place(req) → size position by risk% of virtual balance → open OPEN order
             → spawn background monitor task (polls live price every 10s)
  monitor    → price hits SL or TP → close, book PnL, persist to DB (mode=PAPER)
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.paper import ManualOrder, ManualOrderRequest, ManualPaperStatus
from backend.app.services.db_service import DatabaseService
from backend.app.services.market_service import MarketService
from backend.app.services.position.position_factory import PositionFactory

_POLL_SECONDS = 10


class ManualPaperTrader:

    def __init__(self, starting_balance: float = 10000.0) -> None:
        self._starting_balance = starting_balance
        self.balance = starting_balance
        self.realized_pnl = 0.0
        self._open: dict[int, ManualOrder] = {}
        self._closed: list[ManualOrder] = []
        self._next_id = 1
        self._position = PositionFactory.get_engine()
        self._db = DatabaseService()
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place(self, req: ManualOrderRequest) -> ManualOrder:
        direction = req.direction.upper()
        if direction not in ("BUY", "SELL"):
            raise ValueError("direction must be BUY or SELL")
        self._validate_levels(direction, req.entry, req.stop_loss, req.take_profit)

        sized = self._position.calculate(
            account_equity=self.balance,
            entry=req.entry,
            stop_loss=req.stop_loss,
            risk_percent=req.risk_percent,
        )
        max_value = self.balance * strategy_config.MAX_POSITION_EQUITY_PCT
        quantity = min(sized.quantity, max_value / req.entry)
        if quantity <= 0:
            raise ValueError("Computed quantity is zero — check balance or stop distance")

        order = ManualOrder(
            id=self._next_id,
            symbol=req.symbol.upper(),
            strategy=req.strategy,
            direction=direction,
            entry=round(req.entry, 4),
            stop_loss=round(req.stop_loss, 4),
            take_profit=round(req.take_profit, 4),
            quantity=round(quantity, 8),
            status="OPEN",
            current_price=req.entry,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            opened_at=datetime.now(timezone.utc).isoformat(),
        )
        self._next_id += 1
        self._open[order.id] = order

        task = asyncio.create_task(self._monitor(order, req.symbol, req.interval))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        print(f"[Manual] OPEN #{order.id} {direction} {order.quantity:.6f} {order.symbol} "
              f"@ {order.entry} SL={order.stop_loss} TP={order.take_profit}")
        return order

    def status(self) -> ManualPaperStatus:
        # This trader settles PnL on close (balance is never debited when a
        # position opens), so equity = balance + open unrealized PnL. The
        # previous `balance + quantity*price` added the full position
        # NOTIONAL on top of an undebited balance — opening a $500 position
        # instantly showed +$500 equity out of thin air.
        open_upnl = sum(o.unrealized_pnl for o in self._open.values())
        equity = self.balance + open_upnl
        return ManualPaperStatus(
            balance=round(self.balance, 4),
            equity=round(equity, 4),
            realized_pnl=round(self.realized_pnl, 4),
            open_count=len(self._open),
            open_orders=list(self._open.values()),
            closed_orders=self._closed[-20:],
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_levels(direction: str, entry: float, sl: float, tp: float) -> None:
        if direction == "BUY" and not (sl < entry < tp):
            raise ValueError("BUY requires stop_loss < entry < take_profit")
        if direction == "SELL" and not (tp < entry < sl):
            raise ValueError("SELL requires take_profit < entry < stop_loss")

    def _pnl(self, order: ManualOrder, price: float) -> float:
        if order.direction == "BUY":
            return (price - order.entry) * order.quantity
        return (order.entry - price) * order.quantity

    def _hit(self, order: ManualOrder, price: float) -> Optional[str]:
        if order.direction == "BUY":
            if price <= order.stop_loss:
                return "STOP_LOSS"
            if price >= order.take_profit:
                return "TAKE_PROFIT"
        else:  # SELL
            if price >= order.stop_loss:
                return "STOP_LOSS"
            if price <= order.take_profit:
                return "TAKE_PROFIT"
        return None

    async def _latest_price(self, symbol: str, interval: str) -> float:
        df = await asyncio.to_thread(
            MarketService().get_market_data,
            symbol=symbol,
            interval=interval,
            limit=1,
        )
        return float(df.iloc[-1]["close"])

    async def _monitor(self, order: ManualOrder, symbol: str, interval: str) -> None:
        try:
            while order.status == "OPEN":
                await asyncio.sleep(_POLL_SECONDS)
                try:
                    price = await self._latest_price(symbol, interval)
                except Exception as exc:
                    print(f"[Manual] #{order.id} price fetch failed: {exc}")
                    continue

                order.current_price = round(price, 4)
                order.unrealized_pnl = round(self._pnl(order, price), 4)

                reason = self._hit(order, price)
                if reason:
                    await self._close(order, price, reason)
                    return
        except asyncio.CancelledError:
            pass

    async def _close(self, order: ManualOrder, price: float, reason: str) -> None:
        pnl = self._pnl(order, price)
        self.balance += pnl
        self.realized_pnl += pnl

        order.status = "CLOSED"
        order.current_price = round(price, 4)
        order.exit_price = round(price, 4)
        order.exit_reason = reason
        order.unrealized_pnl = 0.0
        order.realized_pnl = round(pnl, 4)
        order.closed_at = datetime.now(timezone.utc).isoformat()

        self._open.pop(order.id, None)
        self._closed.append(order)

        try:
            await self._db.save_trade(
                symbol=order.symbol,
                strategy=order.strategy,
                mode="PAPER",
                entry_price=order.entry,
                exit_price=price,
                quantity=order.quantity,
                pnl=pnl,
                exit_reason=reason,
                entry_timestamp=order.opened_at,
                direction=order.direction,
            )
        except Exception as exc:
            print(f"[Manual] #{order.id} persist failed: {exc}")

        print(f"[Manual] CLOSE #{order.id} {reason} @ {price} PnL={pnl:.2f}")


# Module-level singleton
_trader = ManualPaperTrader()


class ManualPaperFactory:

    @staticmethod
    def get_trader() -> ManualPaperTrader:
        return _trader
