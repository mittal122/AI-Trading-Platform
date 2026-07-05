"""A9 — SMC per-side confluence checklist + veto rules (§6.3).

Full-fire long (all 8 factors -> 110, STRONG), each veto in isolation
(equilibrium / counter-trend / volatility / zone-vacuum), and a moderate
not-fired case. Plus a live both-sides smoke.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_confluence.py
"""

import backend.app.core.config  # noqa: F401

from backend.app.schemas.smc import (
    DealingRange, Direction, FVG, HTFTrend, LiquiditySweep, OrderBlock,
    OrderFlow, POI, PressureLabel, Side, StrengthLabel, TrendState,
)
from backend.app.services.market_service import MarketService
from backend.app.services.smc.confluence import score_side
from backend.app.services.smc.scoring import compute_verdict  # noqa: F401 (sanity import)


def _dr(pos, zone):
    return DealingRange(range_hi=1100, range_lo=900, equilibrium=1000, position=pos, zone=zone)


def make_long(**over):
    kwargs = dict(
        side=Side.LONG, entry=1000.0, price=1000.0, atr=10.0,
        obs=[OrderBlock(index=0, time="t", top=1002, bottom=998, direction=Direction.BULLISH)],
        fvgs=[FVG(index=0, time="t", top=1001, bottom=999, direction=Direction.BULLISH)],
        pois=[POI(top=1003, bottom=997, direction=Direction.BULLISH)],
        sweeps=[LiquiditySweep(pool_price=996, direction=Direction.BULLISH,
                               sweep_index=5, reversal_index=9, recent=True)],
        supply_demand=[],
        htf=HTFTrend(available=True, trend=TrendState.UP, htf_bars=20),
        dealing_range=_dr(0.2, "discount"),
        trend=TrendState.UP, events=[],
        prev_candle=(1001, 1002, 997, 998),   # bearish
        last_candle=(997, 1004, 996, 1003),    # bullish engulfing
        order_flow=OrderFlow(imbalance=0.3, cvd_ratio=0.2, pressure=PressureLabel.BUY),
    )
    kwargs.update(over)
    return kwargs


def test_full_fire():
    r = score_side(**make_long())
    assert r.total == 110, [f.name for f in r.factors if f.hit]
    assert r.fired and r.strength == StrengthLabel.STRONG and not r.reject_reasons
    print(f"PASS full fire: 110/110, STRONG, all 8 factors hit")


def test_equilibrium_veto():
    r = score_side(**make_long(dealing_range=_dr(0.5, "equilibrium")))
    assert not r.fired and r.strength == StrengthLabel.REJECTED
    assert any("equilibrium" in x for x in r.reject_reasons), r.reject_reasons
    assert r.total == 95, r.total   # loses the +15 correct-zone factor
    print(f"PASS equilibrium veto: total 95 but REJECTED")


def test_counter_trend_veto():
    # HTF unavailable so only the counter-trend veto fires (isolate it)
    r = score_side(**make_long(trend=TrendState.DOWN,
                               htf=HTFTrend(available=False, trend=TrendState.NEUTRAL)))
    assert not r.fired
    assert any("counter-trend" in x for x in r.reject_reasons), r.reject_reasons
    print("PASS counter-trend veto: long vs DOWN trend -> rejected")


def test_volatility_veto():
    r = score_side(**make_long(atr=60.0))   # 60/1000 = 6% > 4%
    assert not r.fired
    assert any("volatility too high" in x for x in r.reject_reasons), r.reject_reasons
    print("PASS volatility veto: 6% ATR -> chaos rejected")


def test_zone_vacuum_veto():
    r = score_side(**make_long(obs=[], fvgs=[], pois=[], supply_demand=[],
                               sweeps=[], order_flow=None,
                               prev_candle=None, last_candle=None))
    assert not r.fired
    assert any("zone vacuum" in x for x in r.reject_reasons), r.reject_reasons
    print("PASS zone vacuum veto: no same-dir structure within 2xATR -> rejected")


def test_moderate_not_fired():
    # htf(+15) + dealing zone(+15) + POI(+10) = 40, no veto -> MODERATE, not fired
    r = score_side(**make_long(obs=[], fvgs=[], sweeps=[], order_flow=None,
                               prev_candle=None, last_candle=None))
    assert r.total == 40 and not r.fired and r.strength == StrengthLabel.MODERATE
    assert not r.reject_reasons, r.reject_reasons
    print("PASS moderate: 40/110, no veto, MODERATE, not fired")


def test_live():
    from backend.app.services.smc.atr import compute_atr
    from backend.app.services.smc.dealing_range import compute_dealing_range
    from backend.app.services.smc.fvg import find_fvgs
    from backend.app.services.smc.liquidity import find_liquidity_pools, find_sweeps
    from backend.app.services.smc.order_blocks import find_order_blocks
    from backend.app.services.smc.poi import find_pois, find_supply_demand
    from backend.app.services.smc.structure import analyze_structure
    from backend.app.services.smc.swing import find_swings

    df = MarketService().get_market_data("BTCUSDT", "1h", 500)
    price = float(df["close"].iloc[-1])
    atr = compute_atr(df)
    swings = find_swings(df)
    sr = analyze_structure(swings)
    obs = find_order_blocks(df, sr.events)
    fvgs = find_fvgs(df)
    pools = find_liquidity_pools(df, swings)
    sweeps = find_sweeps(df, pools)
    pois = find_pois(obs, fvgs, pools, atr)
    sd = find_supply_demand(df, atr)
    dr = compute_dealing_range(df)
    common = dict(price=price, atr=atr, obs=obs, fvgs=fvgs, pois=pois, sweeps=sweeps,
                  supply_demand=sd, htf=None, dealing_range=dr, trend=sr.trend, events=sr.events)
    lng = score_side(side=Side.LONG, entry=price, **common)
    sht = score_side(side=Side.SHORT, entry=price, **common)
    assert 0 <= lng.total <= 110 and 0 <= sht.total <= 110
    print(f"PASS live BTCUSDT/1h: long {lng.total}/110 fired={lng.fired} ({lng.strength.value}), "
          f"short {sht.total}/110 fired={sht.fired} ({sht.strength.value})")


if __name__ == "__main__":
    test_full_fire()
    test_equilibrium_veto()
    test_counter_trend_veto()
    test_volatility_veto()
    test_zone_vacuum_veto()
    test_moderate_not_fired()
    test_live()
    print("A9 OK")
