from backend.app.services.strategy.rsi_strategy import RSIStrategy
from backend.app.services.strategy.ema_strategy import EMAStrategy
from backend.app.services.strategy.macd_strategy import MACDStrategy
from backend.app.services.strategy.breakout_strategy import BreakoutStrategy
from backend.app.services.strategy.supertrend_strategy import SupertrendStrategy
from backend.app.services.strategy.cta_trend_strategy import CTATrendStrategy
from backend.app.services.strategy.turtle_strategy import TurtleStrategy
from backend.app.services.strategy.engulfing_scalp_strategy import EngulfingScalpStrategy


class StrategyFactory:

    STRATEGIES = {
        "rsi":        RSIStrategy,
        "ema":        EMAStrategy,
        "macd":       MACDStrategy,
        "breakout":   BreakoutStrategy,
        "supertrend": SupertrendStrategy,
        "cta_trend":  CTATrendStrategy,
        "turtle":     TurtleStrategy,
        "engulfing_scalp": EngulfingScalpStrategy,
    }

    @staticmethod
    def get_strategy(
        strategy: str = "rsi",
    ):

        strategy = strategy.lower()

        if strategy not in StrategyFactory.STRATEGIES:
            raise ValueError(
                f"Unknown strategy: {strategy}. "
                f"Available: {list(StrategyFactory.STRATEGIES.keys())}"
            )

        return StrategyFactory.STRATEGIES[strategy]()

    @staticmethod
    def list_strategies() -> list[str]:
        return list(StrategyFactory.STRATEGIES.keys())
