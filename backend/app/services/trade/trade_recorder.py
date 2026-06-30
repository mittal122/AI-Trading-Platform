from backend.app.schemas.backtest import (
    TradeResult,
)


class TradeRecorder:

    def __init__(self):

        self.entry_price = None
        self.quantity = 0.0

        self.trades = []

    def open_trade(
        self,
        entry_price: float,
        quantity: float,
    ):

        self.entry_price = entry_price
        self.quantity = quantity

    def close_trade(
        self,
        exit_price: float,
    ):

        if self.entry_price is None:

            return

        pnl = (
            exit_price
            - self.entry_price
        ) * self.quantity

        return_percent = (
            (
                exit_price
                - self.entry_price
            )
            / self.entry_price
        ) * 100

        self.trades.append(

            TradeResult(

                entry_price=self.entry_price,
                exit_price=exit_price,
                quantity=self.quantity,
                pnl=pnl,
                return_percent=return_percent,

            )

        )

        self.entry_price = None
        self.quantity = 0.0

    def get_trades(
        self,
    ):

        return self.trades