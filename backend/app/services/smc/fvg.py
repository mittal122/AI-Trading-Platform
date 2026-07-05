"""Fair value gaps (§5.5).

Three-candle imbalance scan at bar i:
  * bullish FVG when candle[i+1].low  > candle[i-1].high (void = that gap)
  * bearish FVG when candle[i+1].high < candle[i-1].low

Fill (from FVG_FILL_CHECK_FROM bars after formation):
  * a bullish FVG fills when a later low trades down to its bottom
  * a bearish FVG fills when a later high reaches its top
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import Direction, FVG


def find_fvgs(df: pd.DataFrame) -> list[FVG]:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    times = [t.isoformat() for t in df["timestamps"]]
    n = len(df)
    fvgs: list[FVG] = []

    for i in range(1, n - 1):
        h_prev = highs[i - 1]
        l_prev = lows[i - 1]
        l_next = lows[i + 1]
        h_next = highs[i + 1]

        if l_next > h_prev:  # bullish imbalance
            fvgs.append(FVG(
                index=i, time=times[i],
                top=float(l_next), bottom=float(h_prev),
                direction=Direction.BULLISH,
            ))
        elif h_next < l_prev:  # bearish imbalance
            fvgs.append(FVG(
                index=i, time=times[i],
                top=float(l_prev), bottom=float(h_next),
                direction=Direction.BEARISH,
            ))

    fill_from = smc_config.FVG_FILL_CHECK_FROM
    for fvg in fvgs:
        for k in range(fvg.index + fill_from, n):
            if fvg.direction == Direction.BULLISH and lows[k] <= fvg.bottom:
                fvg.filled = True
                fvg.filled_index = k
                break
            if fvg.direction == Direction.BEARISH and highs[k] >= fvg.top:
                fvg.filled = True
                fvg.filled_index = k
                break

    return fvgs
