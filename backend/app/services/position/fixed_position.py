from backend.app.schemas.position import PositionResponse

from backend.app.services.position.base_position import (
    BasePosition,
)


class FixedPosition(BasePosition):

    def __init__(
        self,
        max_exposure: float = 1.0,
        fee_buffer: float = 1.001,
    ):

        self.max_exposure = max_exposure
        self.fee_buffer = fee_buffer

    def calculate(
        self,
        account_equity: float,
        entry: float,
        stop_loss: float,
        risk_percent: float,
    ) -> PositionResponse:

        capital_at_risk = (
            account_equity
            * risk_percent
            / 100
        )

        risk_per_unit = abs(
            entry - stop_loss
        )

        if risk_per_unit == 0:

            quantity = 0.0

        else:

            quantity = (
                capital_at_risk
                / risk_per_unit
            )

        position_value = (
            quantity
            * entry
        )

        max_position_value = (
            account_equity
            * self.max_exposure
        ) / self.fee_buffer

        if position_value > max_position_value:

            position_value = max_position_value

            quantity = (
                position_value
                / entry
            )

        total_cost = (
            position_value
            * self.fee_buffer
        )

        if total_cost > account_equity:

            position_value = (
                account_equity
                / self.fee_buffer
            )

            quantity = (
                position_value
                / entry
            )

        utilized_capital = position_value

        available_cash = (
            account_equity
            - total_cost
        )

        leverage = (
            position_value
            / account_equity
        )

        exposure = leverage * 100

        return PositionResponse(
            account_equity=account_equity,
            risk_percent=risk_percent,
            capital_at_risk=capital_at_risk,
            quantity=quantity,
            position_value=position_value,
            utilized_capital=utilized_capital,
            available_cash=available_cash,
            leverage=leverage,
            exposure=exposure,
        )