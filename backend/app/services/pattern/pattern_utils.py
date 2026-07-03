import hashlib
from datetime import datetime, timezone

import pandas as pd

from backend.app.core.pattern_config import pattern_config
from backend.app.schemas.pattern import PatternDirection, PatternStatus


def make_pattern_id(symbol: str, interval: str, pattern_type: str, formation_start: str) -> str:
    raw = f"{symbol}:{interval}:{pattern_type}:{formation_start}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def status_from_breakout(
    direction: PatternDirection,
    current_price: float,
    breakout_level: float,
    invalidation_level: float,
    atr: float,
) -> PatternStatus:
    """
    DEVELOPING — still forming, price hasn't cleared the breakout level by a
    meaningful margin yet.
    CONFIRMED — price cleared breakout_level by >= BREAKOUT_CONFIRMATION_ATR_MULT * ATR
    in the pattern's direction.
    BROKEN — price moved past invalidation_level against the pattern.
    """
    margin = pattern_config.BREAKOUT_CONFIRMATION_ATR_MULT * atr

    if direction == PatternDirection.BULLISH:
        if invalidation_level is not None and current_price < invalidation_level:
            return PatternStatus.BROKEN
        if breakout_level is not None and current_price >= breakout_level + margin:
            return PatternStatus.CONFIRMED
    elif direction == PatternDirection.BEARISH:
        if invalidation_level is not None and current_price > invalidation_level:
            return PatternStatus.BROKEN
        if breakout_level is not None and current_price <= breakout_level - margin:
            return PatternStatus.CONFIRMED

    return PatternStatus.DEVELOPING


def measured_move_targets(
    direction: PatternDirection, breakout_level: float, measured_move: float
) -> tuple[float, float, float]:
    """Target 1 = the pattern's own measured move projected from breakout.
    Targets 2/3 are fib-style extensions beyond it — the standard convention
    for continuation targets once T1 looks achievable."""
    sign = 1 if direction == PatternDirection.BULLISH else -1
    measured_move = abs(measured_move)
    t1 = breakout_level + sign * measured_move
    t2 = breakout_level + sign * measured_move * pattern_config.TARGET_2_MEASURED_MOVE_MULTIPLIER
    t3 = breakout_level + sign * measured_move * pattern_config.TARGET_3_MEASURED_MOVE_MULTIPLIER
    return t1, t2, t3


def risk_reward(entry: float, stop_loss: float, target_1: float) -> float:
    risk = abs(entry - stop_loss)
    reward = abs(target_1 - entry)
    return round(reward / risk, 2) if risk > 0 else 0.0


def volume_confirmation_score(df: pd.DataFrame, start_idx: int, end_idx: int) -> float:
    """Rewards a pattern where volume ramps toward the end of formation
    (interest building into a potential breakout) — 0-100 scale."""
    volumes = df["volume"].to_numpy()[start_idx: end_idx + 1]
    if len(volumes) < 4:
        return 50.0
    first_half = volumes[: len(volumes) // 2].mean()
    second_half = volumes[len(volumes) // 2:].mean()
    if first_half <= 0:
        return 50.0
    ratio = second_half / first_half
    score = 50.0 + (ratio - 1.0) * 50.0  # ratio 1.0 -> 50, 2.0+ -> 100, 0.5- -> 0
    return clamp(score)


def algorithmic_confidence(
    geometry_fit: float,
    volume_confirmation: float,
    breakout_strength: float,
    pattern_size: float,
) -> float:
    cfg = pattern_config
    score = (
        geometry_fit * cfg.CONF_WEIGHT_GEOMETRY_FIT
        + volume_confirmation * cfg.CONF_WEIGHT_VOLUME_CONFIRMATION
        + breakout_strength * cfg.CONF_WEIGHT_BREAKOUT_STRENGTH
        + pattern_size * cfg.CONF_WEIGHT_PATTERN_SIZE
    )
    return round(clamp(score), 2)


def breakout_strength_score(current_price: float, breakout_level: float, atr: float) -> float:
    """How far price has already moved past the breakout level, in ATR units — 0-100 scale."""
    if not breakout_level or not atr or atr <= 0:
        return 30.0
    atr_multiples = abs(current_price - breakout_level) / atr
    return clamp(atr_multiples * 60.0)  # ~1.67 ATR past breakout maxes the score
