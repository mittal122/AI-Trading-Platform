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

Endpoints (actual paths — verified against running server):
- GET  /market/history      — historical candles (response: {symbol, interval, candles:[{timestamp,open,high,low,close,volume,amount}]})
- GET  /market/live         — latest candle
- GET  /indicator           — all indicators (SINGULAR path; response: {symbol, interval, indicators:{...}})
- GET  /strategy            — StrategyResponse (signal string, no regime/quality)
- GET  /strategy/signal     — FULL TradingSignal (direction, regime, quality_score/grade, atr, explanation)
- GET  /portfolio/analytics — Sharpe/Sortino/Calmar/etc.
- GET  /trades/history      — persisted trade history (filter: symbol, strategy, mode, limit, offset)
- GET  /trades/backtest-history + POST /trades/backtest-record
- POST /paper/start, /paper/stop · GET /paper/status · WS /paper/ws (2s status stream)
- POST /paper/order — one-click manual paper trade from a signal (entry/SL/TP); auto-closes at SL or TP, persists to DB
- GET  /paper/orders — manual paper trader state (balance, open + closed orders)
      Frontend: "Place Paper Trade" button lives inside SignalCard → shows on Dashboard + Signals
- POST /trading/start, /trading/stop?emergency=true · GET /trading/status
- POST /ai/chat, /ai/analyze, /ai/select-strategy, /ai/validate-trade, /ai/review-risk, /ai/sentiment
- POST /prediction/predict  — Kronos OHLCV forecast

Frontend consumes these via Vite proxy (/api → localhost:8000, ws:true). Client: frontend/src/api/client.ts

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
      Files: ema_strategy.py, macd_strategy.py, breakout_strategy.py, supertrend_strategy.py,
      cta_trend_strategy.py, turtle_strategy.py, engulfing_scalp_strategy.py (all added 2026-07-02)
      All registered in StrategyFactory (keys: rsi, ema, macd, breakout, supertrend, cta_trend,
      turtle, engulfing_scalp)
      IndicatorService extended: previous_ema20/50, EMA crossover booleans,
      previous_histogram, MACD crossover booleans, supertrend + supertrend_direction,
      calculate_cta_trend() — 3 EMA-pair composite + 2 momentum sub-signals + realized vol,
      calculate_atr_at_period() — ATR at a caller-specified window (not fixed 14),
      rolling_channel() — highest-high/lowest-low over N closed candles,
      calculate_rsi_series() — full RSI series (not just latest scalar)

      CTA Trend (Systematic Trend Following, CTA-style): composite of 3 EMA-crossover pairs
      (10/50, 20/100, 50/200) + 2 time-series momentum sub-signals (90/180-bar lookback),
      averaged to [-1,+1]. Confidence = conviction (sub-signal agreement) + volatility-targeted
      exposure bonus. Stops/targets are ATR(20)-scaled (2.5x/4x), independent of the
      regime-based DynamicATR table other strategies use. All periods in strategy_config.py
      (CTA_* constants).

      Turtle Trading (Richard Dennis-style dual breakout): System 1 = 20-bar breakout,
      filtered by whether the LAST System-1 breakout in that direction was a loss (skip if it
      won, unless price also breaks the unfiltered 55-bar channel as a failsafe). System 2 =
      55-bar breakout, always taken, no filter. N = ATR(20), stops/targets are 2N/4N (fixed
      RR=2.0 by construction). The last-breakout-loss filter is a historical simulation
      (backward scan, capped at TURTLE_BACKWARD_SCAN_BARS=150) — kept in the strategy file,
      not IndicatorService, since it's a trade-outcome decision, not an indicator calc.
      Slowest strategy in the platform (~15s for a 500-candle backtest) due to this scan —
      acceptable but noticeably slower than the others. All periods in TURTLE_* config.

      Engulfing Scalp (long-only): price > EMA200 AND RSI14 > 50 AND a bullish engulfing
      candle on the last closed bar → BUY. Stop/target sized off the engulfing candle's own
      range (not ATR): stop = entry - 2x range, target = entry + (risk x RR 2.0) → fixed
      RR=2.0 by construction. Confidence gets a +10 bonus on bullish RSI divergence (price
      lower-low + RSI higher-low across the last 2 swing lows in a 20-bar window). All
      periods in ENGULF_* config.

      User-supplied 5 strategies total (Turtle, CTA Trend, EMA Pullback, SMC, Engulfing
      Scalp) across two conversations. Implemented: CTA Trend, Turtle, Engulfing Scalp (user
      explicitly requested each in turn). NOT implemented: EMA Pullback, SMC (Smart Money
      Concepts — most complex, has FVG/liquidity-sweep/HTF-structure logic) — user hasn't
      asked for these yet.

