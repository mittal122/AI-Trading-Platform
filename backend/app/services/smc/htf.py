"""Higher-timeframe trend (§5.12).

The in-scope candles are resampled in-memory into synthetic HTF bars (no extra
API call, hence walk-forward safe). Bars per HTF candle come from
HTF_BARS_PER_CANDLE; the oldest partial group is dropped so the newest HTF bar is
always complete; aggregation is standard OHLC (first/max/min/last, summed
volume). If at least HTF_MIN_BARS HTF bars exist, the same swing + structure
algorithm runs on them to yield the HTF trend. Weekly/monthly (no mapping) ->
unavailable, and any gate involving HTF is skipped.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import HTFTrend, TrendState
from backend.app.services.smc.structure import analyze_structure
from backend.app.services.smc.swing import find_swings


def resample_htf(df: pd.DataFrame, bars_per: int) -> pd.DataFrame:
    """Aggregate every `bars_per` LTF candles into one HTF bar, dropping the
    oldest partial group so the newest HTF bar is complete."""
    n = len(df)
    groups = n // bars_per
    if groups == 0:
        return df.iloc[0:0]
    trimmed = df.iloc[n - groups * bars_per:]  # drop oldest partial

    rows = []
    for g in range(groups):
        chunk = trimmed.iloc[g * bars_per:(g + 1) * bars_per]
        rows.append({
            "timestamps": chunk["timestamps"].iloc[0],
            "open": float(chunk["open"].iloc[0]),
            "high": float(chunk["high"].max()),
            "low": float(chunk["low"].min()),
            "close": float(chunk["close"].iloc[-1]),
            "volume": float(chunk["volume"].sum()),
            "amount": float(chunk["amount"].sum()),
        })
    return pd.DataFrame(rows)


def compute_htf(df: pd.DataFrame, interval: str) -> HTFTrend:
    bars_per = smc_config.HTF_BARS_PER_CANDLE.get(interval)
    if bars_per is None:
        return HTFTrend(available=False, trend=TrendState.NEUTRAL, htf_bars=0)

    htf_df = resample_htf(df, bars_per)
    groups = len(htf_df)
    if groups < smc_config.HTF_MIN_BARS:
        return HTFTrend(available=False, trend=TrendState.NEUTRAL, htf_bars=groups)

    result = analyze_structure(find_swings(htf_df))
    return HTFTrend(available=True, trend=result.trend, htf_bars=groups)
