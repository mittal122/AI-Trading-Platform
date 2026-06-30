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


strategy_config = StrategyConfig()
