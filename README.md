# AI Trading Platform

An AI-powered algorithmic trading terminal for crypto. FastAPI + PyTorch backend,
React trading-terminal frontend, live Binance market data, eight rule-based
strategies, a Smart Money Concepts (SMC) engine, candlestick + chart-pattern
recognition, LLM-assisted analysis, and an OHLCV foundation model (Kronos) for
price forecasting — with paper trading, hands-free auto-testing, backtesting,
and real portfolio analytics built in.

> **Disclaimer** — This is a research/educational project. Paper trading is the
> default everywhere; live trading is opt-in, dry-run by default, and entirely
> at your own risk. Nothing here is financial advice.

---

## Highlights

- **Terminal** — dense market dashboard: watchlist with signal radar, live
  candlestick chart with infinite scroll-back, order-book pressure, aggressive
  taker-flow, perp funding, market movers, and a volume-spike scanner across
  the most liquid pairs.
- **Strategy engine** — 8 strategies (RSI, EMA crossover, MACD, Bollinger
  breakout, Supertrend, CTA trend-following, Turtle, Engulfing scalp) with
  market-regime detection, adaptive signal weighting, entry filters, trade
  quality grading (A+–F), and a plain-English explanation for every signal.
- **SMC Analyzer** — full Smart Money Concepts pipeline (structure/BOS/CHoCH,
  order blocks, FVGs, liquidity pools & sweeps, premium/discount, POIs) with a
  six-factor market-bias verdict, a per-side confluence checklist that gates
  trade plans, walk-forward backtesting, and a background signal scanner.
- **SMC Auto-Test** — a server-side loop that re-analyzes on every candle
  close, paper-trades the stronger side, holds to target, and flips direction
  when the opposite side's confluence overtakes the current one.
- **Pattern recognition** — ~32 candlestick patterns + classical chart shapes
  (double/triple tops, head & shoulders, triangles, wedges, flags, channels,
  staircases, cup & handle), forward-resolved statuses (Confirmed / Forming /
  Failed), drawn directly on the chart, with on-demand AI explanations.
- **Analysis tools** — support/resistance, moving averages, VWAP, pivot points,
  ATR, FVG, and trend lines as toggleable chart overlays, plus client-side
  Fibonacci/EMA indicators with editable settings and automatic best-fit trend
  lines by the classical touch-count rules.
- **Paper & live trading** — virtual account with real Binance prices, manual
  order ticket with live entry sync and one-click close, a strategy auto-bot,
  and a Binance live-execution engine (dry-run by default) with an emergency
  stop.
- **Backtesting & analytics** — candle-replay backtests with wick-accurate
  exits, persisted run history across all timeframes, and portfolio analytics
  computed from your *real* recorded trades (win rate, profit factor, Sharpe,
  Sortino, Calmar, expectancy, drawdown).
- **AI services** — market analyst, strategy selector, trade validator, risk
  manager, sentiment, backtest explainer, and pattern explanations, all routed
  through a single NVIDIA NIM endpoint (one `NVIDIA_API_KEY`), each degrading
  gracefully when unconfigured.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic |
