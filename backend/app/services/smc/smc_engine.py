"""SMC analysis engine — pipeline orchestration (§5.1).

analyze() runs the full deterministic pipeline over a fixed candle snapshot and
returns one AnalysisResult containing everything the UI renders: candles, all
detections, both scoring systems, both trade plans, human-readable reasons, and a
freeze stamp (frozenAt + cutoffPrice). The live path passes an OrderFlow snapshot;
the backtest/scanner path omits it, keeping historical decisions free of
look-ahead data.
"""

from datetime import datetime, timezone

import pandas as pd

from backend.app.schemas.pattern import (
    ChartAnnotations, LabelAnnotation, LevelAnnotation, ZoneAnnotation,
)
from backend.app.schemas.smc import (
    AnalysisResult, Direction, OrderFlow, Side, SmcCandle, StructureType, TradePlan,
)
from backend.app.services.smc.atr import compute_atr
from backend.app.services.smc.confluence import score_side
from backend.app.services.smc.dealing_range import compute_dealing_range
from backend.app.services.smc.fvg import find_fvgs
from backend.app.services.smc.htf import compute_htf
from backend.app.services.smc.liquidity import (
    find_liquidity_pools, find_sweeps, recent_swings,
)
from backend.app.services.smc.order_blocks import find_order_blocks
from backend.app.services.smc.poi import (
    find_inducements, find_pois, find_supply_demand,
)
from backend.app.services.smc.scoring import compute_verdict
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings
from backend.app.services.smc.trade_plan import build_plan
from backend.app.services.smc.volume import compute_volume


def _candle_tuple(df: pd.DataFrame, i: int):
    r = df.iloc[i]
    return (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))


def analyze(
    symbol: str, interval: str, df: pd.DataFrame,
    order_flow: OrderFlow | None = None,
) -> AnalysisResult:
    price = float(df["close"].iloc[-1])
    atr = compute_atr(df)

    # ----- Detections -----
    swings = find_swings(df)
    sr = analyze_structure(swings)          # labels swings + events + trend
    obs = find_order_blocks(df, sr.events)
    fvgs = find_fvgs(df)
    pools = find_liquidity_pools(df, sr.swings)
    sweeps = find_sweeps(df, pools)
    dr = compute_dealing_range(df)
    vol = compute_volume(df)
    htf = compute_htf(df, interval)
    pois = find_pois(obs, fvgs, pools, atr)
    inducements = find_inducements(sr.swings, pois, sr.trend, atr)
    supply_demand = find_supply_demand(df, atr)

    # ----- Scoring + plans -----
    verdict = compute_verdict(sr.trend, sr.events, obs, fvgs, pools, dr, vol, price)
    rs = recent_swings(sr.swings)
    prev_candle = _candle_tuple(df, -2) if len(df) >= 2 else None
    last_candle = _candle_tuple(df, -1)

    def plan_for(side: Side) -> TradePlan:
        plan = build_plan(side, price, atr, pois=pois, obs=obs,
                          supply_demand=supply_demand, recent_swings=rs, pools=pools)
        conf = score_side(
            side, plan.entry, price, atr,
            obs=obs, fvgs=fvgs, pois=pois, sweeps=sweeps, supply_demand=supply_demand,
            htf=htf, dealing_range=dr, trend=sr.trend, events=sr.events,
            prev_candle=prev_candle, last_candle=last_candle, order_flow=order_flow,
        )
        plan.confluence = conf
        plan.strength = conf.strength
        plan.strength_score = conf.total
        plan.fired = conf.fired
        return plan

    long_plan = plan_for(Side.LONG)
    short_plan = plan_for(Side.SHORT)
    primary = _primary(long_plan, short_plan)

    reasons = _build_reasons(verdict, sr.trend, htf, long_plan, short_plan, primary)
    annotations = _build_annotations(df, obs, fvgs, pois, supply_demand, pools,
                                     sr.events, long_plan, short_plan, primary)

    candles = [
        SmcCandle(
            time=t.isoformat(), open=float(o), high=float(h),
            low=float(low), close=float(c), volume=float(v),
        )
        for t, o, h, low, c, v in zip(
            df["timestamps"], df["open"], df["high"], df["low"], df["close"], df["volume"])
    ]

    return AnalysisResult(
        symbol=symbol.upper(), interval=interval,
        frozen_at=datetime.now(timezone.utc).isoformat(), cutoff_price=price, atr=atr,
        candles=candles,
        swings=sr.swings, structure=sr.events, trend=sr.trend,
        order_blocks=obs, fvgs=fvgs, liquidity_pools=pools, sweeps=sweeps,
        dealing_range=dr, volume=vol, pois=pois, inducements=inducements,
        supply_demand=supply_demand, htf=htf,
        verdict=verdict, long_plan=long_plan, short_plan=short_plan, primary=primary,
        order_flow=order_flow, reasons=reasons, annotations=annotations,
    )


