from backend.app.schemas.execution import (
    ExecutionResponse,
    OrderSide,
)

from backend.app.services.execution.base_execution import (
    BaseExecution,
)


class SimpleExecution(BaseExecution):

    def __init__(
        self,
        fee_percent: float = 0.10,
        slippage_percent: float = 0.05,
    ):

        self.fee_percent = fee_percent
        self.slippage_percent = slippage_percent

    def calculate_affordable_quantity(
        self,
        cash: float,
        price: float,
        requested_quantity: float,
    ) -> float:
        """
        Return the largest quantity that can be bought
        without exceeding available cash after slippage
        and fees.
        """

        executed_price = (
            price
            * (1 + self.slippage_percent / 100)
        )

        cost_per_unit = (
            executed_price
            * (1 + self.fee_percent / 100)
        )

        if cost_per_unit <= 0:
            return 0.0

        affordable_quantity = (
            cash
            / cost_per_unit
        )

        return min(
            requested_quantity,
            affordable_quantity,
        )

    def execute(
        self,
        side: OrderSide,
        price: float,
        quantity: float,
    ) -> ExecutionResponse:

        if side == OrderSide.BUY:

            executed_price = (
                price
                * (1 + self.slippage_percent / 100)
            )

        else:

            executed_price = (
                price
                * (1 - self.slippage_percent / 100)
            )

        trade_value = (
            executed_price
            * quantity
        )

        fee = (
            trade_value
            * self.fee_percent
            / 100
        )

        slippage_cost = abs(
            executed_price - price
        ) * quantity

        total_cost = (
            trade_value + fee
            if side == OrderSide.BUY
            else trade_value - fee
        )

        return ExecutionResponse(
            side=side,
            requested_price=price,
            executed_price=executed_price,
            quantity=quantity,
            trade_value=trade_value,
            fee=fee,
            slippage_cost=slippage_cost,
            total_cost=total_cost,
        )