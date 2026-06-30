# AI Trading Platform — Build Guide

This file is the single source of truth for building this project.
Read this before touching any code.

---

## Project Goal

Enterprise-grade algorithmic trading platform with AI integration.
Multi-asset. Multi-strategy. Eventually SaaS.
Current completion: ~45%.

---

## Stack

- Python 3.12 + FastAPI + Pydantic v2
- PyTorch + CUDA — Kronos model (OHLCV forecasting)
- Binance — market data provider
- pandas / numpy
- DB / Auth / Frontend — NOT YET BUILT

---

## Architecture Rules — NEVER VIOLATE

1. Factory pattern everywhere — never instantiate services directly
2. Strict layer separation:
   - IndicatorService calculates indicators — nothing else does
   - Strategy layer generates signals — never executes trades
   - Trading Engine executes — never calculates indicators or generates signals
   - Portfolio tracks positions — never generates signals
   - Schemas hold data — no business logic inside schemas
3. No hardcoded thresholds — all values come from config or env vars
4. BaseClass + Simple/concrete implementation pattern
5. Every new module needs a test file in tests/
6. Black formatting, descriptive names, functions 10-40 lines, classes 300-500 lines max
7. Conventional commits: feat(strategy): ..., fix(backtest): ..., test(risk): ...

---

## Canonical Pipeline

```
Binance
  → MarketService
  → IndicatorService
  → MarketRegime          ← NEW (just built)
  → SignalScore
  → TradeDecision
  → TradingSignal
  → TradingEngine
  → TradeManager
  → ExecutionEngine
  → PortfolioEngine
  → TradeRecorder
  → BacktestReport / Live Trade
```

AI prediction path (separate):
```
MarketService → KronosService → PredictionService → POST /predict
```

---

## API Base URL

`http://localhost:8000/api/v1`

Endpoints:
- GET  /market           — historical candles
- GET  /indicators       — all indicators
- POST /strategy/analyze — TradingSignal via RSI strategy
- POST /prediction/predict — Kronos OHLCV forecast

---

## Phase Completion Status

### Phase 1 — Core Infrastructure ✅ DONE

- [x] MarketService (Binance)
- [x] IndicatorService (15+ indicators)
- [x] BaseStrategy + StrategyFactory
- [x] RSIStrategy
- [x] SignalScore (adaptive weighted, regime-aware)
- [x] TradeDecision
- [x] TradingEngine (single-position, simulated)
- [x] ExecutionEngine
- [x] PortfolioEngine
- [x] PositionEngine (fixed risk sizing)
- [x] RiskEngine (ATR stop/TP)
- [x] TradeManager
- [x] TradeRecorder
- [x] BacktestEngine (candle replay, equity curve, win rate)
- [x] Kronos AI prediction endpoint
- [x] FastAPI app (lifespan, routers, schemas)
- [x] 15+ test files

### Phase 2 — Professional Strategy System ✅ DONE

- [x] Task 1: Market Regime Detection
      File: backend/app/services/strategy/market_regime.py
      Detects: STRONG_BULL / WEAK_BULL / STRONG_BEAR / WEAK_BEAR / SIDEWAYS
      Volatility: HIGH / NORMAL / LOW using ATR% + BB Width%
      Integrated into RSIStrategy → SignalScore

- [x] Task 2: Adaptive Signal Weighting
      Replaced fixed (+25/+20/+15) with weighted percentages:
      Trend 30% | Regime 25% | Momentum 20% | Volatility 15% | Volume 10%

- [x] Task 3: Better Confidence Calculation
      Factors: score gap (agreement), regime multiplier, volatility dampener

- [x] Task 4: Better Entry Filters
      File: backend/app/services/strategy/entry_filter.py
      BUY: bull trend (critical) + ADX (critical) + MACD + VWAP + RSI
      SELL: bear trend (critical) + ADX (critical) + MACD + VWAP + RSI
      Wired into RSIStrategy.generate_signal() — gates BUY/SELL decisions

