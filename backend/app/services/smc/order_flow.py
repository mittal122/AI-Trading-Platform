"""Order-flow snapshot (§8).

Combines two live microstructure views into one OrderFlow:
  * Resting book — only levels within max(1% of price, 2xATR) of price; in-band
    bid/ask volume -> imbalance; walls = levels holding >= 4x the mean side
    volume (top 3 per side, with distance-%).
  * Taker aggression — aggregate trades classified buy/sell by the buyer-is-maker
    flag; delta = buyVol - sellVol, cvdRatio = delta/total. Non-fatal if missing.

The live analysis path calls this with atr=0, so the band reduces to a plain
1%-of-price band (the 2xATR term is inert there).

compute_order_flow() is a pure function (network-free, unit-testable);
fetch_order_flow() wires it to MarketService.
"""

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import OrderFlow, PressureLabel

cfg = smc_config


def _walls(levels: list[tuple[float, float]], price: float) -> list[dict]:
    if not levels:
        return []
    mean_q = sum(q for _, q in levels) / len(levels)
    thresh = cfg.OF_WALL_MULT * mean_q
    walls = [
        {"price": p, "qty": q, "distance_pct": abs(p - price) / price * 100 if price else 0.0}
        for p, q in levels if q >= thresh
    ]
    walls.sort(key=lambda w: w["qty"], reverse=True)
    return walls[:cfg.OF_WALL_TOP_N]


def compute_order_flow(
    bids: list[tuple[float, float]], asks: list[tuple[float, float]],
    agg_trades: list[dict] | None, atr: float, price: float,
) -> OrderFlow:
    band = max(cfg.OF_BAND_PRICE_PCT * price, cfg.OF_BAND_ATR * atr)
    lo, hi = price - band, price + band
    in_bids = [(p, q) for p, q in bids if lo <= p <= hi]
    in_asks = [(p, q) for p, q in asks if lo <= p <= hi]

    bid_vol = sum(q for _, q in in_bids)
    ask_vol = sum(q for _, q in in_asks)
    tot = bid_vol + ask_vol
    imbalance = (bid_vol - ask_vol) / tot if tot > 0 else 0.0

    # CVD (taker aggression) — non-fatal.
    cvd_ratio = 0.0
    if agg_trades:
        buy_vol = sum(t["qty"] for t in agg_trades if not t["is_buyer_maker"])
        sell_vol = sum(t["qty"] for t in agg_trades if t["is_buyer_maker"])
        total_trade = buy_vol + sell_vol
        if total_trade > 0:
            cvd_ratio = (buy_vol - sell_vol) / total_trade

    if imbalance > cfg.OF_PRESSURE_THRESHOLD:
        pressure = PressureLabel.BUY
    elif imbalance < -cfg.OF_PRESSURE_THRESHOLD:
        pressure = PressureLabel.SELL
    else:
        pressure = PressureLabel.BALANCED

    return OrderFlow(
        imbalance=imbalance,
        cvd_ratio=cvd_ratio,
        pressure=pressure,
        bid_notional=sum(p * q for p, q in in_bids),
        ask_notional=sum(p * q for p, q in in_asks),
        bid_walls=_walls(in_bids, price),
        ask_walls=_walls(in_asks, price),
    )


def fetch_order_flow(market_service, symbol: str, atr: float, price: float) -> OrderFlow:
    book = market_service.get_raw_order_book(symbol, limit=cfg.OF_DEPTH_LIMIT)
    try:
        trades = market_service.get_agg_trades(symbol, limit=cfg.OF_AGG_TRADES_LIMIT)
    except Exception:
        trades = None   # taker-aggression failure is non-fatal
    return compute_order_flow(book["bids"], book["asks"], trades, atr, price)
