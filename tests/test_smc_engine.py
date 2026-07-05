"""A12 — SMC engine orchestration (§5.1).

Full pipeline on live data: structural integrity, fired/primary consistency
invariants, freeze stamp, annotations, timing; plus order-flow attachment.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_engine.py
"""

import backend.app.core.config  # noqa: F401

import time
from datetime import datetime

from backend.app.schemas.smc import PressureLabel, OrderFlow, VerdictLabel
from backend.app.services.market_service import MarketService
from backend.app.services.smc.smc_engine import analyze


def _invariants(res, df_len):
    # candles
    assert len(res.candles) == df_len, (len(res.candles), df_len)
    # freeze
    datetime.fromisoformat(res.frozen_at)  # parses
    assert res.cutoff_price == res.candles[-1].close
    assert res.atr > 0
    # verdict
    assert res.verdict is not None and len(res.verdict.breakdown.components) == 6
    assert res.verdict.label in (VerdictLabel.BULLISH, VerdictLabel.BEARISH, VerdictLabel.NEUTRAL)
    # both plans present
    assert res.long_plan is not None and res.short_plan is not None
    # fired/primary consistency
    for plan in (res.long_plan, res.short_plan):
        if plan.fired:
            assert plan.strength_score >= 70 and plan.confluence and not plan.confluence.reject_reasons
    if res.primary == "neutral":
        assert not res.long_plan.fired and not res.short_plan.fired
    elif res.primary == "long":
        assert res.long_plan.fired
    elif res.primary == "short":
        assert res.short_plan.fired
    # geometry
    assert res.long_plan.stop_loss < res.long_plan.entry < res.long_plan.take_profit_1
    assert res.short_plan.take_profit_1 < res.short_plan.entry < res.short_plan.stop_loss
    # reasons + annotations
    assert len(res.reasons) >= 2
    assert res.annotations is not None


def test_live_multi():
    ms = MarketService()
    for sym, iv in [("BTCUSDT", "1h"), ("ETHUSDT", "15m"), ("SOLUSDT", "4h")]:
        df = ms.get_market_data(sym, iv, 500)
        t0 = time.monotonic()
        res = analyze(sym, iv, df)
        elapsed = time.monotonic() - t0
        _invariants(res, len(df))
        assert elapsed < 5.0, f"{sym}/{iv} slow: {elapsed:.1f}s"
        print(f"PASS {sym}/{iv}: verdict={res.verdict.label.value} "
              f"primary={res.primary} long={res.long_plan.strength_score}/110 "
              f"short={res.short_plan.strength_score}/110 "
              f"({len(res.order_blocks)}OB {len(res.fvgs)}FVG {len(res.pois)}POI) "
              f"{elapsed*1000:.0f}ms")


def test_order_flow_attached():
    ms = MarketService()
    df = ms.get_market_data("BTCUSDT", "1h", 500)
    of = OrderFlow(imbalance=0.5, cvd_ratio=0.4, pressure=PressureLabel.BUY)
    res = analyze("BTCUSDT", "1h", df, order_flow=of)
    assert res.order_flow is not None and res.order_flow.pressure == PressureLabel.BUY
    # the long side's order-flow factor is now eligible (bias 0.45 > 0.12)
    of_factor = [f for f in res.long_plan.confluence.factors if f.name == "order_flow_aligned"]
    assert of_factor and of_factor[0].hit, "order-flow-aligned factor should hit for a strong buy"
    print(f"PASS order flow attached: long OF factor hit={of_factor[0].hit}")


def test_walk_forward_no_order_flow():
    ms = MarketService()
    df = ms.get_market_data("BTCUSDT", "1h", 500)
    res = analyze("BTCUSDT", "1h", df)  # no order flow (backtest/scanner path)
    assert res.order_flow is None
    of_factor = [f for f in res.long_plan.confluence.factors if f.name == "order_flow_aligned"]
    assert of_factor and not of_factor[0].hit, "OF factor cannot hit without order flow"
    print("PASS walk-forward: no order flow -> OF factor never hits")


if __name__ == "__main__":
    test_live_multi()
    test_order_flow_attached()
    test_walk_forward_no_order_flow()
    print("A12 OK")