### Phase 3 — Advanced Risk Management

- [x] Kelly Criterion position sizing
      File: backend/app/services/position/kelly_position.py
      Formula: f = (bp - q) / b, where b=RR, p=win_rate, q=1-p
      Cap at 25% of equity

- [x] Trailing Stop implementation
      Move to exit_manager.py (Task 5 above — done there)

- [x] Drawdown protection
      File: backend/app/services/risk/drawdown_guard.py
      Track peak equity. If drawdown > 10%, halt new trades.
      If drawdown > 20%, close all positions.

- [x] Daily loss limit
      File: backend/app/services/risk/daily_loss_limit.py
      Track daily realized PnL. If daily loss > 2% of equity, halt trading for the day.

- [x] Partial exits
      In exit_manager.py: close 50% at 1:1 RR, let remaining run to full TP

- [x] Risk-adjusted position sizing
      In PortfolioEngine: cap single position at 5% of equity regardless of signal

### Phase 4 — Portfolio Analytics

- [x] Sharpe Ratio
- [x] Sortino Ratio
- [x] Calmar Ratio
- [x] Profit Factor
- [x] Maximum Drawdown
- [x] Win Rate, Avg Win, Avg Loss
- [x] Expectancy per trade
      File: backend/app/services/portfolio/analytics.py
      Add analytics endpoint: GET /api/v1/portfolio/analytics

### Phase 5 — AI Integration ✅ DONE (multi-model via NVIDIA NIM)

All 7 AI services route through a single NVIDIA NIM endpoint (one OpenAI-compatible
API, one NVIDIA_API_KEY) — NIM hosts each third-party model behind its own slug.
File: backend/app/core/ai_provider_config.py — connection + per-service ServiceModelConfig
File: backend/app/services/ai/llm_client.py — MultiProviderAIService (openai SDK, base_url=NIM)
NOT Anthropic/Claude — base_ai.py (old Anthropic-only base class) was removed.

| Service | File | Model (NIM slug) | Notes |
|---|---|---|---|
| Market Analyst | market_analyst.py | nvidia/nemotron-3-super-120b-a12b | thinking OFF (fast/credit-efficient) |
| Strategy Selector | strategy_selector.py | zai-org/glm-5.1 | best-guess slug — verify on build.nvidia.com |
| Trade Validator | trade_validator.py | deepseek-ai/deepseek-v4-pro | thinking ON (money-critical, highest reasoning) |
| Risk Manager | risk_manager.py | zai-org/glm-5.1 | |
| Sentiment Analyzer | sentiment_analyzer.py | minimaxai/minimax-m3 | multimodal-capable model, used text-only here |
| Chat Assistant | chat_assistant.py | moonshotai/kimi-k2.5 | best-guess slug |
| Backtest Explainer (NEW) | backtest_explainer.py | minimaxai/minimax-m2.7 | explains completed backtest metrics in plain English |

- [x] LLM Market Analyst — indicators+regime → sentiment + analysis + key levels
- [x] AI Strategy Selector — regime+performance → recommended strategy + reasoning
- [x] AI Trade Validator — APPROVE/REJECT + reason + risk_flags
- [x] AI Risk Manager — HOLD/REDUCE/CLOSE/TIGHTEN_STOP + suggested stop/size
- [x] News/Sentiment Analysis — headlines → BULLISH/BEARISH/NEUTRAL + score
- [x] AI Chat Assistant — POST /api/v1/ai/chat, multi-turn
- [x] Backtest Explainer — POST /api/v1/ai/explain-backtest — NEW, takes backtest
      metrics (win rate, Sharpe, etc.) → plain-English summary/strengths/weaknesses/suggestion
      Endpoints: /ai/analyze, /ai/select-strategy, /ai/validate-trade, /ai/review-risk,
      /ai/sentiment, /ai/chat, /ai/explain-backtest — all rate-limited via tier_rate_limit
      Model slugs + temperature/top_p/extra_body (thinking toggles) all in
      ai_provider_config.py, every value overridable via env var — no code change needed
      to fix a wrong slug.

### Phase 6 — Paper Trading ✅ DONE

