# AI Trading Platform

# API Reference

---

# Purpose

This document describes every REST API exposed by the backend.

It serves as the official reference for:

- Frontend developers
- Backend developers
- AI assistants
- Third-party integrations

Every API endpoint should be documented here.

Whenever a new API is added, modified, or removed, this document must be updated.

---

# Current Status

Backend Framework

FastAPI

API Style

REST API

Response Format

JSON

Authentication

Not yet implemented

Version

v1

Base URL

```
http://localhost:8000/api/v1
```

Future

```
https://api.tradingplatform.com/api/v1
```

---

# Standard Response Format

Successful response

```json
{
    "success": true,
    "data": {},
    "message": "Operation successful"
}
```

Error response

```json
{
    "success": false,
    "error": "Invalid symbol",
    "code": 400
}
```

Every endpoint should follow the same response structure.

---

# Market APIs

---

## Get Market Data

Endpoint

```
GET /market
```

Purpose

Retrieve historical market candles.

Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | Trading pair |
| interval | string | Yes | Candle interval |
| limit | integer | No | Number of candles |

Example

```
GET

/market

?symbol=BTCUSDT

&interval=5m

&limit=500
```

Response

```json
{
    "symbol":"BTCUSDT",
    "interval":"5m",
    "candles":[]
}
```

---

# Indicator APIs

---

## Calculate Indicators

Endpoint

```
GET /indicators
```

Purpose

Return all calculated indicators for the requested market.

Parameters

- symbol
- interval

Response

```json
{
    "price":59342,

    "ema20":59298,

    "ema50":59124,

    "ema200":58711,

    "rsi14":41.7,

    "macd":-31,

    "atr14":84,

    "trend":"BEARISH"
}
```

---

# Strategy APIs

---

## Analyze Market

Endpoint

```
POST /strategy/analyze
```

Purpose

Analyze the current market and generate a TradingSignal.

Input

```json
{
    "symbol":"BTCUSDT",
    "interval":"5m",
    "strategy":"rsi"
}
```

Response

```json
{
    "direction":"BUY",

    "confidence":82,

    "entry":59320,

    "stop_loss":59205,

    "take_profit":59580,

    "risk_reward":2.3,

    "reasons":[]
}
```

---

# Backtesting APIs

---

## Run Backtest

Endpoint

```
POST /backtest
```

Purpose

Execute a complete historical backtest.

Request

```json
{
    "symbol":"BTCUSDT",

    "interval":"5m",

    "strategy":"rsi",

    "initial_balance":10000
}
```

Response

```json
{
    "total_return":18.6,

    "win_rate":61.3,

    "trades":[],

    "equity_curve":[]
}
```

---

# Portfolio APIs

---

## Get Portfolio

Endpoint

```
GET /portfolio
```

Purpose

Return the current portfolio state.

Response

```json
{
    "cash":10000,

    "equity":10240,

    "position_quantity":0.5,

    "market_value":3200,

    "unrealized_pnl":220
}
```

---

# Trade APIs

---

## Execute Trade

Endpoint

```
POST /trade
```

Purpose

Execute a BUY or SELL order.

Current

Used internally.

Future

Will support manual trading.

Request

```json
{
    "symbol":"BTCUSDT",

    "side":"BUY",

    "quantity":0.25
}
```

---

## Close Position

Endpoint

```
POST /trade/close
```

Purpose

Force close an active position.

---

# Position APIs

---

## Calculate Position Size

Endpoint

```
POST /position/size
```

Purpose

Calculate the recommended position size based on account balance and risk settings.

Request

```json
{
    "balance":10000,

    "risk_percent":1,

    "entry":59300,

    "stop_loss":59150
}
```

Response

```json
{
    "quantity":0.32
}
```

---

# Risk APIs

Future

```
GET /risk

POST /risk/validate

GET /risk/exposure
```

Purpose

- Validate trades
- Calculate portfolio risk
- Check drawdown
- Check exposure

---

# AI APIs

Future

```
POST /ai/analyze

POST /ai/explain

POST /ai/chat

POST /ai/validate
```

Purpose

AI-powered analysis and explanations.

---

# Paper Trading APIs

Future

```
POST /paper/start

POST /paper/stop

GET /paper/orders

GET /paper/trades
```

---

# Live Trading APIs

Future

```
POST /live/start

POST /live/stop

POST /live/order

POST /live/cancel
```

---

# Authentication APIs

Future

```
POST /auth/login

POST /auth/register

POST /auth/logout

POST /auth/refresh
```

JWT authentication will be used.

---

# User APIs

Future

```
GET /users/me

PATCH /users/me

DELETE /users/me
```

---

# Settings APIs

Future

```
GET /settings

PATCH /settings
```

Settings will include

- Risk %
- Default Strategy
- Broker
- AI Provider
- Notifications
- Theme

---

# Broker APIs

Future

```
POST /broker/connect

POST /broker/disconnect

GET /broker/status
```

Supported brokers

- Binance
- Bybit
- MetaTrader 5
- Interactive Brokers
- OANDA

---

# WebSocket APIs

Future

```
/ws/market

/ws/trades

/ws/portfolio

/ws/orders
```

Used for real-time updates.

---

# API Versioning

Current

```
v1
```

Future

```
/api/v1/

/api/v2/
```

Older versions should remain functional until officially deprecated.

---

# HTTP Status Codes

| Code | Meaning |
|------|----------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# Security

Future implementation

- JWT Authentication
- OAuth2
- HTTPS
- API Keys
- Rate Limiting
- Request Validation
- Input Sanitization
- CORS Protection

---

# Development Rules

Every API should

- Follow REST conventions
- Return JSON
- Use Pydantic schemas
- Validate input
- Return meaningful errors
- Include logging
- Be documented

Business logic should remain inside services.

Routes should only:

- Receive requests
- Validate input
- Call services
- Return responses

---

# Long-Term Vision

The backend API should evolve into a stable, versioned, and well-documented interface capable of supporting web applications, mobile apps, desktop clients, third-party integrations, AI assistants, and external automation tools.

The API should remain modular, consistent, secure, and scalable so that new services can be added without breaking existing integrations.