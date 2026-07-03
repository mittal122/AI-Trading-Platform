"""
Paper trading engine — live Binance data, virtual execution, no real orders.

Lifecycle:
  start()  → spins up asyncio background task + Binance kline WebSocket
  stop()   → cancels task, closes WebSocket
  status() → snapshot of virtual portfolio and trade log
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from binance import AsyncClient, BinanceSocketManager

from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.execution import OrderSide
from backend.app.schemas.paper import (
    PaperPosition,
    PaperStartRequest,
    PaperStatusResponse,
    PaperTrade,
)
from backend.app.services.db_service import DatabaseService
from backend.app.services.execution.execution_factory import ExecutionFactory
from backend.app.services.market_service import MarketService
from backend.app.services.portfolio.simple_portfolio import SimplePortfolio
from backend.app.services.position.position_factory import PositionFactory
from backend.app.services.risk.daily_loss_limit import DailyLossLimit
from backend.app.services.risk.drawdown_guard import DrawdownGuard
from backend.app.services.strategy.strategy_factory import StrategyFactory
from backend.app.services.trade.trade_manager import TradeManager
from backend.app.services.trade.trade_state import TradeState


class PaperTradingEngine:

    def __init__(self) -> None:
        self.is_running: bool = False
        self.config: Optional[PaperStartRequest] = None
        self.started_at: Optional[str] = None
        self.last_signal: Optional[str] = None
        self.last_price: Optional[float] = None
        self.candles_processed: int = 0
        self._trade_log: list[PaperTrade] = []

        self._portfolio: Optional[SimplePortfolio] = None
        self._strategy = None
        self._position = None
        self._execution = None
        self._trade_manager: Optional[TradeManager] = None
        self._open_trade: Optional[TradeState] = None
        self._drawdown_guard: Optional[DrawdownGuard] = None
        self._daily_loss_limit: Optional[DailyLossLimit] = None

        self._db = DatabaseService()
        self._pending_tasks: set[asyncio.Task] = set()
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, config: PaperStartRequest) -> None:
        if self.is_running:
            raise RuntimeError("Paper trading already running — call /paper/stop first")
        self.config = config
        self._init_components(config)
        self.is_running = True
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._task = asyncio.create_task(self._ws_loop())

    def stop(self) -> None:
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def status(self) -> PaperStatusResponse:
        cfg = self.config or PaperStartRequest()
        initial = self._portfolio.initial_balance if self._portfolio else cfg.initial_balance

        if self._portfolio:
            port = self._portfolio.get_state()
            cash = port.cash
            equity = port.equity
            realized = port.realized_pnl
            unrealized = port.unrealized_pnl
            total_return = port.total_return
            open_pos = self._build_position_snapshot(port)
        else:
            cash = equity = initial
            realized = unrealized = total_return = 0.0
            open_pos = None

        return PaperStatusResponse(
            is_running=self.is_running,
            symbol=cfg.symbol,
            interval=cfg.interval,
            strategy=cfg.strategy,
            started_at=self.started_at,
            initial_balance=initial,
            cash=round(cash, 4),
            equity=round(equity, 4),
            realized_pnl=round(realized, 4),
            unrealized_pnl=round(unrealized, 4),
            total_return=round(total_return, 4),
            open_position=open_pos,
            trade_count=len(self._trade_log),
            recent_trades=self._trade_log[-20:],
            last_signal=self.last_signal,
            last_price=self.last_price,
            candles_processed=self.candles_processed,
        )

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def _init_components(self, config: PaperStartRequest) -> None:
        self._portfolio = SimplePortfolio(initial_balance=config.initial_balance)
        self._strategy = StrategyFactory.get_strategy(config.strategy)
        self._position = PositionFactory.get_engine()
        self._execution = ExecutionFactory.get_engine()
        self._trade_manager = TradeManager()
        self._drawdown_guard = DrawdownGuard()
        self._daily_loss_limit = DailyLossLimit()
        self._open_trade = None
        self._trade_log = []
        self.candles_processed = 0
        self.last_signal = None
        self.last_price = None

    # ------------------------------------------------------------------
    # WebSocket loop
    # ------------------------------------------------------------------

    async def _ws_loop(self) -> None:
        client = await AsyncClient.create()
        bm = BinanceSocketManager(client)
        symbol = self.config.symbol.upper()
        interval = self.config.interval

        print(f"[Paper] WebSocket connected — {symbol} {interval}")

        try:
            async with bm.kline_socket(symbol=symbol, interval=interval) as stream:
                while self.is_running:
                    try:
                        msg = await asyncio.wait_for(stream.recv(), timeout=60.0)
                    except asyncio.TimeoutError:
                        continue

                    if msg and msg.get("k", {}).get("x"):
                        await self._on_candle_close(msg["k"])

        except asyncio.CancelledError:
            print("[Paper] WebSocket task cancelled")
        except Exception as exc:
            print(f"[Paper] WebSocket error: {exc}")
            self.is_running = False
        finally:
            await client.close_connection()
            print("[Paper] WebSocket closed")

    async def _on_candle_close(self, kline: dict) -> None:
        symbol = self.config.symbol
        interval = self.config.interval

        market = await asyncio.to_thread(
            MarketService().get_market_data,
            symbol=symbol,
            interval=interval,
            limit=200,
        )

        current_price = float(kline["c"])
        self.last_price = current_price
        self.candles_processed += 1

        signal = self._strategy.generate_signal(
            market=market,
            symbol=symbol,
            interval=interval,
        )
        self.last_signal = signal.direction.value
        self._portfolio.update_market_price(signal.entry)
        portfolio = self._portfolio.get_state()
        equity = portfolio.equity

        dd_ok, dd_action = self._drawdown_guard.check(equity)
        if dd_action == "CLOSE_ALL" and self._open_trade is not None:
            self._force_close(signal, portfolio, "DRAWDOWN_CLOSE_ALL")
            return

        daily_ok = self._daily_loss_limit.can_trade(equity)

        if (
            signal.direction.value == "BUY"
            and portfolio.position_quantity == 0
            and dd_ok
            and daily_ok
        ):
            self._open_position(signal, portfolio, equity)

        elif self._open_trade is not None and self._trade_manager.should_exit(
            signal, portfolio, self._open_trade, atr=signal.atr or 0.0,
            high=float(market.iloc[-1]["high"]), low=float(market.iloc[-1]["low"]),
        ):
            reason = self._trade_manager.last_exit_reason or "SIGNAL_REVERSAL"
            exit_price = self._trade_manager.last_exit_price or signal.entry
            if reason == "PARTIAL_EXIT":
                self._partial_close(signal, portfolio, exit_price)
            else:
                self._full_close(signal, portfolio, reason, exit_price)

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def _open_position(self, signal, portfolio, equity: float) -> None:
        position = self._position.calculate(
            account_equity=equity,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            risk_percent=1.0,
        )

        max_value = equity * strategy_config.MAX_POSITION_EQUITY_PCT
        capped_qty = (
            min(position.quantity, max_value / signal.entry)
        )

        quantity = self._execution.calculate_affordable_quantity(
            cash=portfolio.cash,
            price=signal.entry,
            requested_quantity=capped_qty,
        )
        if quantity <= 0:
            return

        execution = self._execution.execute(
            side=OrderSide.BUY,
            price=signal.entry,
            quantity=quantity,
        )
        self._portfolio.buy(execution)

        self._open_trade = TradeState(
            entry_price=execution.executed_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            quantity=execution.quantity,
            entry_timestamp=signal.timestamp,
            peak_price=execution.executed_price,
            atr_at_entry=signal.atr or 0.0,
        )

        self._log_trade("BUY", execution.executed_price, execution.quantity, 0.0, "OPEN")
        print(f"[Paper] BUY  {execution.quantity:.6f} @ {execution.executed_price:.2f}")

    def _partial_close(self, signal, portfolio, exit_price: float = None) -> None:
        partial_qty = self._open_trade.quantity * 0.5
        execution = self._execution.execute(
            side=OrderSide.SELL,
            price=exit_price if exit_price is not None else signal.entry,
            quantity=partial_qty,
        )
        self._portfolio.sell(execution)
        pnl = (execution.executed_price - self._open_trade.entry_price) * partial_qty
        self._daily_loss_limit.record_pnl(pnl)
        self._log_trade("SELL", execution.executed_price, partial_qty, pnl, "PARTIAL_EXIT")
        self._persist_trade(
            entry_price=self._open_trade.entry_price,
            exit_price=execution.executed_price,
            quantity=partial_qty,
            pnl=pnl,
            reason="PARTIAL_EXIT",
            entry_timestamp=self._open_trade.entry_timestamp,
        )
        self._open_trade.quantity -= partial_qty
        print(f"[Paper] PARTIAL_EXIT {partial_qty:.6f} @ {execution.executed_price:.2f} PnL={pnl:.2f}")

    def _full_close(self, signal, portfolio, reason: str, exit_price: float = None) -> None:
        execution = self._execution.execute(
            side=OrderSide.SELL,
            price=exit_price if exit_price is not None else signal.entry,
            quantity=portfolio.position_quantity,
        )
        self._portfolio.sell(execution)
        pnl = (execution.executed_price - self._open_trade.entry_price) * execution.quantity
        self._daily_loss_limit.record_pnl(pnl)
        self._log_trade("SELL", execution.executed_price, execution.quantity, pnl, reason)
        self._persist_trade(
            entry_price=self._open_trade.entry_price,
            exit_price=execution.executed_price,
            quantity=execution.quantity,
            pnl=pnl,
            reason=reason,
            entry_timestamp=self._open_trade.entry_timestamp,
        )
        print(f"[Paper] {reason} {execution.quantity:.6f} @ {execution.executed_price:.2f} PnL={pnl:.2f}")
        self._open_trade = None

    def _force_close(self, signal, portfolio, reason: str) -> None:
        if portfolio.position_quantity > 0:
            self._full_close(signal, portfolio, reason)
        else:
            self._open_trade = None
        print(f"[Paper] [RISK] {reason}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log_trade(self, side: str, price: float, qty: float, pnl: float, reason: str) -> None:
        self._trade_log.append(
            PaperTrade(
                side=side,
                price=round(price, 4),
                quantity=round(qty, 6),
                pnl=round(pnl, 4),
                reason=reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def _persist_trade(
        self,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        reason: str,
        entry_timestamp: str,
    ) -> None:
        """Persist a closed trade to the DB (fire-and-forget, GC-safe)."""
        coro = self._db.save_trade(
            symbol=self.config.symbol,
            strategy=self.config.strategy,
            mode="PAPER",
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            pnl=pnl,
            exit_reason=reason,
            entry_timestamp=entry_timestamp,
            direction="BUY",
        )
        task = asyncio.create_task(self._safe_persist(coro))
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    @staticmethod
    async def _safe_persist(coro) -> None:
        try:
            await coro
        except Exception as exc:  # never let DB errors break the trading loop
            print(f"[Paper] trade persist failed: {exc}")

    def _build_position_snapshot(self, port) -> Optional[PaperPosition]:
        if port.position_quantity <= 0 or self._open_trade is None:
            return None
        return PaperPosition(
            symbol=self.config.symbol,
            direction="BUY",
            entry_price=self._open_trade.entry_price,
            quantity=port.position_quantity,
            current_price=port.market_price,
            stop_loss=self._open_trade.stop_loss,
            take_profit=self._open_trade.take_profit,
            unrealized_pnl=round(port.unrealized_pnl, 4),
            candles_held=self._open_trade.candles_held,
        )


# Module-level singleton
_engine = PaperTradingEngine()


class PaperFactory:

    @staticmethod
    def get_engine() -> PaperTradingEngine:
        return _engine
