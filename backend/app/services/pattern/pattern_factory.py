from backend.app.services.pattern.single_candle_patterns import SingleCandlePatternDetector
from backend.app.services.pattern.smc_detector import SMCDetector
from backend.app.services.pattern.three_candle_patterns import ThreeCandlePatternDetector
from backend.app.services.pattern.two_candle_patterns import TwoCandlePatternDetector


class PatternFactory:
    """
    Registers every candlestick-pattern + SMC detector (FVG is handled
    separately by FVGDetector — different return schema, not a
    DetectedPattern). Mirrors StrategyFactory's shape/spirit.

    The classical chart-shape detectors (Double/Triple Top, Head &
    Shoulders, Triangle, Wedge, Flag/Pennant, Channel/Rectangle, Cup &
    Handle, Diamond/Broadening) were removed by explicit user request in
    favor of a full candlestick-pattern engine (~32 patterns across
    single/two/three-candle families) — see CLAUDE.md.
    """

    DETECTORS = {
        "single_candle": SingleCandlePatternDetector,
        "two_candle": TwoCandlePatternDetector,
        "three_candle": ThreeCandlePatternDetector,
        "smc": SMCDetector,
    }

    @staticmethod
    def get_detector(key: str):
        key = key.lower()
        if key not in PatternFactory.DETECTORS:
            raise ValueError(
                f"Unknown pattern detector: {key}. Available: {list(PatternFactory.DETECTORS.keys())}"
            )
        return PatternFactory.DETECTORS[key]()

    @staticmethod
    def list_detectors() -> list[str]:
        return list(PatternFactory.DETECTORS.keys())

    @staticmethod
    def all_detectors() -> list:
        return [cls() for cls in PatternFactory.DETECTORS.values()]
