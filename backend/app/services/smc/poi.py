"""Advanced SMC layer — POIs, inducements, demand/supply zones (§5.8-5.10).

POI (§5.8): pair every unmitigated OB with every open FVG of the same direction;
they form a POI on overlap (take the tighter intersection) or a near-miss with a
gap <= POI_OVERLAP_ATR (bridge into a union). hasLiquidity when a pool rests
within POI_LIQUIDITY_ATR of the zone. Nested same-direction POIs de-duplicate to
the tighter zone.

Inducements (§5.9): only when the trend is directional and POIs exist — every HL
(uptrend) / LH (downtrend) swing whose nearest same-direction POI is within
INDUCEMENT_ATR is the obvious retail entry front-running a deeper zone.

Demand/supply (§5.10): a tight base (<=3 candles, range <= DEMAND_BASE_RANGE_ATR)
followed by a >= DEMAND_IMPULSE_ATR impulse over the next DEMAND_IMPULSE_CANDLES
candles (>=60% closing in-direction). Mitigated by a single touch (unlike OBs).
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import (
    Direction,
    FVG,
    Inducement,
    LiquidityPool,
    OrderBlock,
    POI,
    SupplyDemandZone,
    Swing,
    SwingLabel,
    TrendState,
)


def _dist_to_zone(price: float, bottom: float, top: float) -> float:
    if price < bottom:
        return bottom - price
    if price > top:
        return price - top
    return 0.0


def find_pois(
    obs: list[OrderBlock], fvgs: list[FVG],
    pools: list[LiquidityPool], atr: float,
) -> list[POI]:
    open_obs = [o for o in obs if not o.mitigated]
    open_fvgs = [f for f in fvgs if not f.filled]
    gap_thresh = smc_config.POI_OVERLAP_ATR * atr
    liq_thresh = smc_config.POI_LIQUIDITY_ATR * atr

    raw: list[POI] = []
    for ob in open_obs:
        for fvg in open_fvgs:
            if ob.direction != fvg.direction:
                continue
            lo = max(ob.bottom, fvg.bottom)
            hi = min(ob.top, fvg.top)
            if lo <= hi:                      # overlap -> tighter intersection
                z_bottom, z_top = lo, hi
            else:                             # near-miss -> bridging union
                gap = (fvg.bottom - ob.top) if fvg.bottom > ob.top else (ob.bottom - fvg.top)
                if gap > gap_thresh:
                    continue
                z_bottom = min(ob.bottom, fvg.bottom)
                z_top = max(ob.top, fvg.top)

            poi = POI(
                top=z_top, bottom=z_bottom, direction=ob.direction,
                order_block_index=ob.index, fvg_index=fvg.index,
                has_liquidity=any(
                    z_bottom - liq_thresh <= p.price <= z_top + liq_thresh
                    for p in pools
                ),
            )
            raw.append(poi)

    # De-dup exact duplicates.
    unique: list[POI] = []
    seen: set[tuple] = set()
    for p in raw:
        key = (round(p.bottom, 8), round(p.top, 8), p.direction.value)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Drop any POI that strictly contains a tighter same-direction POI.
    result: list[POI] = []
    for a in unique:
        contains_tighter = any(
            b is not a and b.direction == a.direction
            and b.bottom > a.bottom and b.top < a.top
            for b in unique
        )
        if not contains_tighter:
            result.append(a)
    return result


def find_inducements(
    swings: list[Swing], pois: list[POI], trend: TrendState, atr: float,
) -> list[Inducement]:
    if trend == TrendState.NEUTRAL or not pois:
        return []
    if trend == TrendState.UP:
        want, direction = SwingLabel.HL, Direction.BULLISH
    else:
        want, direction = SwingLabel.LH, Direction.BEARISH

    same = [p for p in pois if p.direction == direction]
    if not same:
        return []
    thresh = smc_config.INDUCEMENT_ATR * atr

    inducements: list[Inducement] = []
    for s in swings:
        if s.label != want:
            continue
        nearest = min(_dist_to_zone(s.price, p.bottom, p.top) for p in same)
        if nearest <= thresh:
            inducements.append(Inducement(
                index=s.index, time=s.time, price=s.price,
                direction=direction, atr_distance=nearest / atr if atr else 0.0,
            ))
    return inducements


def find_supply_demand(df: pd.DataFrame, atr: float) -> list[SupplyDemandZone]:
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    times = [t.isoformat() for t in df["timestamps"]]
    n = len(df)

    base_max = smc_config.DEMAND_BASE_MAX_CANDLES
    base_range_thresh = smc_config.DEMAND_BASE_RANGE_ATR * atr
    impulse_thresh = smc_config.DEMAND_IMPULSE_ATR * atr
    imp_bars = smc_config.DEMAND_IMPULSE_CANDLES
    dir_pct = smc_config.DEMAND_DIRECTIONAL_PCT

    zones: list[SupplyDemandZone] = []
    i = 0
    while i < n:
        hit = False
        for length in range(1, base_max + 1):
            base_end = i + length - 1
            impulse_end = base_end + imp_bars
            if impulse_end >= n:
                break
            base_hi = float(highs[i:base_end + 1].max())
            base_lo = float(lows[i:base_end + 1].min())
            if base_hi - base_lo > base_range_thresh:
                continue

            base_open = float(opens[i])
            final_close = float(closes[impulse_end])
            imp = range(base_end + 1, base_end + 1 + imp_bars)
            up_count = sum(1 for k in imp if closes[k] > opens[k])
            down_count = sum(1 for k in imp if closes[k] < opens[k])

            direction = None
            if final_close - base_open >= impulse_thresh and up_count / imp_bars >= dir_pct:
                direction = Direction.BULLISH
            elif base_open - final_close >= impulse_thresh and down_count / imp_bars >= dir_pct:
                direction = Direction.BEARISH
            if direction is None:
                continue

            zone = SupplyDemandZone(
                index=i, time=times[i], top=base_hi, bottom=base_lo,
                direction=direction,
            )
            # Mitigation by a single touch (from after the impulse).
            for k in range(impulse_end + 1, n):
                if direction == Direction.BULLISH and lows[k] <= zone.top:
                    zone.mitigated = True
                    break
                if direction == Direction.BEARISH and highs[k] >= zone.bottom:
                    zone.mitigated = True
                    break
            zones.append(zone)
            i = impulse_end + 1
            hit = True
            break
        if not hit:
            i += 1
    return zones
