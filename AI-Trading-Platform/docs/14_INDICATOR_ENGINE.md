# AI Trading Platform

# Indicator Engine

---

# Purpose

The Indicator Engine is responsible for calculating all technical indicators used throughout the platform.

It acts as the single source of truth for market analytics.

No strategy should calculate indicators independently.

Instead, every strategy must request indicator values from the Indicator Engine.

This ensures consistency, avoids duplicate calculations, and keeps business logic centralized.

---

# Current Status

Status

✅ Implemented

Current Engine

```
IndicatorService
```

Current Capabilities

- Calculate technical indicators
- Analyze historical market data
- Detect market trend
- Calculate volatility metrics
- Calculate volume metrics

The engine is already integrated with

- Strategy Engine
- Backtesting Engine
- Trading Engine

---

# Architecture

```
Market Service

        │

        ▼

Historical Candles

        │

        ▼

Indicator Engine

        │

        ▼

Indicator Dictionary

        │

        ▼

Strategy Engine
```

The Indicator Engine never generates BUY or SELL signals.

Its only responsibility is to calculate market indicators.

---

# Responsibilities

The Indicator Engine is responsible for

- Reading OHLCV data
- Calculating indicators
- Detecting trend
- Measuring volatility
- Measuring momentum
- Measuring volume
- Returning normalized indicator values

It does not

- Execute trades
- Manage positions
- Generate signals
- Update portfolios

---

# Current Files

```
backend/app/services/

indicator_service.py
```

Future expansion

```
indicator_engine/

indicator_service.py

trend_detector.py

volume_analyzer.py

volatility_analyzer.py

momentum_analyzer.py

indicator_cache.py
```

---

# Input

The engine receives

```
DataFrame

↓

Open

High

Low

Close

Volume

Timestamp
```

The DataFrame is usually provided by

```
MarketService
```

---

# Current Output

The engine returns a dictionary similar to

```python
{
    "price": 59379.96,

    "sma20": 59338.23,

    "ema20": 59365.37,

    "ema50": 59444.32,

    "ema200": 59769.52,

    "rsi14": 49.78,

    "previous_rsi14": 49.18,

    "macd": -25.73,

    "signal": -39.81,

    "histogram": 14.07,

    "bb_upper": 59430.53,

    "bb_middle": 59338.23,

    "bb_lower": 59245.92,

    "atr14": 68.20,

    "vwap": 59336.08,

    "adx14": 19.21,

    "plus_di": 19.90,

    "minus_di": 19.61,

    "volume_sma20": 56.05,

    "relative_volume": 0.65,

    "bollinger_width": 184.61,

    "trend": "BEARISH"
}
```

Every strategy should consume this dictionary.

---

# Current Indicators

## Price

Purpose

Current market price.

Used by

- Entry
- Exit
- Position sizing
- Stop Loss

---

## SMA20

Simple Moving Average.

Used for

- Mean reversion
- Trend confirmation

---

## EMA20

Short-term trend.

---

## EMA50

Medium-term trend.

---

## EMA200

Long-term trend.

This is currently the primary trend indicator.

---

## RSI14

Momentum indicator.

Current use

- Oversold detection
- Overbought detection
- Recovery confirmation

Future

Dynamic RSI thresholds.

---

## Previous RSI

Used to detect RSI crossovers.

Example

```
Previous RSI

29

Current RSI

32

↓

Oversold recovery
```

---

## MACD

Measures momentum.

Current values

- MACD Line
- Signal Line
- Histogram

Strategies primarily use the histogram.

---

## ATR14

Average True Range.

Measures market volatility.

Current uses

- Stop Loss
- Take Profit
- Risk calculations

Future

- Dynamic position sizing
- Market regime detection

---

## Bollinger Bands

Current values

- Upper Band
- Middle Band
- Lower Band

Future

- Breakout detection
- Squeeze detection

---

## Bollinger Width

Measures market compression.

Useful for detecting

- Low volatility
- High volatility
- Breakout preparation

---

## VWAP

Volume Weighted Average Price.

Used to determine whether price is trading above or below average market value.

Future

Institutional confirmation.

---

## ADX

Measures trend strength.

Current interpretation

```
ADX < 20

Weak Trend

ADX 20–25

Moderate Trend

ADX > 25

Strong Trend
```

---

## +DI

Positive Directional Index.

Measures bullish pressure.

---

## -DI

Negative Directional Index.

Measures bearish pressure.

---

## Relative Volume

Formula

```
Current Volume

/

20 Period Average Volume
```

Purpose

Detect unusual trading activity.

Future

Improve breakout detection.

---

## Trend

Current values

```
BULLISH

BEARISH

SIDEWAYS
```

Trend is currently derived using EMA alignment.

Future versions should include

- ADX confirmation
- Market regime
- Higher timeframe validation

---

# Current Calculation Flow

```
OHLCV

↓

EMA

↓

RSI

↓

MACD

↓

ATR

↓

Bollinger Bands

↓

VWAP

↓

ADX

↓

Volume Analysis

↓

Trend Detection

↓

Indicator Dictionary
```

---

# Current Strengths

Implemented

✅ Centralized calculations

✅ Reusable indicators

✅ Trend detection

✅ Volume analysis

✅ Volatility metrics

✅ Momentum metrics

---

# Current Limitations

The engine is intentionally lightweight.

Missing features include

- Supertrend
- Ichimoku Cloud
- Stochastic RSI
- CCI
- OBV
- MFI
- Donchian Channels
- Keltner Channels
- Fibonacci Levels
- Pivot Points

---

# Planned Improvements

## Indicator Caching

Current

Indicators are recalculated every request.

Future

Cache results.

Benefits

- Faster backtesting
- Lower CPU usage
- Better scalability

---

## Multi-Timeframe Indicators

Current

Single timeframe.

Future

Example

```
5m

15m

1h

4h

1d
```

Strategies can use multiple timeframes simultaneously.

---

## Market Regime Detection

Future

Indicator Engine should assist in determining

- Trending
- Sideways
- High Volatility
- Low Volatility

This information will be consumed by the Strategy Engine.

---

## Indicator Normalization

Future

Normalize indicator values.

Example

```
RSI

0–100

↓

0–1

```

This simplifies AI integration.

---

## AI Features

Future AI modules may analyze

- Indicator relationships
- Divergences
- Hidden momentum
- Pattern recognition

The Indicator Engine should provide structured data for these modules.

---

# Testing

Current test

```
tests/test_indicator_service.py
```

This test validates

- Indicator calculations
- Trend detection
- Volume metrics
- Volatility metrics
- Dictionary output

Future tests

```
test_trend_detector.py

test_volume_analysis.py

test_market_regime.py

test_indicator_cache.py
```

---

# Development Rules

The Indicator Engine must

- Remain stateless
- Never execute trades
- Never generate signals
- Never modify portfolio data
- Only calculate and return indicators

All strategies should consume this engine rather than implementing their own calculations.

---

# Long-Term Vision

The Indicator Engine should evolve into a comprehensive market analytics framework capable of calculating dozens of technical indicators across multiple timeframes with high performance and consistent output.

It should remain the foundation of every trading strategy, AI module, and market analysis component within the platform.

By centralizing all indicator calculations, the platform ensures consistency, maintainability, and scalability while making it easy to introduce new indicators without modifying existing strategies.