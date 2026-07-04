from backend.app.services.pattern.channel_rectangle_detector import ChannelRectangleDetector
from backend.app.services.pattern.cup_handle_detector import CupHandleDetector
from backend.app.services.pattern.double_triple_patterns import DoubleTriplePatternDetector
from backend.app.services.pattern.flag_pennant_detector import FlagPennantDetector
from backend.app.services.pattern.head_shoulders_detector import HeadShouldersDetector
from backend.app.services.pattern.single_candle_patterns import SingleCandlePatternDetector
from backend.app.services.pattern.smc_detector import SMCDetector
from backend.app.services.pattern.staircase_detector import StaircaseDetector
from backend.app.services.pattern.three_candle_patterns import ThreeCandlePatternDetector
from backend.app.services.pattern.triangle_detector import TriangleDetector
from backend.app.services.pattern.two_candle_patterns import TwoCandlePatternDetector
from backend.app.services.pattern.wedge_detector import WedgeDetector


class PatternFactory:
    """
    Registers every pattern detector + SMC (FVG is handled separately by
    FVGDetector — different return schema, not a DetectedPattern). Mirrors
    StrategyFactory's shape/spirit.

    Two families coexist:
    - Candlestick formations (single/two/three-candle, ~32 patterns) —
      short-term signals, fully scanned across the loaded history.
    - Classical chart shapes (Double/Triple Top, H&S, Triangle, Wedge,
      Flag/Pennant, Channel/Rectangle) — restored 2026-07-05 from git
      history at user request; drawn on the chart via their trendline
      annotations (necklines, converging boundary lines). Cup & Handle and
      Diamond/Broadening remain deleted — not requested back.
    """

    # Chart shapes listed FIRST — the scanner preserves this ordering in
    # its response so the reference chart patterns (staircases, triangles,
    # wedges, double tops, H&S, cups…) are scanned/reported ahead of the
    # candlestick formations, per explicit user request.
    DETECTORS = {
        "staircase": StaircaseDetector,
        "double_triple": DoubleTriplePatternDetector,
        "head_shoulders": HeadShouldersDetector,
        "triangle": TriangleDetector,
        "wedge": WedgeDetector,
        "flag_pennant": FlagPennantDetector,
        "channel_rectangle": ChannelRectangleDetector,
        "cup_handle": CupHandleDetector,
        "single_candle": SingleCandlePatternDetector,
        "two_candle": TwoCandlePatternDetector,
        "three_candle": ThreeCandlePatternDetector,
        "smc": SMCDetector,
    }

    # Detector key → pattern family, stamped onto every DetectedPattern by
    # the scanner (drives list grouping + per-family display filtering).
    CATEGORIES = {
        "staircase": "chart", "double_triple": "chart", "head_shoulders": "chart",
        "triangle": "chart", "wedge": "chart", "flag_pennant": "chart",
        "channel_rectangle": "chart", "cup_handle": "chart",
        "single_candle": "candlestick", "two_candle": "candlestick",
        "three_candle": "candlestick",
        "smc": "smc",
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