- [x] Virtual account with live Binance prices (no real orders)
- [x] File: backend/app/services/paper/paper_trading_engine.py
- [x] Endpoint: POST /api/v1/paper/start, POST /api/v1/paper/stop, GET /api/v1/paper/status
- [x] Track virtual balance, virtual positions, virtual P&L
- [x] Real-time WebSocket price feed from Binance (kline stream via python-binance)
      PaperFactory.get_engine() → module-level singleton
      Uses all risk guards: DrawdownGuard, DailyLossLimit, 5% equity cap, partial exits
      VERIFIED LIVE (2026-07-02): started engine on 1m BTCUSDT, watched a real
      BUY → TAKE_PROFIT cycle execute end-to-end via backend log + DB row.
      NOT A BUG: the engine itself works correctly — it only trades when its
      strategy actually fires a signal on a closed candle (can look "silent"
      in choppy markets). Frontend gap (fixed): PaperTrade.tsx only showed the
      live in-memory engine's last 20 trades (reset on backend restart) and
      never showed ManualPaperTrader orders (from the SignalCard button) at
      all. Now also fetches GET /trades/history?mode=PAPER (durable, survives
      restarts, covers both auto-bot + manual trades) and GET /paper/orders.
      Engine itself is a server-side singleton — refreshing the browser was
      never actually stopping it; that's now visible in the UI too.

### Phase 7 — Live Trading ✅ DONE

- [x] Binance live order execution (market orders)
      File: backend/app/services/execution/binance_execution.py
      dry_run=True (default) simulates fills locally — no real orders
      dry_run=False places real market orders via Binance API

- [x] Add BINANCE_API_KEY, BINANCE_SECRET to .env (required for live mode)

- [x] Order confirmation + order tracking
      Every order logged to BinanceExecution._orders with order_id, fill price, fee, status

- [x] Emergency stop button endpoint: POST /api/v1/trading/stop?emergency=true
      Cancels all open Binance orders + market-sells open position immediately
      Sets emergency_stopped=True — engine requires app restart to re-enable

- [x] LiveTradingEngine: backend/app/services/trading/live_trading_engine.py
      Same WebSocket loop as PaperTradingEngine, routes execution through BinanceExecution
      Singleton via LiveTradingFactory

- [ ] Bybit adapter (future): bybit_execution.py

### Phase 8 — Database Integration ✅ DONE

