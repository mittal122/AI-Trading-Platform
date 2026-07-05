"""Centralized configuration for the SMC (Smart Money Concepts) analysis engine.

Every numeric threshold used anywhere in backend/app/services/smc/ lives here —
no magic numbers in the engine files (matches the project's "no hardcoded
thresholds" rule). Values are taken directly from SMC_System_Documentation.pdf
(section references in comments). A single module-level singleton `smc_config`
is imported everywhere, e.g.:

    from backend.app.core.smc_config import smc_config
"""


class SmcConfig:
    # ----- Analysis window (§5, §9) -----
    DEFAULT_CANDLES = 500          # typical analysis series length
    MIN_CANDLES = 60              # below this the analysis is invalid (400)
    WARMUP_BARS = 60             # simulation / structure warm-up

    # ----- Swing detection (§5.2) -----
    SWING_LENGTH = 5             # strictly greater/less than N bars each side;
    #                             ties disqualify -> 5-bar confirmation lag

    # ----- Order blocks (§5.4) -----
    OB_LOOKBACK_BARS = 15          # scan back this many bars for the last
    #                             opposite candle before a break
    OB_MITIGATION_CHECK_FROM = 3    # start checking mitigation this many bars
    #                             after the OB forms (decisive close only)

    # ----- Fair value gaps (§5.5) -----
    FVG_FILL_CHECK_FROM = 2         # a gap can begin filling this many bars after

    # ----- Liquidity pools & sweeps (§5.6-5.7) -----
    LIQUIDITY_WINDOW_BARS = 100     # window for equal-high/low clustering
    LIQUIDITY_TOLERANCE_PCT = 0.3   # % of the window's total range (floor below)
    LIQUIDITY_TOLERANCE_FLOOR = 1e-7
    LIQUIDITY_RECENT_SWINGS = 20    # keep last N swings as stop reference points
    SWEEP_CONFIRM_BARS = 2         # close back within 1-2 bars confirms a sweep
    SWEEP_REVERSAL_RECENCY_BARS = 10  # only sweeps reversing within N bars score

    # ----- Dealing range (§5.1 step 6) -----
    DEALING_RANGE_BARS = 60
    EQUILIBRIUM_LOW = 0.45         # 45-55% band = "equilibrium" (no edge)
    EQUILIBRIUM_HIGH = 0.55

    # ----- Volume context (§5 step 7) -----
    VOLUME_RECENT_BARS = 20         # recent average window
    VOLUME_PRIOR_BARS = 40         # prior average window
    VOLUME_SPIKE_RATIO = 1.5        # recent avg > 1.5x prior -> volume boost
    VOLUME_BOOST = 1.3             # multiplier applied to the volume score

    # ----- Points of interest / inducements / zones (§5.8-5.10) -----
    POI_OVERLAP_ATR = 0.6          # OB & FVG form a POI if gap <= 0.6xATR
    POI_LIQUIDITY_ATR = 0.5        # hasLiquidity if a pool rests <= 0.5xATR
    INDUCEMENT_ATR = 1.5          # HL/LH is an inducement if a deeper POI
    #                             sits within 1.5xATR
    DEMAND_BASE_MAX_CANDLES = 3     # tight base of <=3 candles
    DEMAND_BASE_RANGE_ATR = 0.6     # base combined range <= 0.6xATR
    DEMAND_IMPULSE_ATR = 2.5        # impulse net move >= 2.5xATR
    DEMAND_IMPULSE_CANDLES = 5      # over the next 5 candles
    DEMAND_DIRECTIONAL_PCT = 0.60   # >=60% of impulse candles close in-direction

    # ----- ATR (§5.11) -----
    ATR_PERIOD = 14
    ATR_FALLBACK_PRICE_PCT = 0.02   # fallback = max(2% of price, floor)
    ATR_FALLBACK_FLOOR = 0.0001

    # ----- Higher-timeframe trend (§5.12) -----
    HTF_BARS_PER_CANDLE = {         # LTF interval -> bars aggregated per HTF bar
        "1m": 15, "5m": 12, "15m": 16, "1h": 24, "4h": 42, "1d": 7,
    }                             # weekly/monthly have no HTF -> skipped
    HTF_MIN_BARS = 15             # need >=15 HTF bars to run structure on them

    # ===== §6.1 Market-bias component scoring =====
    # Structure: base by trend, then last 3 structure events.
    STRUCTURE_TREND_BASE = 60      # +60 uptrend / -60 downtrend / 0 neutral
    STRUCTURE_CHOCH_POINTS = 15     # each CHoCH in last 3 events, signed
    STRUCTURE_BOS_POINTS = 10      # each BOS in last 3 events, signed
    # Order blocks: last 15 unmitigated, proximity-weighted.
    OB_SCORE_MAX_DIST = 0.25        # skip if normalized dist > 0.25 of range
    OB_SCORE_WEIGHT = 80          # weight = (0.25 - dist) * 80, signed
    OB_SCORE_LOOKBACK = 15
    # FVG: last 20 open, distance to midpoint.
    FVG_SCORE_MAX_DIST = 0.20
    FVG_SCORE_WEIGHT = 60
    FVG_SCORE_LOOKBACK = 20
    # Liquidity magnets.
    LIQUIDITY_SCORE_POINTS = 25     # +25 per EQH above / -25 per EQL below
    LIQUIDITY_SCORE_BAND_PCT = 15    # pools within 15% of price count
    # Dealing-range zone score by position in the 60-bar range.
    ZONE_SCORE_DEEP_DISCOUNT = 50    # pos < 30% -> +50
    ZONE_SCORE_DISCOUNT = 20        # pos < 50% -> +20
    ZONE_SCORE_PREMIUM = -20        # pos < 70% -> -20
    ZONE_SCORE_DEEP_PREMIUM = -50    # else -50
    ZONE_POS_DEEP_DISCOUNT = 0.30
    ZONE_POS_DISCOUNT = 0.50
    ZONE_POS_PREMIUM = 0.70
    # Volume.
    VOLUME_SCORE_WEIGHT = 60        # trendVol * 60, then optional x1.3 boost

    # ===== §6.2 Verdict =====
    WEIGHT_STRUCTURE = 0.30
    WEIGHT_ORDER_BLOCKS = 0.20
    WEIGHT_FVG = 0.10
    WEIGHT_LIQUIDITY = 0.10
    WEIGHT_ZONE = 0.15
    WEIGHT_VOLUME = 0.15
    VERDICT_BULLISH_ABOVE = 20      # total > +20 -> BULLISH
    VERDICT_BEARISH_BELOW = -20     # total < -20 -> BEARISH
    CONFIDENCE_MULT = 1.5          # confidence = min(100, |total| * 1.5)
    CONFIDENCE_HIGH = 65          # > 65 "high"
    CONFIDENCE_MEDIUM = 40         # > 40 "medium", else "low"

    # ===== §6.3 Per-side confluence checklist (out of 110) =====
    CONFLUENCE_MAX = 110
    CONFLUENCE_FIRE_THRESHOLD = 70   # side fires iff total >= 70 AND no veto
    CONTAIN_TOL_ATR = 0.45        # zone-containment tolerance around the entry
    POI_PRESENT_ATR = 1.0          # a same-dir POI within 1xATR of entry
    PTS_OB_IN_ZONE = 25
    PTS_FVG_IN_ZONE = 20
    PTS_HTF_ALIGNED = 15
    PTS_DEALING_RANGE = 15
    PTS_LIQ_SWEEP = 10
    PTS_POI_PRESENT = 10
    PTS_ORDER_FLOW = 10          # live only
    PTS_CANDLE_PATTERN = 5

    # ===== §6.3 Reject (veto) rules — any one vetoes the side =====
    VETO_ZONE_VACUUM_ATR = 2.0      # no same-dir POI/OB/FVG/zone within 2xATR
    VETO_VOLATILITY_LOW_PCT = 0.2    # ATR% of price below this = dead market
    VETO_VOLATILITY_HIGH_PCT = 4.0   # above this = chaos
    VETO_OF_IMBALANCE = -0.45       # long vetoed if imbalance < -0.45 ...
    VETO_OF_CVD = -0.25          # ... AND cvdRatio < -0.25 (mirror for shorts)

    # ===== §7 Trade plan =====
    PLAN_MAX_DIST_ATR = 2.0         # maxDist = min(2xATR, 3% of price)
    PLAN_MAX_DIST_PRICE_PCT = 0.03
    PLAN_MIN_RISK_ATR = 1.0         # if |entry-SL| < 1xATR, push SL to 1xATR
    PLAN_TP1_R = 2.0             # TP1 = entry +/- 2R
    PLAN_TP2_R = 3.5             # TP2 = entry +/- 3.5R
    PLAN_STOP_SCAN_BELOW_ATR = 2.5   # scan swings/EQL from 2.5xATR below zone ...
    PLAN_STOP_SCAN_ABOVE_ATR = 0.3   # ... to 0.3xATR above the zone bottom
    PLAN_STOP_BUFFER_ATR = 0.8      # then subtract a 0.8xATR buffer

    # ===== §8 Order flow =====
    OF_DEPTH_LIMIT = 100          # order-book levels fetched
    OF_BAND_PRICE_PCT = 0.01        # band = max(1% of price, 2xATR)
    OF_BAND_ATR = 2.0
    OF_WALL_MULT = 4.0           # a wall is >= 4x the mean side volume
    OF_WALL_TOP_N = 3
    OF_PRESSURE_THRESHOLD = 0.12    # imbalance > +0.12 buy / < -0.12 sell
    OF_AGG_TRADES_LIMIT = 500


smc_config = SmcConfig()
