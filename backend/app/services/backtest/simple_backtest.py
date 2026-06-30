from backend.app.schemas.backtest import (
    BacktestResult,
    EquityPoint,
)

from backend.app.services.backtest.base_backtest import (
    BaseBacktest,
)

from backend.app.services.backtest.window import (
    WindowGenerator,
)

from backend.app.services.market_service import (
    MarketService,
)

from backend.app.schemas.execution import (
    OrderSide,
)

from backend.app.services.trading.simple_trading_engine import (
    SimpleTradingEngine,
)


class SimpleBacktest(BaseBacktest):

    def __init__(self):

        self.market = MarketService()

    def run(
        self,
        strategy: str = "rsi",
        symbol: str = "BTCUSDT",
        interval: str = "5m",
        limit: int = 500,
    ) -> BacktestResult:

        engine = SimpleTradingEngine(
            strategy=strategy,
        )

        market = self.market.get_market_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        equity_curve = []

        candle = 0

        for window in WindowGenerator.generate(
            market,
        ):

            portfolio = engine.process(
                market=window,
                symbol=symbol,
                interval=interval,
            )

            last = window.iloc[-1]

            equity_curve.append(
                EquityPoint(
                    candle=candle,
                    timestamp=last["timestamps"].isoformat(),
                    equity=portfolio.equity,
                )
            )

            candle += 1

        portfolio = engine.portfolio.get_state()

        if portfolio.position_quantity > 0:

            last_price = float(
                market.iloc[-1]["close"]
            )

            execution = engine.execution.execute(
                side=OrderSide.SELL,
                price=last_price,
                quantity=portfolio.position_quantity,
            )

            engine.portfolio.sell(execution)

            engine.trade_recorder.close_trade(
                exit_price=execution.executed_price,
            )

            engine.portfolio.update_market_price(
                execution.executed_price,
            )

            print(
                f"FORCED SELL | {execution.executed_price:.2f}"
            )

        final_state = engine.portfolio.get_state()

        trades = engine.trade_recorder.get_trades()

        winning_trades = sum(
            1
            for trade in trades
            if trade.pnl > 0
        )

        losing_trades = sum(
            1
            for trade in trades
            if trade.pnl <= 0
        )

        total_trades = len(trades)

        win_rate = (
            (winning_trades / total_trades) * 100
            if total_trades > 0
            else 0.0
        )

        return BacktestResult(
            initial_balance=final_state.initial_balance,
            ending_balance=final_state.equity,
            total_return=final_state.total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            trades=trades,
            equity_curve=equity_curve,
        )