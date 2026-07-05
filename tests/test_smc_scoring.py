"""A8 — SMC market-bias scoring + verdict (§6.1-6.2).

Component functions with crafted inputs (exact expected raws) + the weighted
verdict formula + label/confidence boundaries. Plus live smoke.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_scoring.py
"""

import backend.app.core.config  # noqa: F401

from backend.app.schemas.smc import (
    ConfidenceLabel, DealingRange, Direction, FVG, LiquidityPool, OrderBlock,
    StructureEvent, StructureType, TrendState, VerdictLabel, VolumeContext,
)
from backend.app.services.market_service import MarketService
from backend.app.services.smc.atr import compute_atr
from backend.app.services.smc.dealing_range import compute_dealing_range
from backend.app.services.smc.fvg import find_fvgs
from backend.app.services.smc.liquidity import find_liquidity_pools
from backend.app.services.smc.order_blocks import find_order_blocks
from backend.app.services.smc.scoring import (
    build_verdict, compute_verdict, score_liquidity, score_order_blocks,
    score_structure, score_volume, score_zone,
)
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings
from backend.app.services.smc.volume import compute_volume


def _ev(t):
    return StructureEvent(index=0, time="t", price=1.0, type=t)


def test_components():
    # structure: +60 base + BOS_up(10)+CHoCH_up(15)+BOS_up(10) = 95
    s = score_structure(TrendState.UP, [
        _ev(StructureType.BOS_UP), _ev(StructureType.CHOCH_UP), _ev(StructureType.BOS_UP)])
    assert s == 95.0, s

    # zone by position
    assert score_zone(DealingRange(range_hi=1, range_lo=0, equilibrium=.5, position=0.2, zone="discount")) == 50
    assert score_zone(DealingRange(range_hi=1, range_lo=0, equilibrium=.5, position=0.4, zone="discount")) == 20
    assert score_zone(DealingRange(range_hi=1, range_lo=0, equilibrium=.5, position=0.6, zone="premium")) == -20
    assert score_zone(DealingRange(range_hi=1, range_lo=0, equilibrium=.5, position=0.8, zone="premium")) == -50

    # volume: 0.5*60 = 30; spike -> *1.3 = 39
    assert score_volume(VolumeContext(ratio=1.0, trend_vol=0.5, spike=False)) == 30
    assert abs(score_volume(VolumeContext(ratio=2.0, trend_vol=0.5, spike=True)) - 39) < 1e-9

    # liquidity: equal-highs above -> +25, equal-lows below -> -25
    assert score_liquidity([LiquidityPool(price=110, direction=Direction.BEARISH)], 100) == 25
    assert score_liquidity([LiquidityPool(price=90, direction=Direction.BULLISH)], 100) == -25
    assert score_liquidity([LiquidityPool(price=130, direction=Direction.BEARISH)], 100) == 0  # >15%

    # order blocks: price inside bullish OB -> (0.25-0)*80 = 20
    ob = OrderBlock(index=0, time="t", top=105, bottom=95, direction=Direction.BULLISH)
    assert score_order_blocks([ob], price=100, rng=1000) == 20
    obb = OrderBlock(index=0, time="t", top=105, bottom=95, direction=Direction.BEARISH)
    assert score_order_blocks([obb], price=100, rng=1000) == -20
    print("PASS components: structure=95, zone/volume/liquidity/OB all exact")


def test_verdict_formula():
    scores = {"structure": 100, "order_blocks": 50, "fvg": 20,
              "liquidity": 25, "zone": 50, "volume": 30}
    v = build_verdict(scores)
    # 100*.3 + 50*.2 + 20*.1 + 25*.1 + 50*.15 + 30*.15 = 56.5
    assert abs(v.total - 56.5) < 1e-9, v.total
    assert v.label == VerdictLabel.BULLISH
    assert abs(v.confidence - 84.75) < 1e-9 and v.confidence_label == ConfidenceLabel.HIGH
    print(f"PASS verdict formula: total=56.5 BULLISH conf=84.75 high")


def test_boundaries():
    # total exactly +20 -> NEUTRAL (must be strictly > 20)
    assert build_verdict({"structure": 200/3}).label == VerdictLabel.NEUTRAL  # 66.67*.3=20.0
    # just over
    assert build_verdict({"structure": 70}).label == VerdictLabel.BULLISH      # 21
    assert build_verdict({"structure": -70}).label == VerdictLabel.BEARISH
    # confidence label bands: |total| 30 -> conf 45 -> medium
    v = build_verdict({"structure": 100})   # total 30, conf 45
    assert v.confidence_label == ConfidenceLabel.MEDIUM, (v.confidence, v.confidence_label)
    print("PASS boundaries: +20 neutral, >20 bullish, conf bands")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 500)
    price = float(df["close"].iloc[-1])
    atr = compute_atr(df)
    swings = find_swings(df)
    sr = analyze_structure(swings)
    obs = find_order_blocks(df, sr.events)
    fvgs = find_fvgs(df)
    pools = find_liquidity_pools(df, swings)
    dr = compute_dealing_range(df)
    vol = compute_volume(df)
    v = compute_verdict(sr.trend, sr.events, obs, fvgs, pools, dr, vol, price)
    assert -100 <= v.total <= 100
    assert v.label in (VerdictLabel.BULLISH, VerdictLabel.BEARISH, VerdictLabel.NEUTRAL)
    assert len(v.breakdown.components) == 6
    print(f"PASS live BTCUSDT/1h: verdict={v.label.value} total={v.total:.1f} "
          f"conf={v.confidence:.0f}({v.confidence_label.value})")


if __name__ == "__main__":
    test_components()
    test_verdict_formula()
    test_boundaries()
    test_live()
    print("A8 OK")
