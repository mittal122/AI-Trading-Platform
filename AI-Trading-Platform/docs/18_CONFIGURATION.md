# AI Trading Platform

# Configuration Guide

---

# Purpose

This document defines every configurable option within the AI Trading Platform.

One of the core architectural principles of this project is:

> **No feature should require modifying source code to change its behavior.**

Instead, all configurable values should eventually be managed through:

- Environment Variables
- Configuration Files
- Database Settings
- SaaS Admin Dashboard
- User Settings Page

The application should be fully configurable without editing Python code.

---

# Configuration Philosophy

Configuration should never be hardcoded.

Bad Example

```python
risk_percent = 1
```

Good Example

```python
risk_percent = settings.risk_percent
```

Future sources of configuration

```
Environment Variables

↓

Database

↓

User Settings

↓

Admin Dashboard

↓

Configuration Service
```

---

# Configuration Categories

The platform configuration is divided into the following sections:

- General
- Trading
- Risk Management
- Indicators
- Strategies
- Backtesting
- Paper Trading
- Live Trading
- Brokers
- AI
- Notifications
- Database
- Security
- Performance
- Logging
- Frontend

---

# General Configuration

Examples

```
Application Name

Version

Timezone

Default Currency

Language

Theme

Date Format

Time Format
```

---

# Trading Configuration

Examples

```
Default Symbol

BTCUSDT

Default Interval

5m

Default Strategy

RSI

Maximum Open Positions

5

Default Order Type

Market
```

---

# Risk Management Configuration

Examples

```
Risk Per Trade

1%

Maximum Daily Loss

3%

Maximum Drawdown

10%

Minimum Risk Reward

2.0

ATR Stop Multiplier

1.5

ATR Take Profit Multiplier

3.0

Enable Trailing Stop

True

Break Even Trigger

1R
```

---

# Indicator Configuration

Examples

```
EMA20 Length

20

EMA50 Length

50

EMA200 Length

200

RSI Length

14

RSI Oversold

30

RSI Overbought

70

MACD Fast

12

MACD Slow

26

MACD Signal

9

ADX Length

14

VWAP Enabled

True
```

Every indicator parameter should be configurable.

---

# Strategy Configuration

Each strategy should maintain independent settings.

Example

```
RSI Strategy

RSI Length

Oversold Level

Overbought Level

ATR Multiplier

Minimum Confidence
```

Future

```
EMA Strategy

MACD Strategy

Supertrend Strategy

Breakout Strategy
```

Each strategy should expose its own configuration.

---

# Signal Score Configuration

Current

Hardcoded values.

Future

```
Trend Weight

25

MACD Weight

20

ADX Weight

15

Volume Weight

10

Market Regime Weight

30
```

Weights should be editable without modifying code.

---

# Trade Decision Configuration

Examples

```
Minimum Confidence

70

Minimum Buy Score

60

Minimum Sell Score

60

Maximum Spread

0.15%

Minimum Volume

1.2 Relative Volume
```

---

# Backtesting Configuration

Examples

```
Initial Balance

10000

Commission

0.1%

Slippage

0.05%

Spread

0

Use Market Orders

True

Use Limit Orders

False
```

Future

```
Monte Carlo Enabled

Walk Forward Enabled

Optimization Enabled
```

---

# Paper Trading Configuration

Examples

```
Virtual Balance

10000

Reset Balance

Enabled

Commission

Enabled

Slippage

Enabled

Latency Simulation

Enabled
```

---

# Live Trading Configuration

Examples

```
Live Trading Enabled

False

Trading Mode

Spot

Maximum Position Size

20%

Confirmation Required

True
```

Safety features

```
Emergency Stop

Trading Lock

Manual Approval

Weekend Trading
```

---

# Broker Configuration

Supported Brokers

```
Binance

Bybit

MetaTrader 5

Interactive Brokers

OANDA
```

Each broker should store

```
API Key

Secret

Passphrase

Environment

Sandbox

Live

Timeout

Retry Count
```

Broker credentials should never be stored in source code.

---

# AI Configuration

Examples

```
AI Enabled

True

Preferred Provider

Claude

Fallback Provider

OpenAI

Temperature

0.2

Max Tokens

2000

Streaming Enabled

True
```

Future Providers

```
Claude

GPT

Gemini

Ollama

NVIDIA NIM
```

Changing providers should require only a configuration update.

---

# Notification Configuration

Examples

```
Email Notifications

Telegram

Discord

Slack

SMS

Push Notifications
```

Notification Events

```
Trade Open

Trade Closed

Stop Loss

Take Profit

Drawdown Alert

Daily Report

Weekly Report
```

---

# Database Configuration

Examples

```
Database Host

Port

Username

Password

Database Name

Connection Pool Size

Timeout
```

Support

```
SQLite

PostgreSQL

MySQL
```

---

# Security Configuration

Examples

```
JWT Expiration

Refresh Token

API Rate Limit

Password Policy

Two-Factor Authentication

Encryption Enabled
```

Future

```
OAuth

Google Login

GitHub Login
```

---

# Performance Configuration

Examples

```
Indicator Cache

Enabled

Cache Duration

60 Seconds

Worker Threads

8

Async Enabled

True
```

---

# Logging Configuration

Examples

```
Log Level

INFO

Debug Enabled

False

Log Rotation

Daily

Error Reporting

Enabled
```

---

# Frontend Configuration

Examples

```
Theme

Dark

Accent Color

Blue

Chart Theme

TradingView Dark

Default Dashboard

Portfolio

Language

English
```

---

# Environment Variables

Sensitive values should always come from environment variables.

Examples

```
DATABASE_URL

SECRET_KEY

JWT_SECRET

OPENAI_API_KEY

CLAUDE_API_KEY

GEMINI_API_KEY

BINANCE_API_KEY

BINANCE_SECRET

MT5_LOGIN

MT5_PASSWORD
```

These values should never be committed to Git.

---

# Configuration Service

Future architecture

```
Configuration Service

↓

Environment Variables

↓

Database Settings

↓

User Settings

↓

Admin Settings

↓

Application
```

All modules should obtain configuration through this service rather than reading files directly.

---

# SaaS Settings Page

Eventually, every configurable option should be exposed through the web interface.

Categories

- General
- Trading
- Risk
- Indicators
- Strategies
- Brokers
- AI
- Notifications
- Security

Users should be able to update settings without restarting the application whenever possible.

---

# Development Rules

When adding a new feature:

- Avoid hardcoded values.
- Introduce a configurable setting if the value may change.
- Use the Configuration Service as the single source of truth.
- Document every new setting in this file.

---

# Long-Term Vision

The AI Trading Platform should become a fully configurable SaaS application where every aspect of trading, risk management, AI behavior, broker integration, performance tuning, and user preferences can be managed through a centralized configuration system.

Developers should never need to modify source code simply to adjust operational behavior. By centralizing configuration, the platform becomes easier to maintain, safer to operate, and significantly more flexible for both individual users and enterprise deployments.