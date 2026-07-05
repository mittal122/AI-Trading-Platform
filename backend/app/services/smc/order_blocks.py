"""Order blocks (§5.4).

For every structure event, scan backwards up to OB_LOOKBACK_BARS from the bar
before the break for the first *opposite*-color candle:
  * last down candle before an up-break  -> bullish OB (its full high-low range)
  * last up candle   before a down-break -> bearish OB

Mitigation is checked from OB_MITIGATION_CHECK_FROM bars after formation and only
by a *decisive close* through the far side (a wick into the zone is the intended
entry retest, not mitigation): bullish OB mitigated when a candle closes below its
low; bearish OB when a candle closes above its high.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import Direction, OrderBlock, StructureEvent, StructureType


def _iso_times(df: pd.DataFrame) -> list[str]:
    return [t.isoformat() for t in df["timestamps"]]


def find_order_blocks(
    df: pd.DataFrame, events: list[StructureEvent],
) -> list[OrderBlock]:
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    times = _iso_times(df)
    n = len(df)
    lookback = smc_config.OB_LOOKBACK_BARS

    seen: set[tuple[int, str]] = set()
    obs: list[OrderBlock] = []

    for e in events:
        up = e.type in (StructureType.BOS_UP, StructureType.CHOCH_UP)
        start = e.index - 1
        origin = None
        for j in range(start, max(-1, start - lookback), -1):
            if j < 0:
                break
            is_down = closes[j] < opens[j]
            is_up = closes[j] > opens[j]
            if up and is_down:
                origin = j
                break
            if (not up) and is_up:
                origin = j
                break
        if origin is None:
            continue

        direction = Direction.BULLISH if up else Direction.BEARISH
        key = (origin, direction.value)
        if key in seen:
            continue
        seen.add(key)
        obs.append(OrderBlock(
            index=origin,
            time=times[origin],
            top=float(highs[origin]),
            bottom=float(lows[origin]),
            direction=direction,
        ))

    # Mitigation — decisive close through the far side only.
    check_from = smc_config.OB_MITIGATION_CHECK_FROM
    for ob in obs:
        for k in range(ob.index + check_from, n):
            if ob.direction == Direction.BULLISH and closes[k] < ob.bottom:
                ob.mitigated = True
                ob.mitigated_index = k
                break
            if ob.direction == Direction.BEARISH and closes[k] > ob.top:
                ob.mitigated = True
                ob.mitigated_index = k
                break

    obs.sort(key=lambda o: o.index)
    return obs
