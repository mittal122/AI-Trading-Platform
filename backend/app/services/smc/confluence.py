"""Per-side confluence checklist + veto rules (§6.3).

Each side (long/short) is scored independently against an 8-factor checklist worth
up to 110 points, at a *proposed entry*. A side fires only when its total >= 70
AND no reject (veto) rule triggers. The market-bias verdict (§6.2) never gates a
trade — this does.
"""

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import (
    ConfluenceFactor,
    DealingRange,
    Direction,
    FVG,
    HTFTrend,
    LiquiditySweep,
    OrderBlock,
    OrderFlow,
    POI,
    Side,
    SideConfluence,
    StrengthLabel,
    StructureEvent,
    SupplyDemandZone,
    TrendState,
)

cfg = smc_config


def _dist_to_zone(price: float, bottom: float, top: float) -> float:
    if price < bottom:
        return bottom - price
    if price > top:
        return price - top
    return 0.0


def _matching_candle(prev, last, is_long: bool) -> bool:
    """Engulfing or pin bar in the side's direction. `prev`/`last` = (o,h,l,c)."""
    if last is None:
        return False
    o, h, low, c = last
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - low
    if body <= 0:
        return False
    if is_long:
        pin = lower >= 2 * body and upper < body
        eng = c > o and prev is not None and prev[3] < prev[0] and c >= prev[0] and o <= prev[3]
        return pin or eng
    pin = upper >= 2 * body and lower < body
    eng = c < o and prev is not None and prev[3] > prev[0] and c <= prev[0] and o >= prev[3]
    return pin or eng


def score_side(
    side: Side, entry: float, price: float, atr: float, *,
    obs: list[OrderBlock], fvgs: list[FVG], pois: list[POI],
    sweeps: list[LiquiditySweep], supply_demand: list[SupplyDemandZone],
    htf: HTFTrend | None, dealing_range: DealingRange | None,
    trend: TrendState, events: list[StructureEvent],
    prev_candle=None, last_candle=None, order_flow: OrderFlow | None = None,
) -> SideConfluence:
    is_long = side == Side.LONG
    want = Direction.BULLISH if is_long else Direction.BEARISH
    contain = cfg.CONTAIN_TOL_ATR * atr
    poi_tol = cfg.POI_PRESENT_ATR * atr

    factors: list[ConfluenceFactor] = []

    def add(name, points, hit, detail=""):
        factors.append(ConfluenceFactor(name=name, points=points, hit=hit, detail=detail))
        return points if hit else 0

    total = 0

    ob_hit = any(not o.mitigated and o.direction == want
                 and _dist_to_zone(entry, o.bottom, o.top) <= contain for o in obs)
    total += add("order_block_in_zone", cfg.PTS_OB_IN_ZONE, ob_hit)

    fvg_hit = any(not f.filled and f.direction == want
                  and _dist_to_zone(entry, f.bottom, f.top) <= contain for f in fvgs)
    total += add("fvg_in_zone", cfg.PTS_FVG_IN_ZONE, fvg_hit)

    htf_ok = bool(htf and htf.available and htf.trend ==
                  (TrendState.UP if is_long else TrendState.DOWN))
    total += add("htf_aligned", cfg.PTS_HTF_ALIGNED, htf_ok)

    zone_ok = bool(dealing_range and dealing_range.zone != "equilibrium"
                   and dealing_range.zone == ("discount" if is_long else "premium"))
    total += add("correct_dealing_range", cfg.PTS_DEALING_RANGE, zone_ok)

    sweep_ok = any(s.recent and s.direction == want for s in sweeps)
    total += add("recent_liquidity_sweep", cfg.PTS_LIQ_SWEEP, sweep_ok)

    poi_hit = any(p.direction == want and _dist_to_zone(entry, p.bottom, p.top) <= poi_tol
                  for p in pois)
    total += add("poi_present", cfg.PTS_POI_PRESENT, poi_hit)

    of_aligned = False
    if order_flow is not None:
        bias = (order_flow.imbalance + order_flow.cvd_ratio) / 2
        of_aligned = bias > cfg.OF_PRESSURE_THRESHOLD if is_long else bias < -cfg.OF_PRESSURE_THRESHOLD
    total += add("order_flow_aligned", cfg.PTS_ORDER_FLOW, of_aligned)

    candle_ok = _matching_candle(prev_candle, last_candle, is_long)
    total += add("candle_pattern", cfg.PTS_CANDLE_PATTERN, candle_ok)

    # ----- Reject (veto) rules -----
    rejects: list[str] = []

    if dealing_range and dealing_range.zone == "equilibrium":
        rejects.append("equilibrium: price in the 45-55% dead zone")

    if (htf and htf.available and htf.trend != TrendState.NEUTRAL
            and trend != TrendState.NEUTRAL and htf.trend != trend):
        rejects.append("HTF/LTF disagreement")

    if (is_long and trend == TrendState.DOWN) or (not is_long and trend == TrendState.UP):
        rejects.append("counter-trend: fading a confirmed structure trend")

    has_zone = (
        any(o.direction == want and not o.mitigated
            and _dist_to_zone(price, o.bottom, o.top) <= cfg.VETO_ZONE_VACUUM_ATR * atr for o in obs)
        or any(f.direction == want and not f.filled
               and _dist_to_zone(price, f.bottom, f.top) <= cfg.VETO_ZONE_VACUUM_ATR * atr for f in fvgs)
        or any(p.direction == want
               and _dist_to_zone(price, p.bottom, p.top) <= cfg.VETO_ZONE_VACUUM_ATR * atr for p in pois)
        or any(z.direction == want and not z.mitigated
               and _dist_to_zone(price, z.bottom, z.top) <= cfg.VETO_ZONE_VACUUM_ATR * atr for z in supply_demand)
    )
    if not has_zone:
        rejects.append("zone vacuum: no same-direction structure within 2xATR")

    atr_pct = (atr / price * 100) if price > 0 else 0.0
    if atr_pct < cfg.VETO_VOLATILITY_LOW_PCT:
        rejects.append(f"volatility too low ({atr_pct:.2f}% < 0.2%)")
    elif atr_pct > cfg.VETO_VOLATILITY_HIGH_PCT:
        rejects.append(f"volatility too high ({atr_pct:.2f}% > 4%)")

    if order_flow is not None:
        if is_long and order_flow.imbalance < cfg.VETO_OF_IMBALANCE and order_flow.cvd_ratio < cfg.VETO_OF_CVD:
            rejects.append("order flow strongly against (long)")
        elif not is_long and order_flow.imbalance > -cfg.VETO_OF_IMBALANCE and order_flow.cvd_ratio > -cfg.VETO_OF_CVD:
            rejects.append("order flow strongly against (short)")

    fired = total >= cfg.CONFLUENCE_FIRE_THRESHOLD and not rejects
    if fired:
        strength = StrengthLabel.STRONG
    elif total >= cfg.CONFLUENCE_FIRE_THRESHOLD:
        strength = StrengthLabel.REJECTED
    elif total >= 40:
        strength = StrengthLabel.MODERATE
    else:
        strength = StrengthLabel.WEAK

    return SideConfluence(
        side=side, total=total, fired=fired, strength=strength,
        factors=factors, reject_reasons=rejects,
    )
