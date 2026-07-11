"""GET /portfolio/analytics/history must reflect the REAL recorded trades —
the same rows /trades/history returns — not a simulated backtest.

Requires the backend running on :8000 (same convention as the other live
endpoint tests in this repo).
"""

import urllib.request
import json

BASE = "http://localhost:8000/api/v1"


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=15) as r:
        return json.loads(r.read())


def test_history_analytics_matches_trade_history():
    analytics = _get("/portfolio/analytics/history")
    history = _get("/trades/history?limit=500")
    real_rows = [t for t in history["trades"] if t["mode"] != "BACKTEST"]

    assert analytics["total_trades"] == len(real_rows), (
        f"analytics counted {analytics['total_trades']} trades, "
        f"history has {len(real_rows)} non-backtest rows"
    )

    total_pnl = sum(t["pnl"] for t in real_rows)
    reported = analytics["ending_balance"] - analytics["initial_balance"]
    assert abs(reported - total_pnl) < 0.01, (
        f"analytics PnL {reported:.4f} != sum of trade PnL {total_pnl:.4f}"
    )

    wins = [t for t in real_rows if t["pnl"] > 0]
    assert analytics["winning_trades"] == len(wins)
    if real_rows:
        assert abs(analytics["win_rate"] - len(wins) / len(real_rows) * 100) < 0.01

    print(f"PASS: analytics mirrors {len(real_rows)} real trades, "
          f"PnL {reported:+.2f}, win rate {analytics['win_rate']}%")


def test_mode_filter_isolates_paper():
    paper = _get("/portfolio/analytics/history?mode=PAPER")
    history = _get("/trades/history?mode=PAPER&limit=500")
    assert paper["total_trades"] == history["total"]
    print(f"PASS: mode=PAPER analytics covers exactly {history['total']} paper trades")


if __name__ == "__main__":
    test_history_analytics_matches_trade_history()
    test_mode_filter_isolates_paper()
    print("\nRESULTS: all checks passed")
