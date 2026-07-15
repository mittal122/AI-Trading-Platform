import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import FairValueGap, FVGType
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.pattern_utils import clamp, make_pattern_id, now_iso
from backend.app.services.pattern.swing_detector import _to_datetime


class FVGDetector:
    """
    Fair Value Gap — a 3-candle imbalance where the market moved so fast it
    left a price range untraded:
      Bullish FVG: low[candle 3] > high[candle 1]  (gap = [high1, low3])
      Bearish FVG: high[candle 3] < low[candle 1]   (gap = [high3, low1])
    candle 2 is the displacement candle in between. "Filled" means price
    later traded back into the gap zone; "strength" scales with gap size
    relative to ATR (a wider imbalance = a stronger institutional signature).
    """

    def __init__(self):
        self.indicators = IndicatorService()

    def detect(self, df: pd.DataFrame, symbol: str, interval: str) -> list[FairValueGap]:
        cfg = pattern_config
        n = len(df)
        lookback_start = max(2, n - cfg.FVG_LOOKBACK_BARS)

        atr = self.indicators.calculate_atr_at_period(df, 14)
        if not atr or atr <= 0:
            return []

        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        times = df["timestamps"].to_numpy()

        gaps: list[FairValueGap] = []

        for i in range(lookback_start, n):
            c1, c3 = i - 2, i
            if c1 < 0:
                continue

            if low[c3] > high[c1]:
                gap_bottom, gap_top = float(high[c1]), float(low[c3])
                gap_type = FVGType.BULLISH
            elif high[c3] < low[c1]:
                gap_bottom, gap_top = float(high[c3]), float(low[c1])
                gap_type = FVGType.BEARISH
            else:
                continue

            gap_size = gap_top - gap_bottom
            if gap_size / atr < cfg.FVG_MIN_GAP_ATR_RATIO:
                continue

            filled = False
            filled_at = None
            for j in range(i + 1, n):
                if low[j] <= gap_top and high[j] >= gap_bottom:
                    filled = True
                    filled_at = _to_datetime(times[j].item()).isoformat()
                    break

            strength = clamp((gap_size / atr) / cfg.FVG_STRONG_ATR_RATIO * 100)

            formed_at = _to_datetime(times[i - 1].item()).isoformat()
            gaps.append(
                FairValueGap(
                    id=make_pattern_id(symbol, interval, f"fvg_{gap_type.value.lower()}", formed_at),
                    symbol=symbol,
                    interval=interval,
                    type=gap_type,
                    top=round(gap_top, 8),
                    bottom=round(gap_bottom, 8),
                    formed_at=formed_at,
                    filled=filled,
                    filled_at=filled_at,
                    strength=round(strength, 2),
                    last_updated=now_iso(),
                )
            )

        return gaps
