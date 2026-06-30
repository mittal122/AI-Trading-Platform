from backend.app.schemas.risk import (
    Direction,
    RiskResponse,
)

from backend.app.services.risk.base_risk import (
    BaseRisk,
)


class ATRRisk(BaseRisk):

    def __init__(
        self,
        stop_multiple: float = 2.0,
        reward_multiple: float = 2.0,
    ):

        self.stop_multiple = stop_multiple
        self.reward_multiple = reward_multiple

    def calculate(
        self,
        direction: Direction,
        entry: float,
        atr: float,
    ) -> RiskResponse:

        risk = atr * self.stop_multiple

        if direction == Direction.LONG:

            stop_loss = entry - risk
            take_profit = (
                entry
                + risk * self.reward_multiple
            )

        elif direction == Direction.SHORT:

            stop_loss = entry + risk
            take_profit = (
                entry
                - risk * self.reward_multiple
            )

        else:

            stop_loss = entry
            take_profit = entry

        reward = abs(
            take_profit - entry
        )

        return RiskResponse(
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_per_unit=risk,
            reward_per_unit=reward,
            risk_reward=(
                reward / risk
                if risk > 0
                else 0.0
            ),
        )