"""A6 — SMC ATR + higher-timeframe trend (§5.11-5.12).

ATR: constant-range series -> ATR == range; short series -> fallback.
HTF: resample aggregation exactness, availability gating, a synthetic HTF
uptrend (via exact LTF->HTF expansion), and live consistency.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_htf.py
"""

import backend.app.core.config  # noqa: F401

from datetime import datetime, timedelta

import pandas as pd

from backend.app.schemas.smc import TrendState
from backend.app.services.market_service import MarketService
from backend.app.services.smc.atr import compute_atr
from backend.app.services.smc.htf import compute_htf, resample_htf
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings


def _df(rows: list[dict]) -> pd.DataFrame:
    t0 = datetime(2026, 1, 1)
    for i, r in enumerate(rows):
        r["timestamps"] = t0 + timedelta(hours=i)
        r.setdefault("volume", 100.0)
        r.setdefault("amount", 100.0 * r["close"])
    return pd.DataFrame(rows)


def test_atr():
    # constant 10-wide bars, no gaps -> TR == 10 -> ATR == 10
    rows = [{"open": 105, "high": 110, "low": 100, "close": 105} for _ in range(20)]
    atr = compute_atr(_df(rows), 14)
    assert abs(atr - 10.0) < 1e-9, f"ATR {atr} != 10"

    # too-short series -> fallback max(2% of price, floor)
    short = _df([{"open": 100, "high": 101, "low": 99, "close": 100} for _ in range(5)])
    fb = compute_atr(short, 14)
    assert abs(fb - 2.0) < 1e-9, f"fallback {fb} != 2.0 (2% of 100)"
    print(f"PASS atr: constant-range->10.0, short-series->fallback {fb}")


def test_resample_exact():
    # 2 groups of 24; put high/low/open/close at known bars per group
    rows = []
    for i in range(48):
        rows.append({"open": 12.0, "high": 12.5, "low": 11.5, "close": 12.0})
    # group 0
    rows[0].update(open=10.0)
    rows[3].update(high=20.0)
    rows[7].update(low=5.0)
    rows[23].update(close=15.0)
    # group 1
    rows[24].update(open=15.0)
    rows[30].update(high=30.0)
    rows[35].update(low=10.0)   # below the 11.5 filler low
    rows[47].update(close=25.0)
    htf = resample_htf(_df(rows), 24)
    assert len(htf) == 2, len(htf)
    r0, r1 = htf.iloc[0], htf.iloc[1]
    assert (r0.open, r0.high, r0.low, r0.close) == (10.0, 20.0, 5.0, 15.0), tuple(r0[["open","high","low","close"]])
    assert (r1.open, r1.high, r1.low, r1.close) == (15.0, 30.0, 10.0, 25.0), tuple(r1[["open","high","low","close"]])
    print("PASS resample: 2 HTF bars, exact OHLC (first/max/min/last)")


def _ramp(a, b, n):
    return [b] if n == 1 else [a + (b - a) * i / (n - 1) for i in range(n)]


def _htf_target(pivots, gap=8):
    # A2-style value path, but open==close==v so LTF expansion is exact
    nodes = [pivots[0][1] + 15] + [p for _, p in pivots] + [pivots[-1][1] + 15]
    vals = []
    for s in range(len(nodes) - 1):
        seg = _ramp(nodes[s], nodes[s + 1], gap)
        vals += seg if s == 0 else seg[1:]
    return [{"open": v, "high": v + 0.4, "low": v - 0.4, "close": v} for v in vals]


def _expand(htf_bars, bars_per):
    ltf = []
    for b in htf_bars:
        for j in range(bars_per):
            ltf.append({
                "open": b["close"],
                "high": b["high"] if j == 0 else b["close"],
                "low": b["low"] if j == 0 else b["close"],
                "close": b["close"],
            })
    return ltf


def test_htf_uptrend():
    pivots = [("low", 100), ("high", 120), ("low", 110), ("high", 135),
              ("low", 122), ("high", 150), ("low", 138), ("high", 165)]
    htf_bars = _htf_target(pivots)
    ltf = _expand(htf_bars, 7)          # interval 1d -> 7 bars per HTF candle
    df = _df(ltf)
    result = compute_htf(df, "1d")
    assert result.available, f"HTF should be available ({result.htf_bars} bars)"
    assert result.trend == TrendState.UP, f"expected UP HTF trend, got {result.trend}"
    print(f"PASS htf uptrend: {result.htf_bars} HTF bars, trend={result.trend.value}")


def test_htf_gating():
    # weekly has no HTF mapping
    df = _df([{"open": 100, "high": 101, "low": 99, "close": 100} for _ in range(500)])
    assert not compute_htf(df, "1w").available, "1w must be unavailable (no mapping)"
    # too few HTF bars: 1h needs 24/bar; 200 bars -> 8 groups < 15
    small = _df([{"open": 100, "high": 101, "low": 99, "close": 100} for _ in range(200)])
    r = compute_htf(small, "1h")
    assert not r.available and r.htf_bars == 8, (r.available, r.htf_bars)
    print("PASS htf gating: 1w unavailable, 1h/200 -> 8 bars (unavailable)")


def test_live():
    df = MarketService().get_market_data("BTCUSDT", "1h", 500)
    atr = compute_atr(df)
    r = compute_htf(df, "1h")
    direct = analyze_structure(find_swings(resample_htf(df, 24))).trend
    assert atr > 0
    assert r.available and r.htf_bars == 500 // 24
    assert r.trend == direct, f"compute_htf {r.trend} != direct {direct}"
    print(f"PASS live BTCUSDT/1h: ATR={atr:.2f}, HTF {r.htf_bars} bars "
          f"trend={r.trend.value} (consistent)")


if __name__ == "__main__":
    test_atr()
    test_resample_exact()
    test_htf_uptrend()
    test_htf_gating()
    test_live()
    print("A6 OK")