| ML | PyTorch (+ CUDA), [Kronos](https://github.com/shiyu-coder/Kronos) OHLCV foundation model |
| Data | Binance public REST + WebSocket (`python-binance`) — keyless for market data |
| AI | NVIDIA NIM (OpenAI-compatible) — one key, multiple hosted models |
| DB | SQLite by default (zero config), PostgreSQL via `DATABASE_URL` |
| Frontend | React 19, TypeScript, TailwindCSS v4, Vite, lightweight-charts, lucide-react |

## Quick start

### Linux / macOS

```bash
git clone https://github.com/mittal122/AI-Trading-Platform.git
cd AI-Trading-Platform
./run.sh
```

First run bootstraps everything (Python venv + requirements, `.env` from
`.env.example`, `npm install`), then starts backend (:8000) + frontend (:5173).
You need a local clone of the [Kronos repo](https://github.com/shiyu-coder/Kronos)
with `KRONOS_PATH` pointing at it in `.env` — model weights download from
HuggingFace on first boot.

### Windows

Double-click `run.bat`. On a completely bare PC it installs everything itself:
Python 3.12 and Node.js (winget or direct installer), the Kronos repo
(downloaded from GitHub, no git needed), backend packages from
`requirements-windows.txt`, frontend packages, and auto-fills `.env`
(`KRONOS_PATH`, generated `JWT_SECRET`). Safe to re-run any time.

### Docker

```bash
cp .env.example .env   # set JWT_SECRET, POSTGRES_PASSWORD, KRONOS_PATH_HOST
docker compose up --build
```

Open **http://localhost** — nginx serves the frontend on :80 and proxies
`/api` to the backend; Postgres is internal-only. The default backend image
ships **without PyTorch/Kronos** (~840MB): the `/prediction` endpoint returns
503 and every other feature works normally. To enable AI price forecasts in
Docker, rebuild with `--build-arg INSTALL_KRONOS=true` (CPU-only torch,
~2.3GB) and set `KRONOS_ENABLED=true` in `.env`.

### Any PC, no source build (prebuilt images)

Images are published on Docker Hub
([`mittal122/ai-trading-backend`](https://hub.docker.com/r/mittal122/ai-trading-backend),
[`mittal122/ai-trading-frontend`](https://hub.docker.com/r/mittal122/ai-trading-frontend)),
so any machine with Docker installed can run the platform without Python,
Node, a GPU, or the Kronos repo:

```bash
git clone https://github.com/mittal122/AI-Trading-Platform.git
cd AI-Trading-Platform
cp .env.example .env       # then set JWT_SECRET and POSTGRES_PASSWORD
docker compose pull        # downloads prebuilt images — no build step
docker compose up -d
```

Open **http://localhost**. Generate the two secrets with
`python -c "import secrets; print(secrets.token_urlsafe(48))"` (or any long
random strings). `NVIDIA_API_KEY` is optional — AI explanations switch on
when it's set.

### Share it publicly (frontend on Vercel, backend on your PC)

The frontend can be hosted on Vercel while the backend stays on your own
machine behind an ngrok/Cloudflare tunnel — no port forwarding needed.
Full walkthrough: [docs/DEPLOY_VERCEL.md](docs/DEPLOY_VERCEL.md).

## Configuration

All settings live in `.env` (see `.env.example` for the full annotated list).
The important ones:

| Variable | Purpose |
|---|---|
| `KRONOS_PATH` | Local path to the Kronos model repo (required to boot) |
| `NVIDIA_API_KEY` | Enables all AI features (analysis, explanations, chat) |
| `BINANCE_API_KEY` / `BINANCE_SECRET` | Only for live trading — or enter keys on the Settings page instead (stored encrypted) |
| `JWT_SECRET` | Auth tokens + encryption key derivation (generate a long random value) |
| `DATABASE_URL` | Leave blank for SQLite; set `postgresql+asyncpg://...` for Postgres |
| `ADMIN_API_TOKEN` | Locks money-critical endpoints behind an `X-Admin-Token` header (set before exposing publicly) |

Market data needs **no API key** — Binance public endpoints power all charts,
scanners, and indicators.

## The screens

| Route | What it does |
|---|---|
| `/` Terminal | Market overview, watchlist + radar, live chart, order flow, movers, volume scanner |
| `/patterns` Analysis | Pattern detection + analysis tools + strategy signals on one chart workspace |
| `/patterns/dashboard` Patterns | Confirmed patterns across all timeframes at a glance |
| `/smc` SMC | Smart Money Concepts analysis with trade plans and layer toggles |
| `/smc/autotest` AutoTest | Hands-free SMC paper-trading loop with reversal flips |
| `/backtest` Backtest | Run/persist backtests, compare all timeframes, full run history |
| `/paper` Paper | Order ticket, strategy auto-bot, paper account, trade history |
| `/portfolio` Portfolio | Analytics from your real recorded trades + filterable history |
| `/settings` Settings | Binance keys (encrypted), admin token, environment reference |

## API

FastAPI serves everything under `http://localhost:8000/api/v1` — interactive
docs at `http://localhost:8000/docs`. Main groups: `/market`, `/indicator`,
`/strategy`, `/patterns`, `/analysis`, `/smc`, `/paper`, `/trading`,
`/backtest` (via `/trades`), `/portfolio`, `/ai`, `/prediction`, `/auth`,
`/billing`, `/settings`.

## Tests

```bash
PYTHONPATH=. .venv/bin/python tests/test_<name>.py    # single file
```

50+ test files cover strategies, indicators, exits, risk, SMC pipeline stages,
pattern detectors (per-pattern audit suites), paper trading, analytics, and
security hardening. Some tests hit live Binance data and require the backend
running on :8000.

## Project layout

```
backend/app/
  api/v1/          FastAPI routers (one per domain)
  core/            config (all thresholds live here — no magic numbers)
  db/              SQLAlchemy models, repositories, Alembic migrations
  schemas/         Pydantic schemas (data only, no logic)
  services/        strategy / indicator / smc / pattern / analysis / paper /
                   trading / risk / portfolio / ai — factory pattern throughout
frontend/src/
  pages/           one file per screen
  components/      shared UI (+ design system in design-system/STYLE_GUIDE.md)
  api/client.ts    typed API client
tests/             runnable-as-scripts test files
docs/              architecture and roadmap notes
```

## License

No license granted yet — all rights reserved by the author.
