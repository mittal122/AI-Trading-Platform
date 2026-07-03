from backend.app.schemas.backtest import (
    TradeResult,
)


class TradeRecorder:

    def __init__(self):

        self.entry_price = None
        self.quantity = 0.0
        self.entry_timestamp = None

        self.trades = []

    def open_trade(
        self,
        entry_price: float,
        quantity: float,
        entry_timestamp: str = "",
    ):

        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_timestamp = entry_timestamp

    def close_trade(
        self,
        exit_price: float,
        exit_timestamp: str = "",
        candles_held: int = 0,
        exit_reason: str = "",
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
                entry_timestamp=self.entry_timestamp or "",
                exit_timestamp=exit_timestamp,
                candles_held=candles_held,
                exit_reason=exit_reason,

            )

        )

        self.entry_price = None
        self.quantity = 0.0
        self.entry_timestamp = None

    def get_trades(
        self,
    ):

        return self.trades
