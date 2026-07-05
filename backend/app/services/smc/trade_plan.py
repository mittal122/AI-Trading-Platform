"""Trade plan generation (§7).

Entry by zone priority (POI > OB > demand/supply > recent swing > ATR fallback),
nearest-first within a tier, on the correct side of price and within
maxDist = min(2xATR, 3% of price). Structural stop placed beyond protective
structure + resting liquidity, minus a 0.8xATR buffer. TP1 = 2R, TP2 = 3.5R,
with a TP1 liquidity-snap to an opposing pool sitting between them. A minimum
risk floor of 1xATR applies.

build_plan() returns the geometric plan only; the engine scores confluence (§6.3)
at the chosen entry and overwrites strength / fired / confluence.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import (
    Direction,
    LiquidityPool,
    OrderBlock,
    POI,
    Side,
    StrengthLabel,
    SupplyDemandZone,
    Swing,
    TradePlan,
    ZoneKind,
)

cfg = smc_config


def _mid(bottom: float, top: float) -> float:
    return (bottom + top) / 2


def select_entry(
    side: Side, price: float, atr: float, *,
    pois: list[POI], obs: list[OrderBlock],
    supply_demand: list[SupplyDemandZone], recent_swings: list[Swing],
) -> tuple[ZoneKind, float | None, float | None, float]:
    """Return (source, zone_bottom, zone_top, entry)."""
    is_long = side == Side.LONG
    want = Direction.BULLISH if is_long else Direction.BEARISH
    max_dist = min(cfg.PLAN_MAX_DIST_ATR * atr, cfg.PLAN_MAX_DIST_PRICE_PCT * price)

    def ok(entry: float) -> bool:
        if entry <= 0:
            return False
        return (entry <= price and price - entry <= max_dist) if is_long \
            else (entry >= price and entry - price <= max_dist)

    def best(candidates):  # (entry, bottom, top) -> nearest qualifying
        q = [(abs(price - e), e, b, t) for (e, b, t) in candidates if ok(e)]
        return min(q, key=lambda x: x[0]) if q else None

    # Tier 1: POIs
    c = best([(_mid(p.bottom, p.top), p.bottom, p.top) for p in pois if p.direction == want])
    if c:
        return ZoneKind.POI, c[2], c[3], c[1]

    # Tier 2: order blocks (unmitigated)
    c = best([(_mid(o.bottom, o.top), o.bottom, o.top)
              for o in obs if o.direction == want and not o.mitigated])
    if c:
        return ZoneKind.ORDER_BLOCK, c[2], c[3], c[1]

    # Tier 3: demand/supply zones (unmitigated)
    c = best([(_mid(z.bottom, z.top), z.bottom, z.top)
              for z in supply_demand if z.direction == want and not z.mitigated])
    if c:
        kind = ZoneKind.DEMAND if is_long else ZoneKind.SUPPLY
        return kind, c[2], c[3], c[1]

    # Tier 4: recent swing (thin band around the swing level)
    band = 0.1 * atr
    sw = [s for s in recent_swings if (not s.is_high) == is_long]  # lows for long
    c = best([(s.price, s.price - band, s.price + band) for s in sw])
    if c:
        return ZoneKind.SWING, c[2], c[3], c[1]

    # Tier 5: ATR fallback
    entry = price - 0.5 * atr if is_long else price + 0.5 * atr
    return ZoneKind.ATR_FALLBACK, None, None, entry


def structural_stop(
    side: Side, zone_bottom: float | None, zone_top: float | None, atr: float,
    recent_swings: list[Swing], pools: list[LiquidityPool], source: ZoneKind,
    price: float,
) -> float:
    is_long = side == Side.LONG
    if source == ZoneKind.ATR_FALLBACK or zone_bottom is None or zone_top is None:
        return price - cfg.PLAN_MAX_DIST_ATR * atr if is_long \
            else price + cfg.PLAN_MAX_DIST_ATR * atr

    below = cfg.PLAN_STOP_SCAN_BELOW_ATR * atr
    above = cfg.PLAN_STOP_SCAN_ABOVE_ATR * atr
    buffer = cfg.PLAN_STOP_BUFFER_ATR * atr

    if is_long:
        win_lo, win_hi = zone_bottom - below, zone_bottom + above
        levels = [s.price for s in recent_swings
                  if not s.is_high and win_lo <= s.price <= win_hi]
        levels += [p.price for p in pools
                   if p.direction == Direction.BULLISH and win_lo <= p.price <= win_hi]
        base = min(levels) if levels else zone_bottom
        return base - buffer
    else:
        win_hi, win_lo = zone_top + below, zone_top - above
        levels = [s.price for s in recent_swings
                  if s.is_high and win_lo <= s.price <= win_hi]
        levels += [p.price for p in pools
                   if p.direction == Direction.BEARISH and win_lo <= p.price <= win_hi]
        base = max(levels) if levels else zone_top
        return base + buffer


def compute_targets(
    side: Side, entry: float, sl: float, atr: float, pools: list[LiquidityPool],
) -> tuple[float, float, float, float]:
    """Return (sl_adjusted, tp1, tp2, risk_reward)."""
    is_long = side == Side.LONG
    risk = abs(entry - sl)
    floor = cfg.PLAN_MIN_RISK_ATR * atr
    if risk < floor:
        sl = entry - floor if is_long else entry + floor
        risk = floor

    if is_long:
        tp1 = entry + cfg.PLAN_TP1_R * risk
        tp2 = entry + cfg.PLAN_TP2_R * risk
        opposing = sorted(p.price for p in pools
                          if p.direction == Direction.BEARISH and tp1 < p.price < tp2)
        if opposing:
            tp1 = opposing[0]   # nearest opposing pool above -> snap TP1 down to it
    else:
        tp1 = entry - cfg.PLAN_TP1_R * risk
        tp2 = entry - cfg.PLAN_TP2_R * risk
        opposing = sorted((p.price for p in pools
                           if p.direction == Direction.BULLISH and tp2 < p.price < tp1),
                          reverse=True)
        if opposing:
            tp1 = opposing[0]

    rr = abs(tp1 - entry) / abs(entry - sl) if entry != sl else 0.0
    return sl, tp1, tp2, rr


def build_plan(
    side: Side, price: float, atr: float, *,
    pois: list[POI], obs: list[OrderBlock],
    supply_demand: list[SupplyDemandZone], recent_swings: list[Swing],
    pools: list[LiquidityPool],
) -> TradePlan:
    source, zb, zt, entry = select_entry(
        side, price, atr, pois=pois, obs=obs,
        supply_demand=supply_demand, recent_swings=recent_swings,
    )
    sl = structural_stop(side, zb, zt, atr, recent_swings, pools, source, price)
    sl, tp1, tp2, rr = compute_targets(side, entry, sl, atr, pools)

    sl_atr = abs(entry - sl) / atr if atr else 0.0
    note = f"SL {sl_atr:.1f}xATR - TP1 {rr:.1f}x stop distance"

    return TradePlan(
        side=side, entry=entry, stop_loss=sl,
        take_profit_1=tp1, take_profit_2=tp2, risk_reward=rr, atr=atr,
        source=source, zone_top=zt, zone_bottom=zb,
        strength=StrengthLabel.WEAK, strength_score=0, fired=False, note=note,
    )
