import pandas as pd

from backend.app.core.pattern_config import pattern_config


class SwingPoint:

    def __init__(self, index: int, time, price: float, kind: str):
        self.index = index
        self.time = time
        self.price = price
        self.kind = kind  # "high" or "low"

    def __repr__(self):
        return f"SwingPoint({self.kind}, idx={self.index}, price={self.price:.4f})"


class SwingDetector:
    """
    Fractal pivot detection — a bar is a swing high if its high is the
    strict highest within `lookback` bars on both sides (swing low mirrors
    this on the low). This is the shared geometric primitive nearly every
    classical chart pattern is built from: peaks/troughs for tops/bottoms
    and head & shoulders, anchor points for trendline fitting in triangles/
    wedges/channels, and structural pivots for BOS/CHOCH in SMC detection.
    """

    def __init__(self, lookback: int = None):
        self.lookback = lookback or pattern_config.SWING_LOOKBACK

    def find_swings(self, df: pd.DataFrame) -> list[SwingPoint]:
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        times = df["timestamps"].to_numpy()
        n = len(df)
        lb = self.lookback

        swings: list[SwingPoint] = []

        for i in range(lb, n - lb):
            window_high = highs[i - lb: i + lb + 1]
            if highs[i] == window_high.max() and (window_high == highs[i]).sum() == 1:
                swings.append(SwingPoint(i, times[i].item(), float(highs[i]), "high"))

            window_low = lows[i - lb: i + lb + 1]
            if lows[i] == window_low.min() and (window_low == lows[i]).sum() == 1:
                swings.append(SwingPoint(i, times[i].item(), float(lows[i]), "low"))

        swings.sort(key=lambda s: s.index)
        return swings

    def swing_highs(self, df: pd.DataFrame) -> list[SwingPoint]:
        return [s for s in self.find_swings(df) if s.kind == "high"]

    def swing_lows(self, df: pd.DataFrame) -> list[SwingPoint]:
        return [s for s in self.find_swings(df) if s.kind == "low"]
