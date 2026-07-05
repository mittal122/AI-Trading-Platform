"""Dealing range — premium / discount / equilibrium (§5.1 step 6).

Over the last DEALING_RANGE_BARS: rangeHi/rangeLo, equilibrium midpoint, and the
current price's normalized position pos=(close-lo)/range. Longs are cheap in the
lower half ("discount"), expensive in the upper half ("premium"); the
EQUILIBRIUM_LOW..EQUILIBRIUM_HIGH band is a no-edge dead zone.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import DealingRange


def compute_dealing_range(df: pd.DataFrame) -> DealingRange:
    window = df.iloc[-smc_config.DEALING_RANGE_BARS:]
    hi = float(window["high"].max())
    lo = float(window["low"].min())
    close = float(df["close"].iloc[-1])
    rng = hi - lo

    if rng <= 0:
        return DealingRange(range_hi=hi, range_lo=lo, equilibrium=hi,
                            position=0.5, zone="equilibrium")

    pos = (close - lo) / rng
    if smc_config.EQUILIBRIUM_LOW <= pos <= smc_config.EQUILIBRIUM_HIGH:
        zone = "equilibrium"
    elif pos > 0.5:
        zone = "premium"
    else:
        zone = "discount"

    return DealingRange(
        range_hi=hi, range_lo=lo, equilibrium=(hi + lo) / 2,
        position=pos, zone=zone,
    )
