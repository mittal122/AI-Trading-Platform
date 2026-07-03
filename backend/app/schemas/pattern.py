from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PatternDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class PatternStatus(str, Enum):
    DEVELOPING = "DEVELOPING"
    CONFIRMED = "CONFIRMED"
    BROKEN = "BROKEN"


class PatternRecommendation(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    AVOID = "AVOID"


class ChartPoint(BaseModel):
    time: str
    price: float


class TrendlineAnnotation(BaseModel):
    label: str
    points: list[ChartPoint]


class ZoneAnnotation(BaseModel):
    label: str
    start_time: str
    end_time: str
    top: float
    bottom: float
    bias: Optional[PatternDirection] = None


class LevelAnnotation(BaseModel):
    label: str
    price: float
    # Optional strength signal (e.g. touch count for Support & Resistance) —
    # frontend uses this to shade a level light-to-dark by conviction.
    strength: Optional[float] = None


class LabelAnnotation(BaseModel):
    text: str
    time: str
    price: float


class ChartAnnotations(BaseModel):
    trendlines: list[TrendlineAnnotation] = []
    zones: list[ZoneAnnotation] = []
    levels: list[LevelAnnotation] = []
    labels: list[LabelAnnotation] = []


class AIPatternExplanation(BaseModel):
    why_detected: str = ""
    why_valid: str = ""
    market_psychology: str = ""
    buyer_seller_behavior: str = ""
    strength: str = ""
    reliability_score: Optional[float] = None
    alternative_scenario: str = ""
    recommendation: Optional[PatternRecommendation] = None
    recommendation_reason: str = ""
    # Set (with the rest left blank) if the AI call failed or NVIDIA_API_KEY
    # isn't configured — the algorithmic pattern data is still returned either way.
    error: Optional[str] = None


class DetectedPattern(BaseModel):
    id: str
    pattern_type: str
    pattern_name: str
    symbol: str
    interval: str
    direction: PatternDirection
    confidence: float
    status: PatternStatus
    formation_start: str
    formation_end: str
    current_price: float

    breakout_level: Optional[float] = None
    invalidation_level: Optional[float] = None
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    target_3: Optional[float] = None
    risk_reward: Optional[float] = None

    probability_of_success: Optional[float] = None
    historical_success_rate: Optional[float] = None
    expected_time_to_target: Optional[str] = None
    pullback_zone_low: Optional[float] = None
    pullback_zone_high: Optional[float] = None

    annotations: ChartAnnotations
    ai: Optional[AIPatternExplanation] = None
    last_updated: str


class FVGType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class FairValueGap(BaseModel):
    id: str
    symbol: str
    interval: str
    type: FVGType
    top: float
    bottom: float
    formed_at: str
    filled: bool
    filled_at: Optional[str] = None
    strength: float
    last_updated: str


class PatternScanResponse(BaseModel):
    symbol: str
    interval: str
    patterns: list[DetectedPattern]
    fvgs: list[FairValueGap]
    scanned_at: str
    error: Optional[str] = None


class PatternDashboardRow(BaseModel):
    symbol: str
    interval: str
    pattern_name: str
    pattern_type: str
    confidence: float
    direction: PatternDirection
    current_price: float
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    risk_reward: Optional[float] = None
    status: PatternStatus
    last_updated: str


class PatternDashboardResponse(BaseModel):
    rows: list[PatternDashboardRow]
    scanned_at: str
