from pydantic import BaseModel


class PortfolioResponse(BaseModel):

    initial_balance: float

    cash: float

    position_quantity: float

    average_entry: float

    market_price: float

    position_value: float

    realized_pnl: float

    unrealized_pnl: float

    equity: float

    total_return: float