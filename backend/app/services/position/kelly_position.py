from backend.app.schemas.position import PositionResponse
from backend.app.services.position.base_position import BasePosition
from backend.app.core.strategy_config import strategy_config


class KellyPosition(BasePosition):
    """
    Kelly Criterion position sizing.
    f* = (b*p - q) / b  where b=RR, p=win_rate, q=1-p
    Capped at KELLY_MAX_FRACTION of equity (default 25%).
    """

    def __init__(
        self,
        win_rate: float = strategy_config.KELLY_DEFAULT_WIN_RATE,
        max_kelly: float = strategy_config.KELLY_MAX_FRACTION,
    ):
        self.win_rate = win_rate
        self.max_kelly = max_kelly

    def calculate(
        self,
        account_equity: float,
        entry: float,
        stop_loss: float,
        risk_percent: float,
        risk_reward: float = strategy_config.KELLY_DEFAULT_RR,
    ) -> PositionResponse:

        risk_per_unit = abs(entry - stop_loss)

        # Kelly formula
        p = self.win_rate
        q = 1.0 - p
        b = risk_reward

        kelly_fraction = (b * p - q) / b if b > 0 else 0.0

        # Negative kelly = no edge; zero out
        kelly_fraction = max(kelly_fraction, 0.0)

        # Cap at max allowed
        kelly_fraction = min(kelly_fraction, self.max_kelly)

        # Also honour risk_percent as an additional cap
        risk_cap = risk_percent / 100.0
        kelly_fraction = min(kelly_fraction, risk_cap) if risk_cap > 0 else kelly_fraction

        capital_at_risk = account_equity * kelly_fraction

        quantity = capital_at_risk / risk_per_unit if risk_per_unit > 0 else 0.0

        position_value = quantity * entry

        # Cap position value at max_kelly fraction of equity (e.g. 25%)
        max_position_value = account_equity * self.max_kelly
        if position_value > max_position_value:
            position_value = max_position_value
            quantity = position_value / entry if entry > 0 else 0.0

        utilized_capital = position_value
        available_cash = account_equity - position_value
        leverage = position_value / account_equity if account_equity > 0 else 0.0
        exposure = leverage * 100

        return PositionResponse(
            account_equity=account_equity,
            risk_percent=kelly_fraction * 100,
            capital_at_risk=capital_at_risk,
            quantity=quantity,
            position_value=position_value,
            utilized_capital=utilized_capital,
            available_cash=available_cash,
            leverage=leverage,
            exposure=exposure,
        )