- [x] Task 5: Advanced Exit Logic
      File: backend/app/services/trade/exit_manager.py + trade_manager.py
      Implemented: trailing stop, break-even, ATR reversal exit, time exit, signal reversal
      TradeState extended: peak_price, candles_held, atr_at_entry, trailing_stop_active

- [x] Task 6: Dynamic ATR Multiplier
      File: backend/app/services/risk/dynamic_atr.py
      Regime+volatility lookup table — 15 combinations
      Wired into RSIStrategy + all 4 new strategies

- [x] Task 7: Trade Quality Score
      File: backend/app/services/strategy/trade_quality.py
      0-100 score across: Trend(25) + Momentum(20) + Volume(20) + RR(20) + Regime(15)
      Grades: A+ / A / B / C / D / F
      Added quality_score + quality_grade to TradingSignal schema

- [x] Task 8: Strategy Explanation Engine
      File: backend/app/services/strategy/explainer.py
      Human-readable summary + market context + indicator snapshot + reasons + quality
      Added explanation field to TradingSignal schema

- [x] Task 9: Strategy Configuration
      File: backend/app/core/strategy_config.py
      All thresholds centralized: RSI, ADX, ATR multipliers, regime ADX, BB thresholds,
      entry filter confirmations, time exit, quality RR thresholds, supertrend params

- [x] Task 10: Multiple Strategies
      Files: ema_strategy.py, macd_strategy.py, breakout_strategy.py, supertrend_strategy.py
      All registered in StrategyFactory (keys: rsi, ema, macd, breakout, supertrend)
      IndicatorService extended: previous_ema20/50, EMA crossover booleans,
      previous_histogram, MACD crossover booleans, supertrend + supertrend_direction

### Phase 3 — Advanced Risk Management

- [ ] Kelly Criterion position sizing
      File: backend/app/services/position/kelly_position.py
      Formula: f = (bp - q) / b, where b=RR, p=win_rate, q=1-p
      Cap at 25% of equity

- [ ] Trailing Stop implementation
      Move to exit_manager.py (Task 5 above — done there)

- [ ] Drawdown protection
      File: backend/app/services/risk/drawdown_guard.py
      Track peak equity. If drawdown > 10%, halt new trades.
      If drawdown > 20%, close all positions.

- [ ] Daily loss limit
      File: backend/app/services/risk/daily_loss_limit.py
      Track daily realized PnL. If daily loss > 2% of equity, halt trading for the day.

- [ ] Partial exits
      In exit_manager.py: close 50% at 1:1 RR, let remaining run to full TP

- [ ] Risk-adjusted position sizing
      In PortfolioEngine: cap single position at 5% of equity regardless of signal

### Phase 4 — Portfolio Analytics

- [ ] Sharpe Ratio
- [ ] Sortino Ratio
- [ ] Calmar Ratio
- [ ] Profit Factor
- [ ] Maximum Drawdown
- [ ] Win Rate, Avg Win, Avg Loss
- [ ] Expectancy per trade
      File: backend/app/services/portfolio/analytics.py
      Add analytics endpoint: GET /api/v1/portfolio/analytics

### Phase 5 — AI Integration

- [ ] LLM Market Analyst
      Uses Claude API (claude-sonnet-4-6) to analyze market conditions
      Input: indicators dict + regime + recent price action
      Output: natural language market analysis

- [ ] AI Strategy Selector
      Uses Claude API to select best strategy given current regime
      Input: regime + available strategies + recent backtest performance
      Output: recommended strategy name + reasoning

- [ ] AI Trade Validator
      Before executing a trade, ask Claude to validate the signal
      Red flags: contradicting indicators, news events, extreme volatility
      Output: APPROVE / REJECT + reason

- [ ] AI Risk Manager
      Claude reviews open positions and suggests risk adjustments
      Checks: position size, stop distance, portfolio exposure

- [ ] News / Sentiment Analysis
      Fetch crypto news via API, run sentiment analysis
      Input into confidence calculation as sentiment multiplier

