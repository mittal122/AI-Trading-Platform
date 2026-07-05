"""A10 — SMC trade plan generation (§7).

POI-priority entry + structural stop + liquidity-snapped TP1; priority ladder
(POI beats a closer OB); minimum risk floor; ATR fallback; short mirror.
Plus live both-sides smoke.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_trade_plan.py
"""

import backend.app.core.config  # noqa: F401

from backend.app.schemas.smc import (
    Direction, LiquidityPool, OrderBlock, POI, Side, Swing, SupplyDemandZone, ZoneKind,
)
from backend.app.services.market_service import MarketService
from backend.app.services.smc.atr import compute_atr
from backend.app.services.smc.liquidity import find_liquidity_pools, recent_swings
from backend.app.services.smc.order_blocks import find_order_blocks
from backend.app.services.smc.poi import find_pois, find_supply_demand
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings
from backend.app.services.smc.trade_plan import build_plan
from backend.app.services.smc.fvg import find_fvgs


def _pool(price, d):
    return LiquidityPool(price=price, direction=d)


def test_long_poi_plan():
    # POI [990,994] -> entry 992; swing low 985 + eq-lows 980 in window -> base 980
    # sl 980-8=972; risk 20; tp1 1032 snaps to eq-highs 1040; tp2 1062; rr 2.4
    plan = build_plan(
        Side.LONG, price=1000, atr=10,
        pois=[POI(top=994, bottom=990, direction=Direction.BULLISH)],
        obs=[], supply_demand=[],
        recent_swings=[Swing(index=5, time="t", price=985, is_high=False)],
        pools=[_pool(980, Direction.BULLISH), _pool(1040, Direction.BEARISH)],
    )
    assert plan.source == ZoneKind.POI and plan.entry == 992, (plan.source, plan.entry)
    assert plan.stop_loss == 972, plan.stop_loss
    assert plan.take_profit_1 == 1040 and plan.take_profit_2 == 1062, (plan.take_profit_1, plan.take_profit_2)
    assert abs(plan.risk_reward - 2.4) < 1e-9, plan.risk_reward
    print(f"PASS long POI: entry 992 SL 972 TP1 1040(snap) TP2 1062 RR 2.4")


def test_priority_poi_over_ob():
    # OB is closer (mid 998) but POI (mid 992) must still win by tier priority
    plan = build_plan(
        Side.LONG, price=1000, atr=10,
        pois=[POI(top=994, bottom=990, direction=Direction.BULLISH)],
        obs=[OrderBlock(index=0, time="t", top=999, bottom=997, direction=Direction.BULLISH)],
        supply_demand=[], recent_swings=[], pools=[],
    )
    assert plan.source == ZoneKind.POI and plan.entry == 992
    print("PASS priority: POI (entry 992) beats a closer OB (mid 998)")


def test_min_risk_floor():
    # tight POI at price -> structural stop within 1xATR -> floor pushes SL to entry-1xATR
    plan = build_plan(
        Side.LONG, price=1000, atr=10,
        pois=[POI(top=1001, bottom=999, direction=Direction.BULLISH)],
        obs=[], supply_demand=[], recent_swings=[], pools=[],
    )
    # entry 1000, zone_bottom 999, base 999, sl 999-8=991 -> risk 9 < 10 -> floor sl 990
    assert plan.entry == 1000 and plan.stop_loss == 990, (plan.entry, plan.stop_loss)
    assert plan.take_profit_1 == 1020 and abs(plan.risk_reward - 2.0) < 1e-9
    print("PASS min risk floor: risk 9 -> pushed to 1xATR (SL 990), RR 2.0")


def test_atr_fallback():
    plan = build_plan(
        Side.LONG, price=1000, atr=10,
        pois=[], obs=[], supply_demand=[], recent_swings=[], pools=[],
    )
    # entry 995, sl 980, risk 15, tp1 1025, rr 2.0
    assert plan.source == ZoneKind.ATR_FALLBACK
    assert plan.entry == 995 and plan.stop_loss == 980
    assert plan.take_profit_1 == 1025 and abs(plan.risk_reward - 2.0) < 1e-9
    print("PASS ATR fallback: entry 995 SL 980 TP1 1025 RR 2.0")


def test_short_mirror():
    # supply POI [1006,1010] above price -> entry 1008; sl above; TPs below
    plan = build_plan(
        Side.SHORT, price=1000, atr=10,
        pois=[POI(top=1010, bottom=1006, direction=Direction.BEARISH)],
        obs=[], supply_demand=[],
        recent_swings=[Swing(index=5, time="t", price=1015, is_high=True)],
        pools=[_pool(1020, Direction.BEARISH)],
    )
    assert plan.source == ZoneKind.POI and plan.entry == 1008
    # win [1010-3, 1010+25]=[1007,1035]; swing high 1015 + eq-high 1020 -> base 1020; sl 1020+8=1028
    assert plan.stop_loss == 1028, plan.stop_loss
    assert plan.take_profit_1 < plan.entry and plan.take_profit_2 < plan.take_profit_1
    print(f"PASS short mirror: entry 1008 SL 1028 TP1 {plan.take_profit_1} TP2 {plan.take_profit_2}")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 500)
    price = float(df["close"].iloc[-1])
    atr = compute_atr(df)
    swings = find_swings(df)
    sr = analyze_structure(swings)
    obs = find_order_blocks(df, sr.events)
    fvgs = find_fvgs(df)
    pools = find_liquidity_pools(df, swings)
    pois = find_pois(obs, fvgs, pools, atr)
    sd = find_supply_demand(df, atr)
    rs = recent_swings(swings)
    for side in (Side.LONG, Side.SHORT):
        plan = build_plan(side, price, atr, pois=pois, obs=obs,
                          supply_demand=sd, recent_swings=rs, pools=pools)
        if side == Side.LONG:
            assert plan.stop_loss < plan.entry < plan.take_profit_1, (plan.stop_loss, plan.entry, plan.take_profit_1)
        else:
            assert plan.take_profit_1 < plan.entry < plan.stop_loss
        assert plan.risk_reward > 0
        print(f"  {side.value}: {plan.source.value} entry={plan.entry:.1f} SL={plan.stop_loss:.1f} "
              f"TP1={plan.take_profit_1:.1f} RR={plan.risk_reward:.2f}")
    print("PASS live BTCUSDT/1h: both sides geometrically valid")


if __name__ == "__main__":
    test_long_poi_plan()
    test_priority_poi_over_ob()
    test_min_risk_floor()
    test_atr_fallback()
    test_short_mirror()
    test_live()
    print("A10 OK")
