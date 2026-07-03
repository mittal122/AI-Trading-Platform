from backend.app.core.strategy_config import strategy_config
from backend.app.core.time_utils import candles_to_display


class TimeToTargetEstimator:
    """
    Approximates how many candles a signal needs to reach its take-profit —
    an ATR-velocity heuristic (no trade history required), so every live
    signal ships with an ETA. Once real trade history exists for a
    strategy/symbol/interval, prefer BacktestResult.avg_candles_to_win —
    that's measured, this is a rough estimate for signals with no history yet.
    """

    REGIME_MULTIPLIERS = {
        "STRONG_BULL": strategy_config.ETA_REGIME_STRONG_MULTIPLIER,
        "STRONG_BEAR": strategy_config.ETA_REGIME_STRONG_MULTIPLIER,
        "WEAK_BULL": strategy_config.ETA_REGIME_WEAK_MULTIPLIER,
        "WEAK_BEAR": strategy_config.ETA_REGIME_WEAK_MULTIPLIER,
        "SIDEWAYS": strategy_config.ETA_REGIME_SIDEWAYS_MULTIPLIER,
    }

    def estimate(
        self,
        entry: float,
        take_profit: float,
        atr: float,
        interval: str,
        regime: str = None,
    ) -> tuple[int, str]:
        """Returns (eta_candles, human-readable display string)."""

        if not atr or atr <= 0:
            return None, None

        reward_distance = abs(take_profit - entry)
        if reward_distance <= 0:
            return None, None

        multiplier = self.REGIME_MULTIPLIERS.get(regime, strategy_config.ETA_REGIME_WEAK_MULTIPLIER)
        progress_per_candle = atr * strategy_config.ETA_ATR_PROGRESS_FACTOR * multiplier

        if progress_per_candle <= 0:
            return None, None

        eta_candles = max(1, round(reward_distance / progress_per_candle))
        eta_display = candles_to_display(eta_candles, interval)

        return eta_candles, eta_display
