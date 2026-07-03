class PatternConfig:

    # Swing point (fractal pivot) detection — bars required on each side
    SWING_LOOKBACK = 5

    # "Roughly equal" price tolerance used across multiple pattern families
    PRICE_EQUALITY_TOLERANCE_PCT = 1.5

    # Double / Triple Top / Bottom
    DT_LOOKBACK_BARS = 150
    DT_MIN_TROUGH_DEPTH_PCT = 2.0
    DT_PEAK_TOLERANCE_PCT = 1.5

    # Head & Shoulders / Inverse
    HS_LOOKBACK_BARS = 180
    HS_SHOULDER_TOLERANCE_PCT = 3.0
    HS_HEAD_MIN_PROMINENCE_PCT = 2.0

    # Triangles (Ascending / Descending / Symmetrical)
    TRIANGLE_LOOKBACK_BARS = 120
    TRIANGLE_MIN_TOUCHES_PER_SIDE = 2
    TRIANGLE_FLAT_SLOPE_TOLERANCE_PCT = 0.05
    TRIANGLE_MIN_CONVERGENCE_PCT = 30.0

    # Wedges (Rising / Falling)
    WEDGE_LOOKBACK_BARS = 120
    WEDGE_MIN_TOUCHES_PER_SIDE = 2
    WEDGE_MIN_CONVERGENCE_PCT = 20.0

    # Flags / Pennants
    FLAGPOLE_LOOKBACK_BARS = 40
    FLAGPOLE_MIN_MOVE_PCT = 5.0
    FLAG_MIN_CONSOLIDATION_BARS = 5
    FLAG_MAX_CONSOLIDATION_BARS = 30
    FLAG_MAX_RETRACE_PCT = 50.0

    # Rectangle / Channel
    CHANNEL_LOOKBACK_BARS = 120
    CHANNEL_MIN_TOUCHES_PER_SIDE = 2

    # Cup & Handle / Rounding Bottom
    CUP_MIN_BARS = 30
    CUP_MAX_BARS = 200
    CUP_DEPTH_MIN_PCT = 8.0
    CUP_DEPTH_MAX_PCT = 50.0
    CUP_RIM_TOLERANCE_PCT = 5.0
    HANDLE_MAX_BARS = 40
    HANDLE_MAX_RETRACE_PCT = 50.0

    # Diamond / Broadening Formation
    BROADENING_LOOKBACK_BARS = 120
    BROADENING_MIN_TOUCHES_PER_SIDE = 2
    DIAMOND_LOOKBACK_BARS = 140

    # Fair Value Gap
    FVG_MIN_GAP_ATR_RATIO = 0.15
    FVG_LOOKBACK_BARS = 300
    FVG_STRONG_ATR_RATIO = 0.6

    # Smart Money Concepts — order blocks, BOS, CHOCH, liquidity
    SMC_LOOKBACK_BARS = 150
    OB_MIN_MOVE_ATR_RATIO = 1.0
    LIQUIDITY_EQUAL_LEVEL_TOLERANCE_PCT = 0.3
    BOS_SWING_LOOKBACK = SWING_LOOKBACK

    # Breakout / invalidation confirmation
    BREAKOUT_CONFIRMATION_ATR_MULT = 0.25

    # Target scaling beyond the pattern's own measured move (fib-style extensions)
    TARGET_2_MEASURED_MOVE_MULTIPLIER = 1.618
    TARGET_3_MEASURED_MOVE_MULTIPLIER = 2.618

    # Algorithmic confidence scoring weights (normalized to 0-100 internally)
    CONF_WEIGHT_GEOMETRY_FIT = 0.40
    CONF_WEIGHT_VOLUME_CONFIRMATION = 0.25
    CONF_WEIGHT_BREAKOUT_STRENGTH = 0.20
    CONF_WEIGHT_PATTERN_SIZE = 0.15

    # Multi-timeframe scan defaults
    PATTERN_SCAN_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    PATTERN_SCAN_MAX_WORKERS = 8
    PATTERN_SCAN_MIN_CONFIDENCE = 40.0
    # AI explanation calls are real network I/O against NVIDIA NIM — capped
    # lower than the pure-CPU detector concurrency to avoid hammering the
    # API when a multi-timeframe scan is itself running scans concurrently.
    PATTERN_AI_MAX_WORKERS = 4


pattern_config = PatternConfig()
