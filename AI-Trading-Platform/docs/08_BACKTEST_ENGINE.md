# AI Trading Platform

# Backtesting Engine

---

# Purpose

The Backtesting Engine is responsible for evaluating trading strategies using historical market data.

Instead of placing real orders, it simulates the complete trading process candle by candle.

The objective is to determine whether a strategy would have been profitable before risking real money.

The backtesting engine is one of the most important components of the platform because every strategy must be validated here before it can be used in paper trading or live trading.

---

# Current Status

Status

✅ Implemented

Current Version

Simple Historical Backtesting Engine

The engine is fully integrated with the rest of the architecture.

It executes trades using the exact same Trading Engine used elsewhere in the project.

This ensures that backtesting behavior closely matches future paper trading and live trading.

---

# Architecture

Current execution flow

```
Historical Data

        │

        ▼

Market Service

        │

        ▼

Backtest Engine

        │

        ▼

Trading Engine

        │

        ▼

Strategy

        │

        ▼

Signal Score

        │

        ▼

Trade Decision

        │

        ▼

Execution Engine

        │

        ▼

Portfolio Engine

        │

        ▼

Trade Recorder

        │

        ▼

Performance Report
```

Every historical candle passes through the same workflow.

No shortcuts are taken.

---

# Responsibilities

The Backtesting Engine is responsible for

- Loading historical candles
- Feeding candles one by one
- Calling the Trading Engine
- Updating portfolio value
- Recording trades
- Building the equity curve
- Calculating statistics
- Returning a complete performance report

---

# Current Workflow

Step 1

Download historical data

```
MarketService

↓

DataFrame
```

---

Step 2

Replay candles sequentially

Instead of exposing future candles,

only candles up to the current index are visible.

Example

```
Candle 1

↓

Candle 2

↓

Candle 3

↓

...

↓

Current Candle
```

This prevents look-ahead bias.

---

Step 3

Generate indicators

```
IndicatorService

↓

Technical Indicators
```

Indicators are calculated using only historical information available at that candle.

---

Step 4

Generate signal

```
RSI Strategy

↓

TradingSignal
```

The strategy never sees future prices.

---

Step 5

Execute trade

```
Trading Engine

↓

BUY

SELL

WAIT
```

The trading engine decides whether to

- Open a position
- Close a position
- Hold

---

Step 6

Update portfolio

Portfolio tracks

- Cash
- Position
- Equity
- Unrealized PnL
- Realized PnL

Portfolio value is updated after every candle.

---

Step 7

Record equity

After each candle

```
timestamp

↓

equity
```

is stored.

This becomes the equity curve.

---

Step 8

Finish simulation

When all candles have been processed

the engine generates a complete report.

---

# Current Report

The backtesting engine currently returns

```
{
    initial_balance,
    ending_balance,
    total_return,
    total_trades,
    winning_trades,
    losing_trades,
    win_rate,
    trades,
    equity_curve
}
```

---

# Trade Report

Every completed trade contains

```
Entry Price

Exit Price

Quantity

PnL

Return %

```

Future versions should include

Entry Time

Exit Time

Holding Duration

Exit Reason

Strategy Name

Market Regime

Confidence

Trade Quality

---

# Equity Curve

The engine stores portfolio equity after every candle.

Example

```
[
    {
        candle:0,
        timestamp:"...",
        equity:10000
    },

    {
        candle:1,
        timestamp:"...",
        equity:10012
    }
]
```

This allows future visualization.

---

# Current Strengths

The engine already supports

✅ Historical replay

✅ Portfolio tracking

✅ Trade recording

✅ Equity curve

✅ Win rate

✅ Total return

✅ Risk-aware position sizing

✅ ATR stop loss

✅ ATR take profit

---

# Current Limitations

The current implementation is intentionally simple.

Several professional features are still missing.

---

## Slippage

Current

None

Future

Simulate realistic fills.

---

## Commission

Current

Zero

Future

Exchange fees

Broker fees

Maker / Taker fees

---

## Spread

Current

Ignored

Future

Bid / Ask simulation

---

## Partial Orders

Current

Full fills only

Future

Partial fills

---

## Limit Orders

Current

Market Orders only

Future

Limit

Stop

Stop Limit

Trailing Orders

---

## Multiple Positions

Current

Single Position

Future

Multiple simultaneous trades

Multiple symbols

Portfolio diversification

---

## Leverage

Current

Spot trading

Future

Margin

Futures

Cross Margin

Isolated Margin

---

# Future Metrics

The engine should eventually calculate

Sharpe Ratio

Sortino Ratio

Calmar Ratio

Profit Factor

Recovery Factor

Maximum Drawdown

Average Win

Average Loss

Average Holding Time

Expectancy

Risk Reward Ratio

Largest Win

Largest Loss

Consecutive Wins

Consecutive Losses

Monthly Returns

Yearly Returns

---

# Planned Improvements

## Walk Forward Testing

Split data into

Training

↓

Validation

↓

Testing

This prevents overfitting.

---

## Monte Carlo Simulation

Randomize trade order.

Estimate strategy robustness.

---

## Parameter Optimization

Automatically test

RSI Length

ATR Multiplier

EMA Length

ADX Threshold

etc.

---

## Grid Search

Evaluate hundreds of parameter combinations.

---

## Genetic Optimization

Use evolutionary algorithms to discover better parameters.

---

## Portfolio Backtesting

Current

Single asset

Future

Multiple assets

Capital allocation

Correlation

Diversification

---

## Benchmark Comparison

Compare strategy performance against

Buy and Hold

BTC

ETH

NASDAQ

S&P500

---

## Report Export

Future exports

CSV

Excel

PDF

Interactive Dashboard

---

# Testing

Current test

```
tests/test_backtest_service.py
```

The test validates

- Historical replay
- Trade execution
- Portfolio updates
- Trade recording
- Final statistics

Every future enhancement must continue passing this test.

---

# Development Rules

The Backtesting Engine must never

- Use future candles
- Modify strategy logic
- Calculate indicators directly
- Execute trades directly
- Manage portfolio manually

Instead it should reuse existing services.

```
Market

↓

Strategy

↓

Trading Engine

↓

Portfolio

↓

Trade Recorder
```

This guarantees that

Backtesting

Paper Trading

Live Trading

all behave consistently.

---

# Long-Term Vision

The Backtesting Engine should eventually become a professional quantitative research environment capable of

- Testing thousands of strategies
- Optimizing parameters
- Simulating realistic market conditions
- Measuring institutional performance metrics
- Comparing multiple strategies
- Generating professional reports

The objective is not simply to know whether a strategy made money.

The objective is to understand

- Why it made money
- Under which market conditions
- How much risk it took
- Whether the results are statistically reliable
- Whether the strategy is suitable for deployment in live trading

Every future trading strategy must successfully pass through the Backtesting Engine before being promoted to Paper Trading or Live Trading.