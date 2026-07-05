"""ATR (§5.11).

A 14-period *simple* average of Wilder's True Range (max of high-low,
|high-prevClose|, |low-prevClose|) — NOT the RMA-smoothed variant. ATR
parameterizes nearly every threshold in the engine, so it is computed directly
per the doc. Fallback = max(2% of price, floor) when the series is too short.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config


def compute_atr(df: pd.DataFrame, period: int | None = None) -> float:
    period = period or smc_config.ATR_PERIOD
    n = len(df)
    last_close = float(df["close"].iloc[-1]) if n else 0.0
    fallback = max(smc_config.ATR_FALLBACK_PRICE_PCT * last_close,
                   smc_config.ATR_FALLBACK_FLOOR)

    if n < period + 1:
        return fallback

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()

    trs = []
    for i in range(1, n):
        prev_close = closes[i - 1]
        trs.append(max(
            highs[i] - lows[i],
            abs(highs[i] - prev_close),
            abs(lows[i] - prev_close),
        ))

    atr = float(sum(trs[-period:]) / period)
    return atr if atr > 0 else fallback
