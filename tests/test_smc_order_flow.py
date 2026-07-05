"""A11 — SMC order flow (§8).

Pure compute_order_flow tests (band filter, imbalance, walls, CVD, non-fatal
trades, ATR band widening) + a live fetch through Binance.
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_order_flow.py
"""

import backend.app.core.config  # noqa: F401

from backend.app.schemas.smc import PressureLabel
from backend.app.services.market_service import MarketService
from backend.app.services.smc.order_flow import compute_order_flow, fetch_order_flow


def test_band_imbalance_walls():
    price = 1000.0
    bids = [(1000, 2), (999, 2), (998, 2), (997, 2), (992, 40), (985, 100)]  # 985 out of band
    asks = [(1005, 2), (1006, 2), (1007, 2), (1008, 2), (1020, 100)]        # 1020 out
    of = compute_order_flow(bids, asks, None, atr=0.0, price=price)  # band = 1% = [990,1010]
    # bid_vol 48 (990..1010), ask_vol 8 -> imbalance (48-8)/56 = 0.714 -> BUY
    assert abs(of.imbalance - (40 / 56)) < 1e-9, of.imbalance
    assert of.pressure == PressureLabel.BUY
    # wall at 992 (qty 40 >= 4x mean 9.6); the out-of-band 985/1020 excluded
    assert len(of.bid_walls) == 1 and of.bid_walls[0]["price"] == 992, of.bid_walls
    assert abs(of.bid_walls[0]["distance_pct"] - 0.8) < 1e-9
    assert of.ask_walls == []
    print(f"PASS band/imbalance/walls: imbalance={of.imbalance:.3f} BUY, 1 bid wall @992")


def test_cvd():
    of = compute_order_flow(
        [(1000, 1)], [(1001, 1)],
        [{"qty": 10, "is_buyer_maker": False}, {"qty": 5, "is_buyer_maker": False},
         {"qty": 3, "is_buyer_maker": True}],
        atr=0.0, price=1000,
    )
    # buy 15, sell 3 -> cvd (12)/18 = 0.667
    assert abs(of.cvd_ratio - (12 / 18)) < 1e-9, of.cvd_ratio
    # non-fatal: no trades -> cvd 0
    of2 = compute_order_flow([(1000, 1)], [(1001, 1)], None, 0.0, 1000)
    assert of2.cvd_ratio == 0.0
    print(f"PASS cvd: +0.667 from taker buys; None trades -> 0 (non-fatal)")


def test_balanced_and_atr_band():
    # symmetric book -> imbalance 0 -> balanced
    of = compute_order_flow([(1000, 5)], [(1001, 5)], None, 0.0, 1000)
    assert of.pressure == PressureLabel.BALANCED and of.imbalance == 0.0
    # atr band widens: atr=10 -> band max(10,20)=20 -> [980,1020] includes 985/1015
    bids = [(1000, 5), (985, 5)]
    asks = [(1001, 5), (1015, 5)]
    narrow = compute_order_flow(bids, asks, None, atr=0.0, price=1000)   # band 10
    wide = compute_order_flow(bids, asks, None, atr=10.0, price=1000)    # band 20
    assert narrow.bid_notional < wide.bid_notional, "ATR band should include more levels"
    print("PASS balanced + ATR band widening (985/1015 pulled in at atr=10)")


def test_live():
    ms = MarketService()
    price = float(ms.get_market_data("BTCUSDT", "1h", 2)["close"].iloc[-1])
    of = fetch_order_flow(ms, "BTCUSDT", atr=0.0, price=price)
    assert -1 <= of.imbalance <= 1 and -1 <= of.cvd_ratio <= 1
    assert of.pressure in (PressureLabel.BUY, PressureLabel.SELL, PressureLabel.BALANCED)
    print(f"PASS live BTCUSDT: imbalance={of.imbalance:.3f} cvd={of.cvd_ratio:.3f} "
          f"pressure={of.pressure.value} bid_walls={len(of.bid_walls)} ask_walls={len(of.ask_walls)}")


if __name__ == "__main__":
    test_band_imbalance_walls()
    test_cvd()
    test_balanced_and_atr_band()
    test_live()
    print("A11 OK")
