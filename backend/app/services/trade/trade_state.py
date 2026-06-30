from dataclasses import dataclass, field


@dataclass
class TradeState:

    entry_price: float

    stop_loss: float

    take_profit: float

    quantity: float

    entry_timestamp: str

    is_open: bool = True

    # Trailing stop / time exit tracking
    peak_price: float = 0.0
    candles_held: int = 0
    atr_at_entry: float = 0.0
    trailing_stop_active: bool = False