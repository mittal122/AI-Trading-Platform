from pydantic import BaseModel


class PositionResponse(BaseModel):

    account_equity: float

    risk_percent: float

    capital_at_risk: float

    quantity: float

    position_value: float

    utilized_capital: float

    available_cash: float

    leverage: float

    exposure: float