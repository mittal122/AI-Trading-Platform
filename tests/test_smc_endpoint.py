"""A13 — SMC API endpoints.

Exercises the route functions directly (no server boot needed): full analysis
response shape + the 400 guards. Live curl through the running server was also
verified during development.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_endpoint.py
"""

import backend.app.core.config  # noqa: F401

from fastapi import HTTPException

from backend.app.api.v1.smc import smc_analyze, smc_analyze_get, smc_health
from backend.app.schemas.smc import AnalysisRequest, AnalysisResult


def test_health():
    assert smc_health()["status"] == "ok"
    print("PASS health")


def test_post_and_get():
    res = smc_analyze(AnalysisRequest(symbol="BTCUSDT", interval="1h", limit=300))
    assert isinstance(res, AnalysisResult)
    assert len(res.candles) == 300 and res.verdict is not None
    assert res.long_plan is not None and res.short_plan is not None

    res2 = smc_analyze_get("ETHUSDT", "1h", 200)
    assert isinstance(res2, AnalysisResult) and res2.symbol == "ETHUSDT"
    print(f"PASS post/get: BTC verdict={res.verdict.label.value} primary={res.primary}, "
          f"ETH candles={len(res2.candles)}")


def test_bad_interval_400():
    try:
        smc_analyze(AnalysisRequest(symbol="BTCUSDT", interval="99z", limit=300))
        raise AssertionError("expected HTTPException")
    except HTTPException as e:
        assert e.status_code == 400
    print("PASS bad interval -> 400")


if __name__ == "__main__":
    test_health()
    test_post_and_get()
    test_bad_interval_400()
    print("A13 OK")
