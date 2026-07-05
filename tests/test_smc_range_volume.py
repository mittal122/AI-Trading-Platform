"""A5 — SMC dealing range + volume context (§5.1.6, §5 step 7).

Synthetic: known price position -> premium/discount/equilibrium; directional
volume -> trendVol sign + spike. Plus live BTCUSDT smoke.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_range_volume.py
"""

import backend.app.core.config  # noqa: F401

from datetime import datetime, timedelta

import pandas as pd

from backend.app.services.market_service import MarketService
from backend.app.services.smc.dealing_range import compute_dealing_range
from backend.app.services.smc.volume import compute_volume


def build(n: int, default: dict, ov: dict[int, dict]) -> pd.DataFrame:
    t0 = datetime(2026, 1, 1)
    rows = []
    for i in range(n):
        d = {**default, **ov.get(i, {})}
        rows.append({
            "timestamps": t0 + timedelta(hours=i),
            "open": d["open"], "high": d["high"], "low": d["low"],
            "close": d["close"], "volume": d["volume"],
            "amount": d["volume"] * d["close"],
        })
    return pd.DataFrame(rows)


def _range_df(last_close: float) -> pd.DataFrame:
    default = {"open": 150, "high": 190, "low": 110, "close": 150, "volume": 100}
    ov = {0: {"low": 100}, 1: {"high": 200}, 59: {"close": last_close}}
    return build(60, default, ov)  # rangeLo=100 rangeHi=200 range=100


def test_dealing_range():
    cases = {125: ("discount", 0.25), 150: ("equilibrium", 0.50),
             180: ("premium", 0.80)}
    for close, (zone, pos) in cases.items():
        dr = compute_dealing_range(_range_df(close))
        assert dr.range_hi == 200 and dr.range_lo == 100, (dr.range_hi, dr.range_lo)
        assert dr.zone == zone, f"close {close}: zone {dr.zone} != {zone}"
        assert abs(dr.position - pos) < 1e-6, f"pos {dr.position} != {pos}"
    print("PASS dealing range: 0.25->discount, 0.50->equilibrium, 0.80->premium")


def test_volume():
    # recent 20 up-candles vol 200; prior 40 flat vol 100 -> trendVol +1, spike
    default = {"open": 100, "high": 101, "low": 99, "close": 100, "volume": 100}
    ov = {}
    for i in range(50, 70):  # last 20 bars: up candles, double volume
        ov[i] = {"open": 100, "close": 102, "high": 103, "low": 99, "volume": 200}
    vc = compute_volume(build(70, default, ov))
    assert abs(vc.trend_vol - 1.0) < 1e-9, f"trendVol {vc.trend_vol}"
    assert abs(vc.ratio - 2.0) < 1e-9, f"ratio {vc.ratio}"
    assert vc.spike, "2x prior volume should flag a spike"

    # down-dominant recent -> negative trendVol
    ov2 = {i: {"open": 102, "close": 100, "high": 103, "low": 99, "volume": 150}
           for i in range(50, 70)}
    vc2 = compute_volume(build(70, default, ov2))
    assert vc2.trend_vol < 0, f"expected negative trendVol, got {vc2.trend_vol}"

    # no volume -> zeroed
    vc3 = compute_volume(build(70, {**default, "volume": 0}, {}))
    assert vc3.trend_vol == 0.0 and vc3.ratio == 1.0 and not vc3.spike
    print(f"PASS volume: up->+1(spike), down->{vc2.trend_vol:.2f}, novol->0")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 300)
    dr = compute_dealing_range(df)
    vc = compute_volume(df)
    assert dr.zone in ("premium", "discount", "equilibrium")
    assert 0 <= dr.position <= 1, dr.position
    assert -1 <= vc.trend_vol <= 1, vc.trend_vol
    print(f"PASS live BTCUSDT/1h: zone={dr.zone} pos={dr.position:.2f} "
          f"trendVol={vc.trend_vol:.2f} ratio={vc.ratio:.2f} spike={vc.spike}")


if __name__ == "__main__":
    test_dealing_range()
    test_volume()
    test_live()
    print("A5 OK")
