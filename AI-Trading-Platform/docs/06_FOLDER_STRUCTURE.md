# AI Trading Platform

# Complete Project Structure

---

# Purpose

This document explains the complete directory structure of the project.

It describes the purpose of every folder, every major module, and where future development should take place.

This file should always reflect the actual project structure.

---

# Project Root

```
AI-Trading-Platform/

│

├── backend/
├── frontend/
├── docs/
├── tests/
├── scripts/
├── docker/
├── deployment/
├── .github/
├── requirements.txt
├── README.md
├── .env
├── .gitignore

```

---

# backend/

```
backend/

└── app/

    ├── api/
    ├── config/
    ├── schemas/
    ├── services/
    ├── utils/
    ├── database/
    ├── middleware/
    ├── websocket/
    ├── dependencies/

```

Backend contains the complete business logic of the application.

---

# backend/app/api/

Purpose

Contains REST API endpoints.

Example

```
api/

market.py

strategy.py

portfolio.py

backtest.py

execution.py

broker.py

```

Responsibilities

- Receive HTTP requests
- Validate input
- Call services
- Return responses

No business logic should exist here.

---

# backend/app/config/

Purpose

Contains configuration.

Examples

```
config/

settings.py

constants.py

logging.py

environment.py

```

Stores

- API Keys
- Risk %
- Exchange URLs
- Environment variables
- Constants

---

# backend/app/schemas/

Purpose

Contains all data models.

Current schemas

```
execution.py

strategy.py

trading_signal.py

portfolio.py

position.py

trade.py

backtest.py

```

Responsibilities

- Request models
- Response models
- Validation models

No business logic.

---

# backend/app/services/

This is the heart of the platform.

Everything important happens here.

```
services/

market/

strategy/

execution/

portfolio/

position/

trade/

backtest/

```

---

# services/market/

Purpose

Download market data.

Future

```
market/

market_service.py

exchange_factory.py

binance_service.py

bybit_service.py

mt5_service.py

```

---

# services/strategy/

Purpose

Generate trading signals.

Current

```
strategy/

base_strategy.py

strategy_factory.py

rsi_strategy.py

signal_score.py

trade_decision.py

```

Future

```
ema_strategy.py

macd_strategy.py

supertrend_strategy.py

breakout_strategy.py

swing_strategy.py

scalping_strategy.py

ai_strategy.py

```

---

# services/indicator/

(Currently IndicatorService exists as a single service.)

Future structure

```
indicator/

indicator_service.py

trend_indicator.py

momentum_indicator.py

volume_indicator.py

volatility_indicator.py

market_regime.py

```

---

# services/execution/

Purpose

Trade execution.

```
execution/

base_execution_engine.py

simple_execution_engine.py

execution_factory.py

```

Future

```
commission.py

slippage.py

limit_orders.py

market_orders.py

```

---

# services/position/

Purpose

Position sizing.

```
position/

base_position_engine.py

simple_position_engine.py

position_factory.py

```

Future

```
kelly_position.py

atr_position.py

fixed_position.py

```

---

# services/portfolio/

Purpose

Portfolio management.

```
portfolio/

base_portfolio_engine.py

simple_portfolio_engine.py

portfolio_factory.py

```

Tracks

- Cash
- Equity
- Positions
- Returns

---

# services/trade/

Purpose

Trade lifecycle.

Current

```
trade/

trade_manager.py

trade_recorder.py

trade_state.py

```

Future

```
risk_manager.py

trailing_stop.py

break_even.py

partial_exit.py

```

---

# services/backtest/

Purpose

Historical simulation.

```
backtest/

simple_backtest.py

backtest_factory.py

```

Future

```
walk_forward.py

optimization.py

monte_carlo.py

parameter_search.py

```

---

# services/ai/

Future

```
ai/

market_analysis.py

strategy_selector.py

portfolio_ai.py

risk_ai.py

chat_assistant.py

news_analysis.py

```

---

# services/broker/

Future

```
broker/

broker_factory.py

binance.py

bybit.py

mt5.py

oanda.py

ibkr.py

```

---

# services/paper_trading/

Future

```
paper_trading/

paper_account.py

paper_execution.py

paper_portfolio.py

```

---

# services/live_trading/

Future

```
live_trading/

live_engine.py

live_orders.py

order_monitor.py

```

---

# services/analytics/

Future

```
analytics/

performance.py

drawdown.py

sharpe.py

sortino.py

calmar.py

```

---

# services/reporting/

Future

```
reporting/

pdf_report.py

csv_report.py

excel_report.py

trade_summary.py

```

---

# backend/app/utils/

Purpose

Reusable helper functions.

Examples

```
utils/

logger.py

math_utils.py

date_utils.py

validation.py

formatter.py

```

---

# backend/app/database/

Future

```
database/

models/

repositories/

connection.py

migration.py

```

---

# backend/app/middleware/

Future

```
middleware/

authentication.py

authorization.py

logging.py

rate_limit.py

```

---

# backend/app/websocket/

Future

```
websocket/

market_stream.py

trade_stream.py

portfolio_stream.py

```

---

# backend/app/dependencies/

Future

```
dependencies/

broker.py

database.py

security.py

```

---

# frontend/

(Currently planned)

```
frontend/

src/

components/

pages/

hooks/

services/

context/

layouts/

assets/

styles/

```

---

# tests/

Purpose

Contains unit tests.

Current

```
tests/

test_backtest_service.py

test_indicator_service.py

test_signal_score.py

test_trade_decision.py

test_trading_engine.py

```

Future

```
test_market_regime.py

test_trailing_stop.py

test_ai_strategy.py

test_live_trading.py

test_portfolio.py

```

---

# docs/

Project documentation.

Current

```
00_PROJECT_OVERVIEW.md

01_ARCHITECTURE.md

02_COMPLETED_FEATURES.md

03_ROADMAP.md

04_CURRENT_WORK.md

05_CODING_GUIDELINES.md

06_BACKEND_STRUCTURE.md

07_PROJECT_STRUCTURE.md

```

Future

```
API_REFERENCE.md

DEPLOYMENT.md

DATABASE.md

CONTRIBUTING.md

CHANGELOG.md

```

---

# scripts/

Utility scripts.

Examples

```
scripts/

download_data.py

seed_database.py

cleanup.py

benchmark.py

```

---

# docker/

Deployment files.

```
docker/

Dockerfile.backend

Dockerfile.frontend

docker-compose.yml

```

---

# deployment/

Infrastructure.

Future

```
deployment/

kubernetes/

terraform/

helm/

nginx/

```

---

# .github/

GitHub automation.

```
.github/

workflows/

issue_templates/

pull_request_templates/

```

Future CI/CD

- Testing
- Linting
- Docker Build
- Deployment
- Security Scans

---

# Project Growth Strategy

The project is expected to grow significantly.

New functionality should be added by creating new services rather than increasing the size of existing ones.

A service should generally remain focused on one responsibility.

As the project evolves, new modules should naturally fit into the architecture without requiring major restructuring.

---

# Final Principle

The directory structure is intentionally modular.

When adding a feature, always ask:

1. Does an existing module already own this responsibility?
2. Can the feature extend an existing service?
3. If not, should a new service be created?

Maintaining a clean project structure is more important than minimizing the number of files.

The long-term goal is an enterprise-grade AI trading platform with a backend architecture that remains organized, scalable, and easy to maintain regardless of project size.