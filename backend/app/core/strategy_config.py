class StrategyConfig:

    # RSI thresholds
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    # ADX thresholds
    ADX_THRESHOLD = 25
    ADX_STRONG_THRESHOLD = 40

    # ATR multipliers (RSI strategy defaults)
    ATR_STOP_MULTIPLIER = 1.5
    ATR_TP_MULTIPLIER = 3.0

    # Minimum confidence required to act on a signal
    CONFIDENCE_THRESHOLD = 55.0

    # Volume threshold for relative volume confirmation
    VOLUME_THRESHOLD = 1.2

    # Market Regime detection ADX thresholds
    REGIME_STRONG_ADX = 40
    REGIME_TREND_ADX = 20

    # Volatility detection — ATR as % of price
    REGIME_HIGH_ATR_PCT = 3.0
    REGIME_LOW_ATR_PCT = 1.0

    # Volatility detection — Bollinger Width as % of price
    REGIME_HIGH_BB_PCT = 6.0
    REGIME_LOW_BB_PCT = 2.0

    # Entry filter — minimum confirmations needed
    MIN_BUY_CONFIRMATIONS = 3
    MIN_SELL_CONFIRMATIONS = 3

    # Exit — maximum candles to hold a trade before time-based exit
    TIME_EXIT_CANDLES = 20

    # Trade quality thresholds for RR scoring
    QUALITY_MIN_RR = 1.5
    QUALITY_GOOD_RR = 2.0
    QUALITY_GREAT_RR = 3.0

    # Supertrend parameters
    SUPERTREND_PERIOD = 7
    SUPERTREND_MULTIPLIER = 3.0

    # EMA strategy crossover windows
    EMA_FAST = 20
    EMA_SLOW = 50

    # Breakout strategy Bollinger Band threshold
    BREAKOUT_BB_BUFFER = 0.001  # 0.1% inside band to confirm breakout

    # Kelly Criterion position sizing
    KELLY_MAX_FRACTION = 0.25       # cap kelly fraction at 25% of equity
    KELLY_DEFAULT_WIN_RATE = 0.55   # assumed win rate if no history available
    KELLY_DEFAULT_RR = 2.0          # assumed RR if not provided

    # Drawdown protection
    DRAWDOWN_HALT_PCT = 0.10        # halt new trades at 10% drawdown
    DRAWDOWN_CLOSE_ALL_PCT = 0.20   # close all positions at 20% drawdown

    # Daily loss limit
    DAILY_LOSS_LIMIT_PCT = 0.02     # halt trading if daily loss > 2% of equity

    # Risk-adjusted position sizing cap
    MAX_POSITION_EQUITY_PCT = 0.05  # single position max 5% of equity

    # CTA Trend (Systematic Trend Following) — 3 EMA-crossover sub-signals
    CTA_FAST_EMA_1 = 10
    CTA_SLOW_EMA_1 = 50
    CTA_FAST_EMA_2 = 20
    CTA_SLOW_EMA_2 = 100
    CTA_FAST_EMA_3 = 50
    CTA_SLOW_EMA_3 = 200
    # Time-series momentum sub-signals (lookback in candles)
    CTA_MOM_LOOKBACK_1 = 90
    CTA_MOM_LOOKBACK_2 = 180
    # Composite signal must exceed this to take a position (0 = any lean)
    CTA_ENTRY_THRESHOLD = 0.0
    # Volatility targeting
    CTA_VOL_LOOKBACK = 90
    CTA_TARGET_VOL_PCT = 0.15
    CTA_MAX_LEVERAGE = 2.0
    CTA_PERIODS_PER_YEAR = 8760  # annualization factor assuming hourly candles
    # Stop/target — ATR(20)-scaled
    CTA_ATR_PERIOD = 20
    CTA_SL_ATR_MULTIPLIER = 2.5
    CTA_TP_ATR_MULTIPLIER = 4.0

    # Turtle Trading System — dual breakout system (Richard Dennis-style)
    TURTLE_N_PERIOD = 20             # ATR window — the Turtle "volatility unit" N
    TURTLE_SYS1_ENTRY_PERIOD = 20
    TURTLE_SYS1_EXIT_PERIOD = 10
    TURTLE_SYS2_ENTRY_PERIOD = 55
    TURTLE_SYS2_EXIT_PERIOD = 20
    TURTLE_ACTIVE_SYSTEM = 1          # 1 = filtered 20-bar system, 2 = unfiltered 55-bar system
    TURTLE_RISK_PERCENT = 1.0         # % of equity risked per unit (informational — sizing is PositionEngine's job)
    TURTLE_SL_N_MULTIPLIER = 2.0
    TURTLE_TP_N_MULTIPLIER = 4.0
    TURTLE_BACKWARD_SCAN_BARS = 150   # how far back System 1's last-breakout filter searches

    # Engulfing Scalp — EMA200 trend filter + RSI + bullish engulfing candle
    ENGULF_EMA_PERIOD = 200
    ENGULF_RSI_PERIOD = 14
    ENGULF_RSI_MIDLINE = 50
    ENGULF_MIN_BODY_RATIO = 1.0       # engulfing candle body must be >= this x the prior candle's body
    ENGULF_SL_RANGE_MULTIPLIER = 2.0  # stop = entry candle range x this, below entry
    ENGULF_RR_RATIO = 2.0
    ENGULF_DIVERGENCE_LOOKBACK = 20
    ENGULF_DIVERGENCE_BONUS = 10.0


strategy_config = StrategyConfig()
