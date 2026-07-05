"""Market-bias component scoring + verdict (§6.1-6.2).

Six components, each clamped to -100..+100 (positive = bullish), then weighted
into a single total that produces the displayed verdict badge. This composite is
informational only — it never gates a trade (that is §6.3's per-side checklist).
"""

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import (
    ConfidenceLabel,
    DealingRange,
    Direction,
    FVG,
    LiquidityPool,
    OrderBlock,
    ScoreBreakdown,
    ScoreComponent,
    StructureEvent,
    StructureType,
    TrendState,
    Verdict,
    VerdictLabel,
    VolumeContext,
)

cfg = smc_config


def _clamp(x: float) -> float:
    return max(-100.0, min(100.0, x))


def _dist_to_zone(price: float, bottom: float, top: float) -> float:
    if price < bottom:
        return bottom - price
    if price > top:
        return price - top
    return 0.0


def score_structure(trend: TrendState, events: list[StructureEvent]) -> float:
    base = (cfg.STRUCTURE_TREND_BASE if trend == TrendState.UP
            else -cfg.STRUCTURE_TREND_BASE if trend == TrendState.DOWN else 0.0)
    for e in events[-3:]:
        if e.type == StructureType.CHOCH_UP:
            base += cfg.STRUCTURE_CHOCH_POINTS
        elif e.type == StructureType.CHOCH_DOWN:
            base -= cfg.STRUCTURE_CHOCH_POINTS
        elif e.type == StructureType.BOS_UP:
            base += cfg.STRUCTURE_BOS_POINTS
        elif e.type == StructureType.BOS_DOWN:
            base -= cfg.STRUCTURE_BOS_POINTS
    return _clamp(base)


def score_order_blocks(obs: list[OrderBlock], price: float, rng: float) -> float:
    if rng <= 0:
        return 0.0
    unmit = [o for o in obs if not o.mitigated][-cfg.OB_SCORE_LOOKBACK:]
    total = 0.0
    for ob in unmit:
        dist = _dist_to_zone(price, ob.bottom, ob.top) / rng
        if dist > cfg.OB_SCORE_MAX_DIST:
            continue
        weight = (cfg.OB_SCORE_MAX_DIST - dist) * cfg.OB_SCORE_WEIGHT
        total += weight if ob.direction == Direction.BULLISH else -weight
    return _clamp(total)


def score_fvg(fvgs: list[FVG], price: float, rng: float) -> float:
    if rng <= 0:
        return 0.0
    open_fvgs = [f for f in fvgs if not f.filled][-cfg.FVG_SCORE_LOOKBACK:]
    total = 0.0
    for f in open_fvgs:
        mid = (f.top + f.bottom) / 2
        dist = abs(price - mid) / rng
        if dist > cfg.FVG_SCORE_MAX_DIST:
            continue
        weight = (cfg.FVG_SCORE_MAX_DIST - dist) * cfg.FVG_SCORE_WEIGHT
        total += weight if f.direction == Direction.BULLISH else -weight
    return _clamp(total)


def score_liquidity(pools: list[LiquidityPool], price: float) -> float:
    if price <= 0:
        return 0.0
    band = cfg.LIQUIDITY_SCORE_BAND_PCT / 100.0
    pts = cfg.LIQUIDITY_SCORE_POINTS
    total = 0.0
    for p in pools:
        # equal-highs (BEARISH-labelled pool) above price = upside magnet -> +
        if p.direction == Direction.BEARISH and price < p.price <= price * (1 + band):
            total += pts
        # equal-lows below price = downside magnet -> -
        elif p.direction == Direction.BULLISH and price * (1 - band) <= p.price < price:
            total -= pts
    return _clamp(total)


def score_zone(dr: DealingRange | None) -> float:
    if dr is None:
        return 0.0
    pos = dr.position
    if pos < cfg.ZONE_POS_DEEP_DISCOUNT:
        return cfg.ZONE_SCORE_DEEP_DISCOUNT
    if pos < cfg.ZONE_POS_DISCOUNT:
        return cfg.ZONE_SCORE_DISCOUNT
    if pos < cfg.ZONE_POS_PREMIUM:
        return cfg.ZONE_SCORE_PREMIUM
    return cfg.ZONE_SCORE_DEEP_PREMIUM


def score_volume(vol: VolumeContext | None) -> float:
    if vol is None:
        return 0.0
    v = vol.trend_vol * cfg.VOLUME_SCORE_WEIGHT
    if vol.spike:
        v *= cfg.VOLUME_BOOST
    return _clamp(v)


def component_scores(
    trend: TrendState, events: list[StructureEvent],
    obs: list[OrderBlock], fvgs: list[FVG], pools: list[LiquidityPool],
    dr: DealingRange | None, vol: VolumeContext | None, price: float,
) -> dict[str, float]:
    rng = (dr.range_hi - dr.range_lo) if dr else 0.0
    return {
        "structure": score_structure(trend, events),
        "order_blocks": score_order_blocks(obs, price, rng),
        "fvg": score_fvg(fvgs, price, rng),
        "liquidity": score_liquidity(pools, price),
        "zone": score_zone(dr),
        "volume": score_volume(vol),
    }


_WEIGHTS = {
    "structure": cfg.WEIGHT_STRUCTURE,
    "order_blocks": cfg.WEIGHT_ORDER_BLOCKS,
    "fvg": cfg.WEIGHT_FVG,
    "liquidity": cfg.WEIGHT_LIQUIDITY,
    "zone": cfg.WEIGHT_ZONE,
    "volume": cfg.WEIGHT_VOLUME,
}


def build_verdict(scores: dict[str, float]) -> Verdict:
    components = []
    total = 0.0
    for name, weight in _WEIGHTS.items():
        raw = scores.get(name, 0.0)
        contribution = raw * weight
        total += contribution
        components.append(ScoreComponent(
            name=name, raw=raw, weight=weight, contribution=contribution,
        ))

    if total > cfg.VERDICT_BULLISH_ABOVE:
        label = VerdictLabel.BULLISH
    elif total < cfg.VERDICT_BEARISH_BELOW:
        label = VerdictLabel.BEARISH
    else:
        label = VerdictLabel.NEUTRAL

    confidence = min(100.0, abs(total) * cfg.CONFIDENCE_MULT)
    if confidence > cfg.CONFIDENCE_HIGH:
        conf_label = ConfidenceLabel.HIGH
    elif confidence > cfg.CONFIDENCE_MEDIUM:
        conf_label = ConfidenceLabel.MEDIUM
    else:
        conf_label = ConfidenceLabel.LOW

    return Verdict(
        label=label, total=total, confidence=confidence,
        confidence_label=conf_label,
        breakdown=ScoreBreakdown(components=components, total=total),
    )


def compute_verdict(
    trend: TrendState, events: list[StructureEvent],
    obs: list[OrderBlock], fvgs: list[FVG], pools: list[LiquidityPool],
    dr: DealingRange | None, vol: VolumeContext | None, price: float,
) -> Verdict:
    return build_verdict(component_scores(trend, events, obs, fvgs, pools, dr, vol, price))
