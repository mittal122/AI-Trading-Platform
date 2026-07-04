class AnalysisConfig:

    # Support & Resistance — scaled to the full per-request ceiling (1000)
    # so historical levels well back in the loaded dataset still surface,
    # not just a trailing 200-bar slice regardless of how much was fetched.
    SR_LOOKBACK_BARS = 1000
    SR_LEVEL_TOLERANCE_PCT = 0.5          # cluster tolerance for "same level"
    SR_MIN_TOUCHES = 2
    SR_PSYCHOLOGICAL_ROUND_DIGITS = 2      # round-number levels: nearest 10^N below price magnitude

    # Moving Averages
    MA_PERIODS = [20, 50, 100, 200]
    MA_GOLDEN_DEATH_FAST = 50
    MA_GOLDEN_DEATH_SLOW = 200

    # VWAP — anchored VWAP's swing-anchor search benefits from more history
    # too (finds a more significant anchor instead of whatever's in a small
    # trailing window)
    VWAP_STDDEV_MULTIPLIER_1 = 1.0
    VWAP_STDDEV_MULTIPLIER_2 = 2.0
    VWAP_LOOKBACK_BARS = 1000

    # Pivot Points — based on the prior full daily period's H/L/C regardless
    # of the chart's own interval (the professional convention: daily pivots
    # are shown on any intraday timeframe, not recomputed per-bar).
    PIVOT_ANCHOR_INTERVAL = "1d"

    # ATR tool
    ATR_PERIOD = 14
    ATR_SL_MULTIPLIER = 1.5
    ATR_TP_MULTIPLIER = 3.0
    ATR_LOW_VOL_PCT = 1.0     # ATR as % of price below this = LOW volatility
    ATR_HIGH_VOL_PCT = 3.0    # ATR as % of price above this = HIGH volatility

    # Trend Line tool
    TREND_LOOKBACK_BARS = 300
    TREND_MIN_SWINGS_FOR_CHANNEL = 2  # min swing highs AND lows needed to draw a channel

    # Scan defaults
    ANALYSIS_SCAN_MAX_WORKERS = 8


analysis_config = AnalysisConfig()
