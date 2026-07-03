from backend.app.services.pattern.channel_rectangle_detector import ChannelRectangleDetector
from backend.app.services.pattern.cup_handle_detector import CupHandleDetector
from backend.app.services.pattern.diamond_broadening_detector import DiamondBroadeningDetector
from backend.app.services.pattern.double_triple_patterns import DoubleTriplePatternDetector
from backend.app.services.pattern.flag_pennant_detector import FlagPennantDetector
from backend.app.services.pattern.head_shoulders_detector import HeadShouldersDetector
from backend.app.services.pattern.smc_detector import SMCDetector
from backend.app.services.pattern.triangle_detector import TriangleDetector
from backend.app.services.pattern.wedge_detector import WedgeDetector


class PatternFactory:
    """
    Registers every classical-pattern + SMC detector (FVG is handled
    separately by FVGDetector — different return schema, not a
    DetectedPattern). Mirrors StrategyFactory's shape/spirit.
    """

    DETECTORS = {
        "double_triple": DoubleTriplePatternDetector,
        "head_shoulders": HeadShouldersDetector,
        "triangle": TriangleDetector,
        "wedge": WedgeDetector,
        "flag_pennant": FlagPennantDetector,
        "channel_rectangle": ChannelRectangleDetector,
        "cup_handle": CupHandleDetector,
        "diamond_broadening": DiamondBroadeningDetector,
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
