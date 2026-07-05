"""Pydantic schemas for the SMC analysis engine.

Pure data holders — no business logic (matches the "schemas hold data" rule).
Reuses the generic chart-annotation models from schemas.pattern so the frontend
can render SMC zones/levels/markers with the same primitives it already uses for
patterns.

Field names mirror SMC_System_Documentation.pdf so the port stays auditable.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel

# Reuse the generic annotation primitives (identical rendering needs).
from backend.app.schemas.pattern import ChartAnnotations  # noqa: F401


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class Direction(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class TrendState(str, Enum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class StructureType(str, Enum):
    BOS_UP = "BOS_up"
    BOS_DOWN = "BOS_down"
    CHOCH_UP = "CHoCH_up"
    CHOCH_DOWN = "CHoCH_down"


class SwingLabel(str, Enum):
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"


class ZoneKind(str, Enum):
    POI = "POI"
    ORDER_BLOCK = "order_block"
    DEMAND = "demand"
    SUPPLY = "supply"
    SWING = "swing"
    ATR_FALLBACK = "atr_fallback"


class VerdictLabel(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StrengthLabel(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    REJECTED = "REJECTED"


class PressureLabel(str, Enum):
    BUY = "buy"
    SELL = "sell"
    BALANCED = "balanced"


# --------------------------------------------------------------------------- #
# Detection sub-models (§5)
# --------------------------------------------------------------------------- #
class Swing(BaseModel):
    index: int
    time: str
    price: float
    is_high: bool
    label: Optional[SwingLabel] = None


class StructureEvent(BaseModel):
    index: int
    time: str
    price: float           # the level that broke
    type: StructureType


class OrderBlock(BaseModel):
    index: int
    time: str
    top: float
    bottom: float
    direction: Direction   # bullish OB (demand) / bearish OB (supply)
    mitigated: bool = False
    mitigated_index: Optional[int] = None


class FVG(BaseModel):
    index: int             # bar i (the middle candle of the 3-candle scan)
    time: str
    top: float
    bottom: float
    direction: Direction
    filled: bool = False
    filled_index: Optional[int] = None

    @property
    def midpoint(self) -> float:
        return (self.top + self.bottom) / 2


class LiquidityPool(BaseModel):
    price: float
    direction: Direction   # BULLISH = equal-lows (sell-side below),
    #                        BEARISH = equal-highs (buy-side above)
    swing_indices: list[int] = []


class LiquiditySweep(BaseModel):
    pool_price: float
    direction: Direction   # side that was swept
    sweep_index: int
    reversal_index: int
    recent: bool = False   # reversal within SWEEP_REVERSAL_RECENCY_BARS


class DealingRange(BaseModel):
    range_hi: float
    range_lo: float
    equilibrium: float
    position: float        # (close - lo) / range, 0..1
    zone: str              # "premium" / "discount" / "equilibrium"


class VolumeContext(BaseModel):
    ratio: float           # recent avg / prior avg
    trend_vol: float       # net up-vs-down volume, -1..1
    spike: bool = False


class POI(BaseModel):
    top: float
    bottom: float
    direction: Direction
    has_liquidity: bool = False
    order_block_index: Optional[int] = None
    fvg_index: Optional[int] = None


class Inducement(BaseModel):
    index: int
    time: str
    price: float
    direction: Direction   # direction of the deeper POI it front-runs
    atr_distance: float


class SupplyDemandZone(BaseModel):
    index: int
    time: str
    top: float
    bottom: float
    direction: Direction   # BULLISH = demand, BEARISH = supply
    mitigated: bool = False


class HTFTrend(BaseModel):
    available: bool = False
    trend: TrendState = TrendState.NEUTRAL
    htf_bars: int = 0


# --------------------------------------------------------------------------- #
# Scoring (§6)
# --------------------------------------------------------------------------- #
class ScoreComponent(BaseModel):
    name: str
    raw: float             # -100..+100
    weight: float
    contribution: float    # raw * weight


class ScoreBreakdown(BaseModel):
    components: list[ScoreComponent] = []
    total: float = 0.0


class Verdict(BaseModel):
    label: VerdictLabel
    total: float
    confidence: float
    confidence_label: ConfidenceLabel
    breakdown: ScoreBreakdown


class ConfluenceFactor(BaseModel):
    name: str
    points: int
    hit: bool
    detail: str = ""


class SideConfluence(BaseModel):
    side: Side
    total: int
    fired: bool
    strength: StrengthLabel
    factors: list[ConfluenceFactor] = []
    reject_reasons: list[str] = []


# --------------------------------------------------------------------------- #
# Trade plan (§7)
# --------------------------------------------------------------------------- #
class TradePlan(BaseModel):
    side: Side
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward: float
    atr: float
    source: ZoneKind
    zone_top: Optional[float] = None
    zone_bottom: Optional[float] = None
    strength: StrengthLabel
    strength_score: int
    fired: bool
    note: str = ""
    confluence: Optional[SideConfluence] = None


# --------------------------------------------------------------------------- #
# Order flow (§8)
# --------------------------------------------------------------------------- #
class OrderFlow(BaseModel):
    imbalance: float       # (bid - ask) / (bid + ask), -1..1
    cvd_ratio: float       # delta / total, -1..1
    pressure: PressureLabel
    bid_notional: float = 0.0
    ask_notional: float = 0.0
    bid_walls: list[dict] = []
    ask_walls: list[dict] = []


# --------------------------------------------------------------------------- #
# Candle DTO + top-level result (§5.1)
# --------------------------------------------------------------------------- #
class SmcCandle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class AnalysisResult(BaseModel):
    symbol: str
    interval: str
    frozen_at: str
    cutoff_price: float
    atr: float

    candles: list[SmcCandle] = []

    # Detections
    swings: list[Swing] = []
    structure: list[StructureEvent] = []
    trend: TrendState = TrendState.NEUTRAL
    order_blocks: list[OrderBlock] = []
    fvgs: list[FVG] = []
    liquidity_pools: list[LiquidityPool] = []
    sweeps: list[LiquiditySweep] = []
    dealing_range: Optional[DealingRange] = None
    volume: Optional[VolumeContext] = None
    pois: list[POI] = []
    inducements: list[Inducement] = []
    supply_demand: list[SupplyDemandZone] = []
    htf: Optional[HTFTrend] = None

    # Scoring + plans
    verdict: Optional[Verdict] = None
    long_plan: Optional[TradePlan] = None
    short_plan: Optional[TradePlan] = None
    primary: str = "neutral"   # "long" / "short" / "neutral"

    order_flow: Optional[OrderFlow] = None
    reasons: list[str] = []
    annotations: Optional[ChartAnnotations] = None


class AnalysisRequest(BaseModel):
    symbol: str
    interval: str = "1h"
    limit: int = 500
