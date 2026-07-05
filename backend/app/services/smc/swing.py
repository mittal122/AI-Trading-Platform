"""Swing detection (§5.2).

Thin adapter over the shared fractal SwingDetector, producing SMC `Swing` DTOs.
A bar is a swing high if its high is the strict maximum within SWING_LENGTH bars
on both sides (mirror for lows); ties disqualify. This is the only place the
engine reads raw fractal geometry — everything downstream consumes `Swing`s.
"""

import pandas as pd

from backend.app.core.smc_config import smc_config
from backend.app.schemas.smc import Swing
from backend.app.services.pattern.swing_detector import SwingDetector


def _iso(t) -> str:
    """SwingPoint.time is a native datetime (via numpy `.item()`); ISO-format it."""
    return t.isoformat() if hasattr(t, "isoformat") else str(t)


def find_swings(df: pd.DataFrame) -> list[Swing]:
    detector = SwingDetector(lookback=smc_config.SWING_LENGTH)
    points = detector.find_swings(df)
    return [
        Swing(
            index=p.index,
            time=_iso(p.time),
            price=p.price,
            is_high=(p.kind == "high"),
        )
        for p in points
    ]
