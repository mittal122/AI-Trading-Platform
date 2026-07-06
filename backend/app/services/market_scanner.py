"""Market-wide volume-spike scanner.

Fans out over the top-N most-liquid USDT pairs, reads each one's recent order
push (spike ratio + trade count) concurrently, and ranks them by a blended
"surge x size" score so the coins with unusually high order flow — that are
still liquid enough to actually trade — float to the top.

Layer note: BinanceProvider stays single-symbol (one klines call per coin);
this service owns the fan-out + ranking, the same split SignalScanner /
PatternScanner use.
"""

import math
from concurrent.futures import ThreadPoolExecutor

from backend.app.services.market_service import MarketService

# Only pairs above this 24h $ volume enter the universe — the hard liquidity
# gate that stops a surge on a dead micro-cap from topping the list.
_MIN_QUOTE_VOLUME = 1_000_000.0
# Stablecoin bases and leveraged-token suffixes: pure noise, never a trade.
_STABLE_BASES = {"USDC", "FDUSD", "TUSD", "DAI", "BUSD", "USDP", "EUR", "AEUR", "XUSD"}
_LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")
_MAX_WORKERS = 16


class VolumeScanner:
    def __init__(self):
        self.market = MarketService()

    def _liquid_universe(self, top: int) -> dict[str, float]:
        """Top `top` USDT pairs by 24h quote volume → {symbol: quote_volume}."""
        tickers = self.market.get_tickers_24h()  # cached
        liquid = [
            t for t in tickers
            if t["quote_volume"] >= _MIN_QUOTE_VOLUME
            and t["symbol"][:-4] not in _STABLE_BASES  # strip 'USDT'
            and not t["symbol"][:-4].endswith(_LEVERAGED_SUFFIXES)
        ]
        liquid.sort(key=lambda t: t["quote_volume"], reverse=True)
        return {t["symbol"]: t["quote_volume"] for t in liquid[:top]}

    def scan_market(
        self, interval: str = "5m", window: int = 20, top: int = 300, limit: int = 40,
    ) -> dict:
        """Scan the top `top` liquid coins, return the `limit` hottest by
        blended surge x size. A symbol that fails to fetch is dropped, not
        surfaced — a ranked opportunity board shouldn't show error rows."""
        universe = self._liquid_universe(top)

        def _one(symbol: str) -> dict | None:
            try:
                row = self.market.get_volume_scan(symbol, interval, window=window)
                row["quote_volume_24h"] = universe[symbol]
                return row
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            rows = [r for r in pool.map(_one, universe.keys()) if r]

        self._attach_blended_score(rows)
        rows.sort(key=lambda r: r["blended_score"], reverse=True)
        return {
            "interval": interval,
            "window": window,
            "scanned": len(rows),
            "rows": rows[:limit],
        }

    @staticmethod
    def _attach_blended_score(rows: list[dict]) -> None:
        """score = spike_ratio x size_factor, size_factor in [0.5, 1.0] scaled
        by log(quote_volume). Spike dominates the ranking (a 3x surge always
        beats a 1x one); size only nudges — it breaks ties and keeps a modest
        move on a mega-cap from outranking a genuine surge on a mid-cap."""
        qvs = [r["quote_volume_24h"] for r in rows if r.get("quote_volume_24h")]
        if qvs:
            lo, hi = math.log(min(qvs)), math.log(max(qvs))
            span = (hi - lo) or 1.0
        for r in rows:
            qv = r.get("quote_volume_24h") or 0.0
            size_factor = 0.5 + 0.5 * (math.log(qv) - lo) / span if qv > 0 and qvs else 0.5
            r["blended_score"] = round(r["spike_ratio"] * size_factor, 3)
