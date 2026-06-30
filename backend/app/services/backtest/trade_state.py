from dataclasses import dataclass


@dataclass
class TradeState:

    in_position: bool = False

    entry_price: float = 0.0

    quantity: float = 0.0

    entry_index: int = -1
    