"""Volume context (§5 step 7).

Two reads over the recent window:
  * ratio    — last VOLUME_RECENT_BARS average vs the prior VOLUME_PRIOR_BARS
               average (a spike when > VOLUME_SPIKE_RATIO).
  * trendVol — net up-vs-down volume over the recent window, in -1..+1
               (up-candle volume minus down-candle volume, normalized).

Returns a zeroed context when there is no volume data.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import VolumeContext


def compute_volume(df: pd.DataFrame) -> VolumeContext:
    recent_n = smc_config.VOLUME_RECENT_BARS
    prior_n = smc_config.VOLUME_PRIOR_BARS

    vol = df["volume"].to_numpy()
    opens = df["open"].to_numpy()
    closes = df["close"].to_numpy()

    if len(df) == 0 or float(vol.sum()) <= 0:
        return VolumeContext(ratio=1.0, trend_vol=0.0, spike=False)

    recent = vol[-recent_n:]
    prior = vol[-(recent_n + prior_n):-recent_n]
    recent_avg = float(recent.mean()) if len(recent) else 0.0
    prior_avg = float(prior.mean()) if len(prior) else 0.0
    ratio = recent_avg / prior_avg if prior_avg > 0 else 1.0

    up = down = 0.0
    for i in range(max(0, len(df) - recent_n), len(df)):
        if closes[i] > opens[i]:
            up += vol[i]
        elif closes[i] < opens[i]:
            down += vol[i]
    total = up + down
    trend_vol = (up - down) / total if total > 0 else 0.0

    return VolumeContext(
        ratio=ratio,
        trend_vol=trend_vol,
        spike=ratio > smc_config.VOLUME_SPIKE_RATIO,
    )
