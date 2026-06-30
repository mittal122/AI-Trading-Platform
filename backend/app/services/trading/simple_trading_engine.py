from backend.app.schemas.execution import OrderSide
from backend.app.core.strategy_config import strategy_config
from backend.app.services.strategy.strategy_factory import StrategyFactory
from backend.app.services.position.position_factory import PositionFactory
from backend.app.services.trade.trade_manager import TradeManager
from backend.app.services.trade.trade_recorder import TradeRecorder
from backend.app.services.execution.execution_factory import ExecutionFactory
from backend.app.services.portfolio.portfolio_factory import PortfolioFactory
from backend.app.services.trading.base_trading_engine import BaseTradingEngine
from backend.app.services.trade.trade_state import TradeState
from backend.app.services.risk.drawdown_guard import DrawdownGuard
from backend.app.services.risk.daily_loss_limit import DailyLossLimit


class SimpleTradingEngine(BaseTradingEngine):

    def __init__(
        self,
        strategy: str = "rsi",
    ):

        self.trade_manager = TradeManager()
        self.trade_recorder = TradeRecorder()
        self.open_trade = None

        self.strategy = StrategyFactory.get_strategy(strategy)
        self.position = PositionFactory.get_engine()
        self.execution = ExecutionFactory.get_engine()
        self.portfolio = PortfolioFactory.get_engine()

        self.drawdown_guard = DrawdownGuard()
        self.daily_loss_limit = DailyLossLimit()

    def process(
        self,
        market,
        symbol,
        interval,
    ):

        signal = self.strategy.generate_signal(
            market=market,
            symbol=symbol,
            interval=interval,
        )
        print(
            f"{signal.timestamp} | "
            f"{signal.direction.value} | "
            f"Price={signal.entry:.2f}"
        )

        self.portfolio.update_market_price(signal.entry)
        portfolio = self.portfolio.get_state()
        equity = portfolio.equity

        # -----------------------------------
        # Risk gate checks
        # -----------------------------------

        dd_ok, dd_action = self.drawdown_guard.check(equity)

        if dd_action == "CLOSE_ALL" and self.open_trade is not None:
            self._force_close(signal, portfolio, reason="DRAWDOWN_CLOSE_ALL")
            return self.portfolio.get_state()

        daily_ok = self.daily_loss_limit.can_trade(equity)

        # -----------------------------------
        # BUY
        # -----------------------------------

        if (
            signal.direction.value == "BUY"
            and portfolio.position_quantity == 0
            and dd_ok
            and daily_ok
        ):

            position = self.position.calculate(
                account_equity=equity,
                entry=signal.entry,
                stop_loss=signal.stop_loss,
                risk_percent=1.0,
            )

            # Cap position at 5% of equity
            max_position_value = equity * strategy_config.MAX_POSITION_EQUITY_PCT
            if position.position_value > max_position_value:
                capped_qty = max_position_value / signal.entry
                position_value = max_position_value
            else:
                capped_qty = position.quantity
                position_value = position.position_value

            quantity = self.execution.calculate_affordable_quantity(
                cash=portfolio.cash,
                price=signal.entry,
                requested_quantity=capped_qty,
            )

            if quantity > 0:

                execution = self.execution.execute(
                    side=OrderSide.BUY,
                    price=signal.entry,
                    quantity=quantity,
                )

                self.portfolio.buy(execution)

                self.trade_recorder.open_trade(
                    entry_price=execution.executed_price,
                    quantity=execution.quantity,
                )

                self.open_trade = TradeState(
                    entry_price=execution.executed_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    quantity=execution.quantity,
                    entry_timestamp=signal.timestamp,
                    peak_price=execution.executed_price,
                    atr_at_entry=signal.atr or 0.0,
                )

                print(
                    f"BUY  | {execution.executed_price:.2f} | Qty: {execution.quantity:.6f} | "
                    f"Capped at {strategy_config.MAX_POSITION_EQUITY_PCT * 100:.0f}% equity"
                )

        # -----------------------------------
        # EXIT check (partial or full)
        # -----------------------------------

        elif self.open_trade is not None and self.trade_manager.should_exit(
            signal,
            portfolio,
            self.open_trade,
            atr=signal.atr or 0.0,
        ):

            reason = self.trade_manager.last_exit_reason or "SIGNAL_REVERSAL"

            if reason == "PARTIAL_EXIT":
                self._partial_close(signal, portfolio)
            else:
                self._full_close(signal, portfolio, reason)

        return self.portfolio.get_state()

    def _partial_close(self, signal, portfolio):
        """Close 50% of position at 1:1 RR target."""
        partial_qty = self.open_trade.quantity * 0.5

        execution = self.execution.execute(
            side=OrderSide.SELL,
            price=signal.entry,
            quantity=partial_qty,
        )

        self.portfolio.sell(execution)

        pnl = (execution.executed_price - self.open_trade.entry_price) * partial_qty
        self.daily_loss_limit.record_pnl(pnl)

        self.open_trade.quantity -= partial_qty

        print(
            f"PARTIAL_EXIT | {execution.executed_price:.2f} | "
            f"Closed 50% ({partial_qty:.6f}) | Remaining: {self.open_trade.quantity:.6f}"
        )

    def _full_close(self, signal, portfolio, reason: str):
        """Close full open position."""
        execution = self.execution.execute(
            side=OrderSide.SELL,
            price=signal.entry,
            quantity=portfolio.position_quantity,
        )

        self.portfolio.sell(execution)

        pnl = (execution.executed_price - self.open_trade.entry_price) * execution.quantity
        self.daily_loss_limit.record_pnl(pnl)

        self.trade_recorder.close_trade(exit_price=execution.executed_price)

        print(f"{reason} | {execution.executed_price:.2f} | Qty: {execution.quantity:.6f}")

        self.open_trade = None

    def _force_close(self, signal, portfolio, reason: str):
        """Force close due to risk system override."""
        if portfolio.position_quantity > 0:
            self._full_close(signal, portfolio, reason)
        else:
            self.open_trade = None
        print(f"[RISK] {reason} — position force-closed")