def _primary(long_plan: TradePlan, short_plan: TradePlan) -> str:
    if long_plan.fired and short_plan.fired:
        return "long" if long_plan.strength_score >= short_plan.strength_score else "short"
    if long_plan.fired:
        return "long"
    if short_plan.fired:
        return "short"
    return "neutral"


def _build_reasons(verdict, trend, htf, long_plan, short_plan, primary) -> list[str]:
    reasons = [
        f"Market bias: {verdict.label.value} ({verdict.confidence:.0f}% confidence)",
        f"Structure trend: {trend.value}",
    ]
    if htf and htf.available:
        reasons.append(f"Higher-timeframe trend: {htf.trend.value}")

    if primary in ("long", "short"):
        plan = long_plan if primary == "long" else short_plan
        reasons.append(f"{primary.upper()} signal FIRED — {plan.strength_score}/110 "
                       f"({plan.strength.value})")
        if plan.confluence:
            reasons += [f"+{f.points} {f.name.replace('_', ' ')}"
                        for f in plan.confluence.factors if f.hit]
    else:
        best = long_plan if long_plan.strength_score >= short_plan.strength_score else short_plan
        reasons.append(f"No signal fired — best {best.side.value} {best.strength_score}/110")
        if best.confluence:
            reasons += [f"Veto: {r}" for r in best.confluence.reject_reasons]
    return reasons


def _build_annotations(df, obs, fvgs, pois, supply_demand, pools, events,
                       long_plan, short_plan, primary) -> ChartAnnotations:
    end_time = df["timestamps"].iloc[-1].isoformat()
    price = float(df["close"].iloc[-1])
    n = len(df)
    zones: list[ZoneAnnotation] = []
    levels: list[LevelAnnotation] = []
    labels: list[LabelAnnotation] = []

    def _time_at(idx) -> str:
        if idx is None or idx < 0 or idx >= n:
            return end_time
        return df["timestamps"].iloc[idx].isoformat()

    def _nearest(items, mid, limit):
        # Only the few zones closest to current price — drawing every unmitigated
        # OB/FVG extending to "now" stacks into a wall of full-width bands.
        return sorted(items, key=lambda it: abs(mid(it) - price))[:limit]

    for ob in _nearest([o for o in obs if not o.mitigated],
                       lambda o: (o.top + o.bottom) / 2, 5):
        zones.append(ZoneAnnotation(label="Order Block", start_time=ob.time,
                                    end_time=end_time, top=ob.top, bottom=ob.bottom,
                                    bias=ob.direction.value))
    for f in _nearest([x for x in fvgs if not x.filled],
                      lambda x: (x.top + x.bottom) / 2, 5):
        zones.append(ZoneAnnotation(label="FVG", start_time=f.time, end_time=end_time,
                                    top=f.top, bottom=f.bottom, bias=f.direction.value))
    for p in pois:
        # Anchor the POI box to the candle it formed from (its order block, else
        # its FVG) — not the last candle, which mis-placed it at the right edge.
        start = _time_at(p.order_block_index if p.order_block_index is not None else p.fvg_index)
        zones.append(ZoneAnnotation(label="POI", start_time=start, end_time=end_time,
                                    top=p.top, bottom=p.bottom, bias=p.direction.value))
    for z in supply_demand:
        if not z.mitigated:
            label = "Demand" if z.direction == Direction.BULLISH else "Supply"
            zones.append(ZoneAnnotation(label=label, start_time=z.time, end_time=end_time,
                                        top=z.top, bottom=z.bottom, bias=z.direction.value))

    for pool in pools:
        tag = "EQH" if pool.direction == Direction.BEARISH else "EQL"
        levels.append(LevelAnnotation(label=tag, price=pool.price))

    for e in events[-6:]:
        text = e.type.value
        labels.append(LabelAnnotation(text=text, time=e.time, price=e.price))

    # Primary plan levels (entry / SL / TP1 / TP2).
    plan = long_plan if primary == "long" else short_plan if primary == "short" else None
    if plan:
        levels += [
            LevelAnnotation(label="Entry", price=plan.entry),
            LevelAnnotation(label="Stop", price=plan.stop_loss),
            LevelAnnotation(label="TP1", price=plan.take_profit_1),
            LevelAnnotation(label="TP2", price=plan.take_profit_2),
        ]

    return ChartAnnotations(zones=zones, levels=levels, labels=labels)
