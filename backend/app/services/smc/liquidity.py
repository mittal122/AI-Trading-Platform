"""Liquidity pools & sweeps (§5.6-5.7).

Pools (equal highs / equal lows): within the last LIQUIDITY_WINDOW_BARS, every
pair of swing highs within tolerance forms an equal-highs pool (buy-side
liquidity above -> bearish magnet) at their average price; every pair of swing
lows forms an equal-lows pool (sell-side liquidity below -> bullish magnet).
Tolerance = LIQUIDITY_TOLERANCE_PCT of the window's total range (floored).

Sweeps: for each pool, the first candle to poke beyond the pool price + tolerance
starts a stop-hunt; it is *confirmed* only if within the next 1-2 bars a candle
closes back through the level. A bare poke without a close-back is not a sweep.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import Direction, LiquidityPool, LiquiditySweep, Swing


def _window_tolerance(df: pd.DataFrame) -> tuple[float, int]:
    """Tolerance (price units) + the start index of the lookback window."""
    n = len(df)
    start = max(0, n - smc_config.LIQUIDITY_WINDOW_BARS)
    window = df.iloc[start:]
    rng = float(window["high"].max() - window["low"].min())
    tol = max(rng * smc_config.LIQUIDITY_TOLERANCE_PCT / 100.0,
              smc_config.LIQUIDITY_TOLERANCE_FLOOR)
    return tol, start


def find_liquidity_pools(df: pd.DataFrame, swings: list[Swing]) -> list[LiquidityPool]:
    tol, start = _window_tolerance(df)
    highs = [s for s in swings if s.is_high and s.index >= start]
    lows = [s for s in swings if not s.is_high and s.index >= start]

    pools: list[LiquidityPool] = []

    def pair_up(points: list[Swing], direction: Direction):
        for a in range(len(points)):
            for b in range(a + 1, len(points)):
                if abs(points[a].price - points[b].price) <= tol:
                    pools.append(LiquidityPool(
                        price=(points[a].price + points[b].price) / 2,
                        direction=direction,
                        swing_indices=[points[a].index, points[b].index],
                    ))

    pair_up(highs, Direction.BEARISH)   # equal highs = buy-side above
    pair_up(lows, Direction.BULLISH)    # equal lows  = sell-side below
    return pools


def find_sweeps(df: pd.DataFrame, pools: list[LiquidityPool]) -> list[LiquiditySweep]:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    n = len(df)
    tol, _ = _window_tolerance(df)
    confirm = smc_config.SWEEP_CONFIRM_BARS
    recency = smc_config.SWEEP_REVERSAL_RECENCY_BARS

    sweeps: list[LiquiditySweep] = []
    for pool in pools:
        formation = max(pool.swing_indices)
        p = pool.price
        equal_highs = pool.direction == Direction.BEARISH

        for k in range(formation + 1, n):
            poked = highs[k] > p + tol if equal_highs else lows[k] < p - tol
            if not poked:
                continue
            reversal = None
            for j in range(k, min(n, k + confirm + 1)):
                closed_back = closes[j] < p if equal_highs else closes[j] > p
                if closed_back:
                    reversal = j
                    break
            if reversal is not None:
                sweeps.append(LiquiditySweep(
                    pool_price=p,
                    direction=pool.direction,
                    sweep_index=k,
                    reversal_index=reversal,
                    recent=(reversal >= n - 1 - recency),
                ))
                break  # one confirmed sweep per pool
    return sweeps


def recent_swings(swings: list[Swing]) -> list[Swing]:
    """Last N swings kept as reference points for stop placement (§7.3)."""
    return swings[-smc_config.LIQUIDITY_RECENT_SWINGS:]
