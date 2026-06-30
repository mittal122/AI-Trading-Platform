from enum import Enum

from pydantic import BaseModel


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExecutionResponse(BaseModel):

    side: OrderSide

    requested_price: float

    executed_price: float

    quantity: float

    trade_value: float

    fee: float

    slippage_cost: float

    total_cost: float