"""
LiveTradingEngine — real or dry-run Binance order execution.

Start with dry_run=True (default) to verify strategy logic before going live.
Set dry_run=False only when BINANCE_API_KEY + BINANCE_SECRET are configured.

Emergency stop: cancels all open Binance orders and market-sells the open position.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from binance import AsyncClient, BinanceSocketManager

from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.execution import OrderSide
from backend.app.schemas.live_trading import LiveStartRequest, LiveStatusResponse
from backend.app.schemas.paper import PaperPosition
from backend.app.services.execution.binance_execution import BinanceExecution
from backend.app.services.market_service import MarketService
from backend.app.services.portfolio.simple_portfolio import SimplePortfolio
from backend.app.services.position.position_factory import PositionFactory
from backend.app.services.risk.daily_loss_limit import DailyLossLimit
from backend.app.services.risk.drawdown_guard import DrawdownGuard
from backend.app.services.strategy.strategy_factory import StrategyFactory
from backend.app.services.trade.trade_manager import TradeManager
from backend.app.services.trade.trade_state import TradeState


class LiveTradingEngine:

    def __init__(self) -> None:
        self.is_running: bool = False
        self.emergency_stopped: bool = False
        self.config: Optional[LiveStartRequest] = None
        self.started_at: Optional[str] = None
        self.last_signal: Optional[str] = None
        self.last_price: Optional[float] = None
        self.candles_processed: int = 0

        self._portfolio: Optional[SimplePortfolio] = None
        self._strategy = None
        self._position = None
        self._execution: Optional[BinanceExecution] = None
        self._trade_manager: Optional[TradeManager] = None
        self._open_trade: Optional[TradeState] = None
        self._drawdown_guard: Optional[DrawdownGuard] = None
        self._daily_loss_limit: Optional[DailyLossLimit] = None
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, config: LiveStartRequest) -> None:
        if self.is_running:
            raise RuntimeError("Live trading already running — call /trading/stop first")
        if self.emergency_stopped:
            raise RuntimeError(
                "Engine halted by emergency stop. Restart the application to resume."
            )
        self.config = config
        self._init_components(config)
        self.is_running = True
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._task = asyncio.create_task(self._ws_loop())
        mode = "DRY RUN" if config.dry_run else "*** LIVE ***"
        print(f"[Live] Started — {config.symbol} {config.interval} [{mode}]")

    async def stop(self, emergency: bool = False) -> dict:
        self.is_running = False
        orders_cancelled = 0

        if self._task and not self._task.done():
            self._task.cancel()

        if emergency:
            self.emergency_stopped = True
            if self._execution:
                orders_cancelled = await asyncio.to_thread(
                    self._execution.cancel_all_open_orders
                )
            if self._open_trade and self._portfolio:
                portfolio = self._portfolio.get_state()
                if portfolio.position_quantity > 0:
                    await self._market_close(portfolio, "EMERGENCY_STOP")

        print(f"[Live] {'Emergency ' if emergency else ''}stopped. Orders cancelled: {orders_cancelled}")
        return {"orders_cancelled": orders_cancelled}

    def status(self) -> LiveStatusResponse:
        cfg = self.config or LiveStartRequest()

        if self._portfolio:
            port = self._portfolio.get_state()
            cash = port.cash
            equity = port.equity
            realized = port.realized_pnl
            unrealized = port.unrealized_pnl
            total_return = port.total_return
            open_pos = self._build_position_snapshot(port)
        else:
            cash = equity = cfg.initial_balance
            realized = unrealized = total_return = 0.0
            open_pos = None

        orders = self._execution.get_orders() if self._execution else []

        return LiveStatusResponse(
            is_running=self.is_running,
            emergency_stopped=self.emergency_stopped,
            dry_run=cfg.dry_run,
            symbol=cfg.symbol,
            interval=cfg.interval,
            strategy=cfg.strategy,
            started_at=self.started_at,
            initial_balance=cfg.initial_balance,
            cash=round(cash, 4),
            equity=round(equity, 4),
            realized_pnl=round(realized, 4),
            unrealized_pnl=round(unrealized, 4),
            total_return=round(total_return, 4),
            open_position=open_pos,
            order_count=len(orders),
            recent_orders=orders[-20:],
            last_signal=self.last_signal,
            last_price=self.last_price,
            candles_processed=self.candles_processed,
        )

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def _init_components(self, config: LiveStartRequest) -> None:
        self._portfolio = SimplePortfolio(initial_balance=config.initial_balance)
        self._strategy = StrategyFactory.get_strategy(config.strategy)
        self._position = PositionFactory.get_engine()
        self._execution = BinanceExecution(symbol=config.symbol, dry_run=config.dry_run)
        self._trade_manager = TradeManager()
        self._drawdown_guard = DrawdownGuard()
        self._daily_loss_limit = DailyLossLimit()
        self._open_trade = None
        self.candles_processed = 0
        self.last_signal = None
        self.last_price = None

    # ------------------------------------------------------------------
    # WebSocket loop
    # ------------------------------------------------------------------

    async def _ws_loop(self) -> None:
        api_key = None if self.config.dry_run else None  # public WS, no key needed
        client = await AsyncClient.create()
        bm = BinanceSocketManager(client)
        symbol = self.config.symbol.upper()
        interval = self.config.interval

        print(f"[Live] WebSocket connected — {symbol} {interval}")

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
            print("[Live] WebSocket task cancelled")
        except Exception as exc:
            print(f"[Live] WebSocket error: {exc}")
            self.is_running = False
        finally:
            await client.close_connection()
            print("[Live] WebSocket closed")

    async def _on_candle_close(self, kline: dict) -> None:
        symbol = self.config.symbol
        interval = self.config.interval

        market = await asyncio.to_thread(
            MarketService().get_market_data,
            symbol=symbol,
            interval=interval,
            limit=200,
        )

        self.last_price = float(kline["c"])
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
            await self._market_close(portfolio, "DRAWDOWN_CLOSE_ALL")
            return

        daily_ok = self._daily_loss_limit.can_trade(equity)

        if (
            signal.direction.value == "BUY"
            and portfolio.position_quantity == 0
            and dd_ok
            and daily_ok
        ):
            await self._open_position(signal, portfolio, equity)

        elif self._open_trade is not None and self._trade_manager.should_exit(
            signal, portfolio, self._open_trade, atr=signal.atr or 0.0,
            high=float(market.iloc[-1]["high"]), low=float(market.iloc[-1]["low"]),
        ):
            reason = self._trade_manager.last_exit_reason or "SIGNAL_REVERSAL"
            exit_price = self._trade_manager.last_exit_price or signal.entry
            if reason == "PARTIAL_EXIT":
                await self._partial_close(signal, portfolio, exit_price)
            else:
                await self._market_close(portfolio, reason, price_override=exit_price)

    # ------------------------------------------------------------------
    # Position management (async wrappers for thread-safe order placement)
    # ------------------------------------------------------------------

    async def _open_position(self, signal, portfolio, equity: float) -> None:
        position = self._position.calculate(
            account_equity=equity,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            risk_percent=1.0,
        )
        max_value = equity * strategy_config.MAX_POSITION_EQUITY_PCT
        capped_qty = min(position.quantity, max_value / signal.entry)

        quantity = self._execution.calculate_affordable_quantity(
            cash=portfolio.cash,
            price=signal.entry,
            requested_quantity=capped_qty,
        )
        if quantity <= 0:
            return

        execution = await asyncio.to_thread(
            self._execution.execute,
            OrderSide.BUY,
            signal.entry,
            quantity,
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
        mode = "[DRY]" if self.config.dry_run else "[LIVE]"
        print(f"{mode} BUY  {execution.quantity:.6f} @ {execution.executed_price:.2f}")

    async def _partial_close(self, signal, portfolio, exit_price: float = None) -> None:
        partial_qty = self._open_trade.quantity * 0.5
        execution = await asyncio.to_thread(
            self._execution.execute,
            OrderSide.SELL,
            exit_price if exit_price is not None else signal.entry,
            partial_qty,
        )
        self._portfolio.sell(execution)
        pnl = (execution.executed_price - self._open_trade.entry_price) * partial_qty
        self._daily_loss_limit.record_pnl(pnl)
        self._open_trade.quantity -= partial_qty
        mode = "[DRY]" if self.config.dry_run else "[LIVE]"
        print(f"{mode} PARTIAL_EXIT {partial_qty:.6f} @ {execution.executed_price:.2f} PnL={pnl:.2f}")

    async def _market_close(self, portfolio, reason: str, price_override: float = 0.0) -> None:
        qty = portfolio.position_quantity
        if qty <= 0:
            self._open_trade = None
            return

        price = price_override or self.last_price or self._open_trade.entry_price
        execution = await asyncio.to_thread(
            self._execution.execute,
            OrderSide.SELL,
            price,
            qty,
        )
        self._portfolio.sell(execution)
        pnl = (execution.executed_price - self._open_trade.entry_price) * execution.quantity
        self._daily_loss_limit.record_pnl(pnl)
        mode = "[DRY]" if self.config.dry_run else "[LIVE]"
        print(f"{mode} {reason} {execution.quantity:.6f} @ {execution.executed_price:.2f} PnL={pnl:.2f}")
        self._open_trade = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
_engine = LiveTradingEngine()


class LiveTradingFactory:

    @staticmethod
    def get_engine() -> LiveTradingEngine:
        return _engine