- [x] PostgreSQL (production) + SQLite (default, zero-config dev/test)
      DATABASE_URL env var: not set → sqlite+aiosqlite:///./trading.db
                            set → use as-is (postgresql+asyncpg://...)

- [x] SQLAlchemy 2.0 async ORM — backend/app/db/
      database.py: engine, AsyncSessionLocal, Base, create_tables(), get_db()
      models.py: Trade, BacktestRun, Position, Portfolio, Strategy, User
      repository/trade_repo.py: save, get_history (filterable), count_by_mode
      repository/backtest_repo.py: save, get_recent (filterable)

- [x] Alembic migrations
      alembic.ini + alembic/env.py (async-compatible, render_as_batch for SQLite)
      alembic/versions/*_initial_schema.py — all 6 tables

- [x] DB persistence layer — backend/app/services/db_service.py
      DatabaseService: save_trade(), get_trade_history(), save_backtest_run(), get_backtest_history()

- [x] Tables auto-created on startup (main.py lifespan calls create_tables())

- [x] Trade history endpoints — GET /api/v1/trades/history
      Filters: symbol, strategy, mode (PAPER/LIVE/BACKTEST), limit, offset, pagination total
      GET /api/v1/trades/backtest-history — paginated (limit up to 1000, offset), returns
      total + full detail analytics per run (winning/losing trades, avg win/loss, expectancy,
      sortino, calmar — added 2026-07-02, was summary-only before)
      DELETE /api/v1/trades/backtest-history/{id} — delete one run
      DELETE /api/v1/trades/backtest-history — delete all runs
      POST /api/v1/trades/backtest-record — run backtest + persist result in one call

### Phase 9 — Frontend Dashboard ✅ DONE

- [x] React 19 + TypeScript + TailwindCSS v4 + Vite 8
      frontend/ — npm run dev (port 5173), npm run build
      Vite proxy: /api → http://localhost:8000 (no CORS issues)

- [x] TradingView Lightweight Charts — candlestick chart on Dashboard

- [x] Pages: Dashboard, Signals, Backtest, Portfolio, Paper Trade, AI Chat, Settings
      src/pages/Dashboard.tsx   — live chart + signal + indicators, auto-refresh 60s
      src/pages/Signals.tsx     — any strategy/symbol/interval signal on demand
      src/pages/Backtest.tsx    — run + persist backtest, history table + pagination
      (rows-per-page 50/100/All), delete-row + delete-all (2x confirm), expandable
      per-row detail (winning/losing trades, avg win/loss, expectancy, sortino, calmar),
      "Backtest All Timeframes" button (loops all 8 intervals, sorted summary + detail,
      each run persists to history normally), inputs persisted via localStorage
      src/pages/Portfolio.tsx   — analytics + trade history with mode filter
      src/hooks/usePersistedState.ts — useState that survives refresh via localStorage,
      used by Backtest.tsx and PaperTrade.tsx form inputs (2026-07-02 fix — inputs were
      resetting to defaults on every page refresh)
      src/pages/PaperTrade.tsx  — start/stop paper engine, live position + trade log.
      Also shows GET /paper/orders (manual SignalCard-button trades) and
      GET /trades/history?mode=PAPER (durable DB history — survives backend
      restarts; the old page only showed the live engine's in-memory last-20,
      which looked like "trades not shown" whenever the process had restarted
      since the trade happened). Inputs persisted via usePersistedState.
      src/pages/AIChat.tsx      — multi-turn chat with suggested prompts. Error
      handling now surfaces the real backend error (e.g. "NVIDIA_API_KEY not
      set") instead of a canned message — "chat doesn't work" is almost always
      a missing NVIDIA_API_KEY in .env, not a code bug; check that first.
      src/pages/Settings.tsx    — env vars reference + phase completion status
      (Phase 10 was stuck at incomplete in the UI after Phase 10 shipped — fixed)

- [x] Components: SignalCard, PortfolioSummary, TradeTable, IndicatorPanel, RegimeBadge, Sidebar
      src/api/client.ts — typed axios API client for all backend endpoints

### Phase 10 — SaaS Platform ✅ DONE

- [x] JWT authentication (register, login, token refresh)
      File: backend/app/core/security.py (bcrypt hash + JWT encode/decode, tier claim embedded)
      File: backend/app/services/auth/auth_service.py — AuthService (register/login/refresh/API keys)
      File: backend/app/api/v1/auth.py — POST /auth/register, /auth/login, /auth/refresh, GET /auth/me
      File: backend/app/api/deps.py — get_current_user (JWT bearer OR X-API-Key header, either works)
      Uses `python-jose` for JWT, `bcrypt` directly for hashing (passlib's bcrypt backend
      is broken on bcrypt>=4.1 — do not reintroduce passlib for this)

- [x] Multi-user support — User model + auth exists; `trades.user_id` FK added (nullable) for
      future trade-history scoping. NOTE: paper/live trading engines are still process-wide
      singletons (PaperFactory/LiveTradingFactory) — not yet scoped per-user. Fine for one
      deployment per operator; would need per-user engine instances for true multi-tenant trading.

- [x] API key management
      DB: ApiKey model (backend/app/db/models.py) — key_hash (SHA-256) stored, never the raw key
      POST /auth/api-keys (returns raw key once), GET /auth/api-keys, DELETE /auth/api-keys/{id}
      Auth via X-API-Key header — same get_current_user dependency as JWT

- [x] Subscription tiers (free / pro / enterprise)
      User.tier field; GET /billing/tiers (public tier catalog + rate limits)

- [x] Billing integration (Stripe)
      File: backend/app/services/billing/stripe_service.py — checkout sessions + webhook sync
      POST /billing/checkout, GET /billing/subscription, POST /billing/webhook
      Requires STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / STRIPE_PRICE_PRO / STRIPE_PRICE_ENTERPRISE
      Gracefully degrades to 503 if unconfigured (same pattern as AI services)

- [x] Rate limiting per user tier
      File: backend/app/core/rate_limit.py — slowapi, tier read from JWT claim (no DB hit)
      Applied via @limiter.limit(tier_rate_limit) decorator on: AI endpoints (all 6),
      /paper/start, /paper/order, /trading/start. Fixed 10/minute on /auth/register, /auth/login.
      NOTE: no global middleware — slowapi's SlowAPIMiddleware only supports static default
      limits, not per-request dynamic ones combined with middleware's in_middleware=True path
      (it skips per-route dynamic limits entirely). Decorator-per-route is the correct pattern.

- [x] Cloud deployment: Docker + docker-compose
      docker/backend.Dockerfile, docker/frontend.Dockerfile (multi-stage, nginx), docker/nginx.conf
      docker-compose.yml — postgres + backend + frontend, all env vars wired
      Run: `docker compose up --build` (needs .env — see .env.example)
      VERIFIED: both images built and run for real — alembic migrations apply, Kronos loads,
      FastAPI boots, live HTTP requests succeed inside the container; nginx correctly proxies
      to the backend service on the compose network.
      NOTE: no separate AWS/GCP IaC — docker-compose is the deployment artifact; push images to
      any container host (ECS, Cloud Run, etc.) manually or via CI
      NOTE: backend requires KRONOS_PATH mounted with the Kronos model repo's `model.py` present
      (sys.path.insert + `from model import ...` in kronos_service.py) — the whole app fails to
      boot without it, since main.py imports the Kronos singleton eagerly. Set
      KRONOS_PATH_HOST in .env to the real Kronos repo path on the host.

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
