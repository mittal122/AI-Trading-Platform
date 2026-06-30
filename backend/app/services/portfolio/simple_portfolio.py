from backend.app.schemas.portfolio import PortfolioResponse

from backend.app.services.portfolio.base_portfolio import (
    BasePortfolio,
)


class SimplePortfolio(BasePortfolio):

    def __init__(
        self,
        initial_balance: float = 10000,
    ):

        self.initial_balance = initial_balance
        self.cash = initial_balance
        self.position_quantity = 0.0
        self.average_entry = 0.0
        self.market_price = 0.0
        self.realized_pnl = 0.0

    def update_market_price(
        self,
        price: float,
    ):

        self.market_price = price

    def buy(
        self,
        execution,
    ):

        self.cash -= execution.total_cost

        self.average_entry = execution.executed_price

        self.position_quantity += execution.quantity

        self.market_price = execution.executed_price

    def sell(
        self,
        execution,
    ):

        proceeds = (
            execution.trade_value
            - execution.fee
        )

        pnl = (
            execution.executed_price
            - self.average_entry
        ) * execution.quantity

        self.cash += proceeds

        self.realized_pnl += pnl

        self.position_quantity -= execution.quantity

        self.market_price = execution.executed_price

        if self.position_quantity <= 0:

            self.position_quantity = 0.0
            self.average_entry = 0.0

    def get_state(
        self,
    ) -> PortfolioResponse:

        position_value = (
            self.position_quantity
            * self.market_price
        )

        unrealized = (
            self.market_price
            - self.average_entry
        ) * self.position_quantity

        equity = (
            self.cash
            + position_value
        )

        total_return = (
            (equity - self.initial_balance)
            / self.initial_balance
        ) * 100

        return PortfolioResponse(
            initial_balance=self.initial_balance,
            cash=self.cash,
            position_quantity=self.position_quantity,
            average_entry=self.average_entry,
            market_price=self.market_price,
            position_value=position_value,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized,
            equity=equity,
            total_return=total_return,
        )