- [ ] AI Chat Assistant (API endpoint)
      POST /api/v1/ai/chat — user asks questions about their portfolio / signals

### Phase 6 — Paper Trading

- [ ] Virtual account with live Binance prices (no real orders)
- [ ] File: backend/app/services/paper/paper_trading_engine.py
- [ ] Endpoint: POST /api/v1/paper/start, GET /api/v1/paper/status
- [ ] Track virtual balance, virtual positions, virtual P&L
- [ ] Real-time WebSocket price feed from Binance

### Phase 7 — Live Trading

- [ ] Binance live order execution (market + limit orders)
- [ ] File: backend/app/services/execution/binance_execution.py
- [ ] Add BINANCE_API_KEY, BINANCE_SECRET to .env
- [ ] Order confirmation + order tracking
- [ ] Emergency stop button endpoint: POST /api/v1/trading/stop
- [ ] Bybit adapter (future): bybit_execution.py

### Phase 8 — Database Integration

- [ ] Choose: PostgreSQL (recommended for production)
- [ ] File: backend/app/db/models.py — SQLAlchemy models
- [ ] Models: Trade, Position, Portfolio, BacktestRun, Strategy, User
- [ ] Alembic migrations
- [ ] Replace in-memory state with DB persistence
- [ ] Trade history endpoint: GET /api/v1/trades/history

### Phase 9 — Frontend Dashboard

- [ ] React + TypeScript + TailwindCSS + Vite
- [ ] TradingView Lightweight Charts for price/indicator display
- [ ] Pages: Dashboard, Signals, Backtest, Portfolio, Settings, AI Chat
- [ ] Real-time updates via WebSocket
- [ ] Components: SignalCard, PortfolioSummary, TradeTable, IndicatorPanel, RegimeBadge

### Phase 10 — SaaS Platform

- [ ] JWT authentication (register, login, token refresh)
- [ ] Multi-user support
- [ ] API key management
- [ ] Subscription tiers (free / pro / enterprise)
- [ ] Billing integration (Stripe)
- [ ] Rate limiting per user tier
- [ ] Cloud deployment: Docker + AWS/GCP

---

## Immediate Next Task

**Phase 3 — Advanced Risk Management**
Start with: `backend/app/services/position/kelly_position.py` (Kelly Criterion position sizing)
Then: `backend/app/services/risk/drawdown_guard.py` (drawdown protection)
Then: `backend/app/services/risk/daily_loss_limit.py` (daily loss limit)

---

## File Naming Conventions

```
backend/app/services/<domain>/base_<domain>.py      — abstract base
backend/app/services/<domain>/simple_<domain>.py    — default implementation
backend/app/services/<domain>/<domain>_factory.py   — factory
backend/app/schemas/<domain>.py                     — pydantic schemas
backend/app/api/v1/<domain>.py                      — FastAPI router
tests/test_<domain>_service.py                      — test
```

---

## Docs Location

`/media/sun/drive/devops-project/trading app/AI-Trading-Platform/AI-Trading-Platform/docs/`

Key docs:
- 00_PROJECT_OVERVIEW.md
- 01_ARCHITECTURE.md
- 03_ROADMAP.md
- 04_CURRENT_WORK.md
- 07_NEXT_TASKS.md
- 09_STRATEGY_ENGINE.md
- 13_TRADING_ENGINE.md
- 15_RISK_MANAGEMENT.md

---

## Environment Variables Required

```
KRONOS_PATH       # local path to Kronos model
DEFAULT_SYMBOL    # e.g. BTCUSDT
DEFAULT_INTERVAL  # e.g. 5m
DEFAULT_LOOKBACK  # integer
DEFAULT_PRED_LEN  # integer
```

NEVER commit: BINANCE_API_KEY, BINANCE_SECRET, OPENAI_API_KEY, CLAUDE_API_KEY,
              DATABASE_URL, JWT_SECRET

---

## Running Tests

```bash
cd "/media/sun/drive/devops-project/trading app/AI-Trading-Platform"
PYTHONPATH=. .venv/bin/python tests/test_<name>.py
```
