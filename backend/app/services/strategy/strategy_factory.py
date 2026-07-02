from backend.app.services.strategy.rsi_strategy import RSIStrategy
from backend.app.services.strategy.ema_strategy import EMAStrategy
from backend.app.services.strategy.macd_strategy import MACDStrategy
from backend.app.services.strategy.breakout_strategy import BreakoutStrategy
from backend.app.services.strategy.supertrend_strategy import SupertrendStrategy
from backend.app.services.strategy.cta_trend_strategy import CTATrendStrategy
from backend.app.services.strategy.turtle_strategy import TurtleStrategy
from backend.app.services.strategy.engulfing_scalp_strategy import EngulfingScalpStrategy


class StrategyFactory:

    @staticmethod
    def get_strategy(
        strategy: str = "rsi",
    ):

        strategy = strategy.lower()

        strategies = {
            "rsi":        RSIStrategy,
            "ema":        EMAStrategy,
            "macd":       MACDStrategy,
            "breakout":   BreakoutStrategy,
            "supertrend": SupertrendStrategy,
            "cta_trend":  CTATrendStrategy,
            "turtle":     TurtleStrategy,
            "engulfing_scalp": EngulfingScalpStrategy,
        }

        if strategy not in strategies:
            raise ValueError(
                f"Unknown strategy: {strategy}. "
                f"Available: {list(strategies.keys())}"
            )

        return strategies[strategy]()
