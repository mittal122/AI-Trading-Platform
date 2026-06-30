from backend.app.schemas.execution import OrderSide

from backend.app.services.strategy.strategy_factory import (
    StrategyFactory,
)
from backend.app.services.position.position_factory import (
    PositionFactory,
)
from backend.app.services.trade.trade_manager import (
    TradeManager,
)
from backend.app.services.trade.trade_recorder import (
    TradeRecorder,
)
from backend.app.services.execution.execution_factory import (
    ExecutionFactory,
)
from backend.app.services.portfolio.portfolio_factory import (
    PortfolioFactory,
)
from backend.app.services.trading.base_trading_engine import (
    BaseTradingEngine,
)
from backend.app.services.trade.trade_state import (
    TradeState,
)


class SimpleTradingEngine(BaseTradingEngine):

    def __init__(
        self,
        strategy: str = "rsi",
    ):

        self.trade_manager = TradeManager()
        self.trade_recorder = TradeRecorder()
        self.open_trade = None

        self.strategy = StrategyFactory.get_strategy(
            strategy,
        )

        self.position = PositionFactory.get_engine()
        self.execution = ExecutionFactory.get_engine()
        self.portfolio = PortfolioFactory.get_engine()

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

        # Update latest market price
        self.portfolio.update_market_price(
            signal.entry,
        )

        portfolio = self.portfolio.get_state()

        # -----------------------------------
        # BUY
        # -----------------------------------

        if (
            signal.direction.value == "BUY"
            and portfolio.position_quantity == 0
        ):

            position = self.position.calculate(
                account_equity=portfolio.equity,
                entry=signal.entry,
                stop_loss=signal.stop_loss,
                risk_percent=1.0,
            )

            quantity = self.execution.calculate_affordable_quantity(
                cash=portfolio.cash,
                price=signal.entry,
                requested_quantity=position.quantity,
            )

            if quantity > 0:

                execution = self.execution.execute(
                    side=OrderSide.BUY,
                    price=signal.entry,
                    quantity=quantity,
                )

                self.portfolio.buy(
                    execution,
                )

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
                    f"BUY  | {execution.executed_price:.2f} | Qty: {execution.quantity:.6f}"
                )

        # -----------------------------------
        # SELL
        # -----------------------------------

        elif self.trade_manager.should_exit(
            signal,
            portfolio,
            self.open_trade,
            atr=signal.atr or 0.0,
        ):

            execution = self.execution.execute(
                side=OrderSide.SELL,
                price=signal.entry,
                quantity=portfolio.position_quantity,
            )

            self.portfolio.sell(
                execution,
            )

            self.trade_recorder.close_trade(
                exit_price=execution.executed_price,
            )

            reason = self.trade_manager.last_exit_reason or "SIGNAL_REVERSAL"

            print(
                f"{reason} | {execution.executed_price:.2f} | Qty: {execution.quantity:.6f}"
            )

            # Clear trade after logging
            self.open_trade = None

        return self.portfolio.get_state()