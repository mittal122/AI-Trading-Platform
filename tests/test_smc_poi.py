"""A7 — SMC advanced layer: POIs, inducements, demand/supply (§5.8-5.10).

Direct-object synthetic tests (POI geometry, dedup, hasLiquidity, inducements)
+ a candle-based demand-zone test with touch mitigation + live smoke.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_poi.py
"""

import backend.app.core.config  # noqa: F401

from datetime import datetime, timedelta

import pandas as pd

from backend.app.schemas.smc import (
    Direction, FVG, LiquidityPool, OrderBlock, POI, Swing, SwingLabel, TrendState,
)
from backend.app.services.market_service import MarketService
from backend.app.services.smc.atr import compute_atr
from backend.app.services.smc.fvg import find_fvgs
from backend.app.services.smc.liquidity import find_liquidity_pools
from backend.app.services.smc.order_blocks import find_order_blocks
from backend.app.services.smc.poi import find_inducements, find_pois, find_supply_demand
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings


def _ob(i, bottom, top, d=Direction.BULLISH):
    return OrderBlock(index=i, time="t", top=top, bottom=bottom, direction=d)


def _fvg(i, bottom, top, d=Direction.BULLISH):
    return FVG(index=i, time="t", top=top, bottom=bottom, direction=d)


def test_poi_geometry():
    atr = 5.0
    # overlap -> tighter intersection
    p = find_pois([_ob(1, 100, 105)], [_fvg(1, 103, 108)], [], atr)
    assert len(p) == 1 and (p[0].bottom, p[0].top) == (103, 105), p
    # near-miss (gap 0.3 <= 0.6*5) -> bridging union
    p = find_pois([_ob(1, 100, 102)], [_fvg(1, 102.3, 104)], [], atr)
    assert len(p) == 1 and (p[0].bottom, p[0].top) == (100, 104), p
    # gap 4 > 3 -> no POI
    assert find_pois([_ob(1, 100, 102)], [_fvg(1, 106, 108)], [], atr) == []
    # direction mismatch -> no POI
    assert find_pois([_ob(1, 100, 105)], [_fvg(1, 103, 108, Direction.BEARISH)], [], atr) == []
    print("PASS poi geometry: intersection / union / gap-reject / dir-mismatch")


def test_poi_liquidity_and_dedup():
    atr = 5.0
    # hasLiquidity: pool at 106 within 0.5*5 of zone top 105
    p = find_pois([_ob(1, 100, 105)], [_fvg(1, 103, 108)], [LiquidityPool(price=106, direction=Direction.BEARISH)], atr)
    assert p[0].has_liquidity, "pool within 0.5xATR should set hasLiquidity"
    p2 = find_pois([_ob(1, 100, 105)], [_fvg(1, 103, 108)], [LiquidityPool(price=120, direction=Direction.BEARISH)], atr)
    assert not p2[0].has_liquidity

    # nested dedup: [100,110] strictly contains [103,105] -> keep tighter only
    obs = [_ob(1, 100, 110), _ob(2, 103, 105)]
    fvgs = [_fvg(1, 100, 110), _fvg(2, 103, 105)]
    res = find_pois(obs, fvgs, [], atr)
    assert len(res) == 1 and (res[0].bottom, res[0].top) == (103, 105), \
        f"nested dedup failed: {[(r.bottom, r.top) for r in res]}"
    print("PASS poi liquidity + nested dedup (tighter zone kept)")


def test_inducements():
    atr = 5.0
    swings = [Swing(index=5, time="t", price=100, is_high=False, label=SwingLabel.HL)]
    near = [POI(top=98, bottom=96, direction=Direction.BULLISH)]   # dist 2 <= 7.5
    inds = find_inducements(swings, near, TrendState.UP, atr)
    assert len(inds) == 1 and abs(inds[0].atr_distance - 0.4) < 1e-9, inds
    # deeper POI out of range
    far = [POI(top=52, bottom=50, direction=Direction.BULLISH)]
    assert find_inducements(swings, far, TrendState.UP, atr) == []
    # neutral trend -> none
    assert find_inducements(swings, near, TrendState.NEUTRAL, atr) == []
    print("PASS inducements: HL near bullish POI in uptrend; range + trend gating")


def _df(rows):
    t0 = datetime(2026, 1, 1)
    for i, r in enumerate(rows):
        r["timestamps"] = t0 + timedelta(hours=i)
        r.setdefault("volume", 100.0)
        r.setdefault("amount", 100.0 * r["close"])
    return pd.DataFrame(rows)


def test_demand_zone():
    atr = 10.0  # base<=6, impulse>=25
    rows = [
        {"open": 100, "high": 101, "low": 99, "close": 100},   # 0 base
        {"open": 100, "high": 102, "low": 99, "close": 101},   # 1 base (range 3)
        {"open": 101, "high": 109, "low": 101, "close": 108},   # 2 impulse
        {"open": 108, "high": 115, "low": 108, "close": 114},   # 3
        {"open": 114, "high": 121, "low": 114, "close": 120},   # 4
        {"open": 120, "high": 124, "low": 120, "close": 123},   # 5
        {"open": 123, "high": 129, "low": 123, "close": 128},   # 6 (net 28 >= 25)
        {"open": 128, "high": 130, "low": 125, "close": 126},   # 7
        {"open": 126, "high": 128, "low": 124, "close": 125},   # 8
        {"open": 125, "high": 127, "low": 124, "close": 126},   # 9
        {"open": 126, "high": 127, "low": 101, "close": 120},   # 10 touch <=102 -> mitigate
        {"open": 120, "high": 121, "low": 119, "close": 120},   # 11..14 flat filler
        {"open": 120, "high": 121, "low": 119, "close": 120},
        {"open": 120, "high": 121, "low": 119, "close": 120},
        {"open": 120, "high": 121, "low": 119, "close": 120},
    ]
    zones = find_supply_demand(_df(rows), atr)
    demand = [z for z in zones if z.direction == Direction.BULLISH]
    assert len(demand) == 1, f"expected 1 demand zone, got {len(zones)}: {[(z.bottom,z.top,z.direction.value) for z in zones]}"
    z = demand[0]
    assert (z.bottom, z.top) == (99, 102) and z.index == 0, (z.bottom, z.top, z.index)
    assert z.mitigated, "demand zone should be mitigated by the touch at bar 10"
    print(f"PASS demand zone: [{z.bottom},{z.top}] @0, mitigated by touch")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 500)
    atr = compute_atr(df)
    swings = find_swings(df)
    sr = analyze_structure(swings)
    obs = find_order_blocks(df, sr.events)
    fvgs = find_fvgs(df)
    pools = find_liquidity_pools(df, swings)
    pois = find_pois(obs, fvgs, pools, atr)
    inds = find_inducements(sr.swings, pois, sr.trend, atr)
    zones = find_supply_demand(df, atr)
    for p in pois:
        assert p.top >= p.bottom
    print(f"PASS live BTCUSDT/1h: {len(pois)} POIs, {len(inds)} inducements, "
          f"{len(zones)} demand/supply zones (trend={sr.trend.value})")


if __name__ == "__main__":
    test_poi_geometry()
    test_poi_liquidity_and_dedup()
    test_inducements()
    test_demand_zone()
    test_live()
    print("A7 OK")
