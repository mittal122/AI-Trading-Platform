class PatternConfig:

    # Swing point (fractal pivot) detection — bars required on each side
    SWING_LOOKBACK = 5

    # "Roughly equal" price tolerance used across multiple pattern families
    PRICE_EQUALITY_TOLERANCE_PCT = 1.5

    # Default "is this slope flat" tolerance for classify_slope() in
    # trendline.py — a shared primitive (used by the Trend Line analysis
    # tool and the candlestick detectors' local_trend() helper), not tied to
    # any one specific pattern family.
    TRENDLINE_FLAT_SLOPE_TOLERANCE_PCT = 0.05

    # ------------------------------------------------------------------
    # Candlestick patterns (single/two/three-candle formations) — replaced
    # the classical chart-shape detectors (Double/Triple Top, H&S, Triangle,
    # Wedge, Flag/Pennant, Channel/Rectangle, Cup & Handle, Diamond/
    # Broadening) per explicit user request. SMC and FVG are unaffected —
    # different feature, not a "chart shape" detector.
    # ------------------------------------------------------------------

    # How far back to scan for candlestick pattern instances — the full
    # per-request ceiling (1000, matching Binance/backend's own max), so
    # every loaded candle on the chart gets checked, not just a trailing
    # slice. Historical patterns are resolved against the candles that
    # followed them (see CANDLESTICK_CONFIRMATION_WINDOW_BARS), so an old
    # detection is still a truthful "this happened here and resolved
    # this way," not a stale live signal.
    CANDLESTICK_LOOKBACK_BARS = 1000

    # A pattern's signal candle must be a "real" candle relative to recent
    # volatility — tiny chop candles trivially satisfy shape ratios (a 2-tick
    # candle is a "perfect doji") and were flooding the results with noise.
    CANDLESTICK_MIN_RANGE_ATR_RATIO = 0.6
    # Neutral/indecision patterns (Standard Doji, Spinning Top, Inside Bar)
    # fire even more often, and carry less information — they need to be
    # genuinely prominent to be worth reporting.
    CANDLESTICK_NEUTRAL_MIN_RANGE_ATR_RATIO = 1.2

    # How many candles AFTER a pattern completes it has to trigger (price
    # clears the breakout level) or fail (price hits invalidation). A pattern
    # that does neither within this window is expired — reported as BROKEN,
    # since its setup is no longer tradeable.
    CANDLESTICK_CONFIRMATION_WINDOW_BARS = 12

    # Body/wick ratio thresholds, straight from standard (Nison-style)
    # candlestick definitions.
    CANDLESTICK_WICK_TOLERANCE_PCT = 5.0        # Marubozu: max wick as % of total range
    CANDLESTICK_DOJI_BODY_MAX_PCT = 5.0         # Doji family: max body as % of total range
    CANDLESTICK_LONG_WICK_MIN_PCT = 90.0        # Dragonfly/Gravestone: min opposite wick as % of range
    CANDLESTICK_WICK_TO_BODY_RATIO = 2.0        # Hammer/Hanging Man/Inverted Hammer/Shooting Star/Spinning Top
    # Hammer family only: the SHORT wick must stay small relative to the
    # DOMINANT wick (not an ad-hoc mix of body/dominant-wick fractions) —
    # standard screening convention is "opposite shadow under ~30-38% of the
    # main shadow." Single clean ratio, applied uniformly to all 4 shapes.
    CANDLESTICK_OPPOSITE_WICK_MAX_RATIO = 0.3
    CANDLESTICK_MIDPOINT_THRESHOLD = 0.5        # Piercing Line / Dark Cloud Cover
    # Tweezer "same high/low" tolerance, in ATR units — NOT % of price. A
    # %-of-price tolerance (originally 0.15%) was nearly a full ATR on
    # intraday BTC, so almost any two adjacent candles counted as a Tweezer
    # (231 of them in one 1000-candle scan). Two wicks are only "equal" if
    # they differ by a small fraction of normal candle movement.
    CANDLESTICK_TWEEZER_EQUAL_ATR_RATIO = 0.2
    CANDLESTICK_GAP_MIN_PCT = 0.05              # Kickers: min % gap between C1 and C2
    CANDLESTICK_VOLUME_MULTIPLIER = 1.0         # Kickers/Engulfing: C2 volume > C1 volume
    CANDLESTICK_STAR_BODY_MAX_PCT = 30.0        # Morning/Evening Star: max middle-candle body vs C1/C3
    CANDLESTICK_SOLDIER_CROW_MIN_ATR_MULT = 0.5  # Three White Soldiers/Black Crows: min body size vs ATR

    # Trend-context filter (many patterns require "trend is up/down" first) —
    # reuses the same least-squares trendline primitive as the Trend Line
    # analysis tool, just over a shorter local window.
    CANDLESTICK_TREND_LOOKBACK_BARS = 20
    CANDLESTICK_TREND_FLAT_TOLERANCE_PCT = 0.03

    # Default risk/reward multiple for patterns whose target is stated as a
    # ratio ("1:2 R/R") rather than a specific level.
    CANDLESTICK_DEFAULT_RR = 2.0

    # ------------------------------------------------------------------
    # Classical chart-shape patterns — restored 2026-07-05 (user asked for
    # Double Top/Bottom, H&S, Wedges, Rectangles, Pennants, Triangles drawn
    # on the chart; the detectors deleted on 2026-07-04 were brought back
    # from git history and upgraded to the forward-resolution status system).
    # ------------------------------------------------------------------

    # Double / Triple Top / Bottom
    DT_LOOKBACK_BARS = 400
    DT_MIN_TROUGH_DEPTH_PCT = 2.0
    DT_PEAK_TOLERANCE_PCT = 1.5

    # Head & Shoulders / Inverse
    HS_LOOKBACK_BARS = 400
    HS_SHOULDER_TOLERANCE_PCT = 3.0
    HS_HEAD_MIN_PROMINENCE_PCT = 2.0

    # Triangles (Ascending / Descending / Symmetrical)
    TRIANGLE_LOOKBACK_BARS = 300
    TRIANGLE_MIN_TOUCHES_PER_SIDE = 2
    TRIANGLE_MIN_CONVERGENCE_PCT = 30.0

    # Wedges (Rising / Falling)
    WEDGE_LOOKBACK_BARS = 300
    WEDGE_MIN_TOUCHES_PER_SIDE = 2
    WEDGE_MIN_CONVERGENCE_PCT = 20.0

    # Flags / Pennants — inherently short-lived by definition; a "flag"
    # spanning hundreds of candles isn't a flag anymore
    FLAGPOLE_LOOKBACK_BARS = 40
    FLAGPOLE_MIN_MOVE_PCT = 5.0
    FLAG_MIN_CONSOLIDATION_BARS = 5
    FLAG_MAX_CONSOLIDATION_BARS = 30
    FLAG_MAX_RETRACE_PCT = 50.0

    # Rectangle / Channel
    CHANNEL_LOOKBACK_BARS = 300
    CHANNEL_MIN_TOUCHES_PER_SIDE = 2

    # Forward-resolution window for HISTORICALLY-anchored chart shapes
    # (Double/Triple Top, H&S) — larger formations take longer to play out
    # than the candlestick default of 12 bars. Live-edge shapes (Triangle,
    # Wedge, Rectangle, Flag/Pennant) still use current-price status: their
    # formation always ends at the latest candle, so "is price breaking out
    # NOW" is exactly the right question for them.
    CHART_PATTERN_CONFIRMATION_WINDOW_BARS = 40

    # Fair Value Gap — scaled to the full per-request ceiling (1000, matching
    # Binance/backend's own per-call max) so "all historical + unfilled FVGs"
    # genuinely covers everything fetched, not just a trailing slice of it
    FVG_MIN_GAP_ATR_RATIO = 0.15
    FVG_LOOKBACK_BARS = 1000
    FVG_STRONG_ATR_RATIO = 0.6

    # Smart Money Concepts — order blocks, BOS, CHOCH, liquidity. Also scaled
    # up — structure/liquidity levels from well back in the loaded dataset
    # are still meaningful reference points, unlike short-lived patterns.
    SMC_LOOKBACK_BARS = 500
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
    # Raised from 40 (2026-07-04) as part of the noise-reduction pass — with
    # the full-chart scan finding many more candidates, weak matches below
    # this bar aren't worth returning at all.
    PATTERN_SCAN_MIN_CONFIDENCE = 55.0

    # The cross-timeframe dashboard answers "what's actionable NOW" — only
    # patterns that completed within this many bars (of their own interval)
    # appear there. The full-history scan on the chart page is unaffected.
    PATTERN_DASHBOARD_RECENT_BARS = 20
    # AI explanation calls are real network I/O against NVIDIA NIM — capped
    # lower than the pure-CPU detector concurrency to avoid hammering the
    # API when a multi-timeframe scan is itself running scans concurrently.
    PATTERN_AI_MAX_WORKERS = 4


pattern_config = PatternConfig()
