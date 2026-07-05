from typing import Optional

from pydantic import BaseModel


class Ticker24h(BaseModel):
    symbol: str
    last_price: float
    price_change_pct: float
    high: float
    low: float
    quote_volume: float
    trades: int


class MarketOverviewResponse(BaseModel):
    """One call powering the whole dashboard top: leaders, breadth, movers.

    Breadth counts only pairs above the volume floor — thousands of dead
    micro-caps would otherwise drown the read on real market direction.
    """
    btc: Optional[Ticker24h] = None
    eth: Optional[Ticker24h] = None
    advancers: int
    decliners: int
    avg_change_pct: float
    total_quote_volume: float
    counted_pairs: int
    top_gainers: list[Ticker24h]
    top_losers: list[Ticker24h]
    volume_leaders: list[Ticker24h]


class WatchlistResponse(BaseModel):
    tickers: list[Ticker24h]


class DepthPressureResponse(BaseModel):
    symbol: str
    bid_notional: float
    ask_notional: float
    bid_ratio: float                  # 0..1 — >0.5 means more resting bid-side notional
    best_bid: float
    best_ask: float
    biggest_bid_wall_price: float
    biggest_bid_wall_notional: float
    biggest_ask_wall_price: float
    biggest_ask_wall_notional: float
    levels: int


class BuyPressureResponse(BaseModel):
    symbol: str
    interval: str
    candles: int
    buy_ratio: float                  # taker-buy share of volume, 0..1
    recent_ratios: list[float]


class FundingResponse(BaseModel):
    symbol: str
    funding_rate: float
    funding_rate_annualized_pct: float
    mark_price: float
    next_funding_time: int


class VolumeScanRow(BaseModel):
    symbol: str
    interval: str
    time: str                         # last CLOSED candle's close time (ISO)
    ltp: float                        # last traded price (that candle's close)
    volume_window: float              # current candle volume (base asset)
    volume_average: float             # mean volume over prior `window` candles
    spike_ratio: float                # volume_window / volume_average
    orders: int                       # number_of_trades on the current candle
    avg_orders: float                 # mean trade count over the window
    max_push_volume: float            # biggest single-candle volume in the window
    max_push_ratio: float             # max_push_volume / volume_average
    error: Optional[str] = None       # set instead of the numbers if the scan failed


class VolumeScanResponse(BaseModel):
    interval: str
    window: int
    rows: list[VolumeScanRow]
