# AI Trading Platform

# AI Context

---

# Purpose

This document provides context specifically for AI assistants working on this project.

It explains the project's philosophy, development approach, architectural decisions, coding expectations, and long-term vision.

Before making any code changes, every AI assistant should read the following documents in order:

1. 00_PROJECT_OVERVIEW.md
2. 01_ARCHITECTURE.md
3. 02_COMPLETED_FEATURES.md
4. 03_ROADMAP.md
5. 04_CURRENT_WORK.md
6. 05_CODING_GUIDELINES.md
7. 06_BACKEND_STRUCTURE.md
8. 07_PROJECT_STRUCTURE.md
9. 08_NEXT_TASKS.md
10. 09_BACKTEST_ENGINE.md
11. 10_STRATEGY_ENGINE.md
12. 11_AI_SYSTEM.md
13. 12_AI_CONTEXT.md

Only after understanding these documents should development begin.

---

# Project Goal

This project is NOT intended to become a simple cryptocurrency trading bot.

The objective is to build a complete enterprise-grade AI-powered algorithmic trading platform.

The final system should support:

- Professional backtesting
- Paper trading
- Live trading
- Multiple brokers
- Portfolio management
- AI-assisted trading
- Multi-user SaaS deployment
- Institutional-grade analytics

Every implementation should move the project closer to this vision.

---

# Development Philosophy

The project is being developed incrementally.

Instead of rapidly adding features, the priority is to build a strong foundation.

Each layer should be completed before the next layer begins.

Quality is preferred over speed.

Correct architecture is preferred over shortcuts.

---

# Current Development Phase

The infrastructure has already been built.

Current work focuses on improving the intelligence of the trading system.

The highest priorities are:

- Better market understanding
- Better trade quality
- Better confidence calculation
- Better risk management

Infrastructure work should only be performed when necessary.

---

# How the Project Works

The project follows a layered architecture.

```
Market Data

↓

Indicator Service

↓

Strategy Engine

↓

Signal Score

↓

Trade Decision

↓

Trading Signal

↓

Trading Engine

↓

Execution Engine

↓

Portfolio

↓

Trade Recorder

↓

Backtesting
```

Every new feature should fit naturally into this pipeline.

Do not bypass existing layers.

---

# Important Design Principles

Business logic should remain inside services.

Schemas should only describe data.

Factories should create objects.

Trading Engine should execute signals.

Strategy Engine should generate signals.

Indicator Service should calculate indicators.

Portfolio should manage balances.

Trade Manager should manage exits.

Backtesting should reuse every existing service.

---

# Preferred Development Style

When implementing new functionality:

1. Understand the existing architecture.
2. Reuse existing modules whenever possible.
3. Avoid duplicate logic.
4. Keep classes focused.
5. Keep methods small.
6. Write modular code.
7. Preserve readability.
8. Keep future extensibility in mind.

---

# Never Do These Things

Do not place indicator calculations inside strategies.

Do not place trading logic inside schemas.

Do not duplicate calculations already available in IndicatorService.

Do not hardcode configuration values that should eventually become configurable.

Do not bypass Factory classes.

Do not write large monolithic classes.

Do not break existing architecture simply because another implementation appears easier.

---

# Code Quality Expectations

Every new feature should be:

- Modular
- Reusable
- Testable
- Readable
- Extensible
- Well documented

Avoid unnecessary complexity.

Avoid clever code that is difficult to maintain.

---

# Existing Progress

The following systems already exist:

- Market Service
- Indicator Service
- Strategy Framework
- RSI Strategy
- Signal Score
- Trade Decision
- Trading Engine
- Position Engine
- Execution Engine
- Portfolio Engine
- Trade Manager
- Trade Recorder
- Backtesting Engine

Whenever possible, extend these components instead of replacing them.

---

# Future Direction

The project will eventually include:

- Market Regime Detection
- Dynamic Signal Weighting
- Advanced Risk Management
- Multiple Trading Strategies
- Paper Trading
- Live Trading
- AI Modules
- Portfolio Analytics
- SaaS Dashboard

Development should follow this order unless explicitly instructed otherwise.

---

# AI Responsibilities

When writing code:

Understand the existing implementation before modifying it.

Prefer improving existing modules over creating redundant ones.

Follow the documented architecture.

Explain architectural decisions when introducing new modules.

Ensure that new code integrates cleanly with the rest of the project.

When appropriate, recommend improvements that increase maintainability, scalability, or performance.

---

# Communication Style

When proposing changes:

- Clearly explain why the change is needed.
- Mention which files will be modified.
- Explain how the change affects the overall architecture.
- Avoid making unnecessary changes outside the current scope.

If additional work is required in another module, explicitly state which file should be updated and why.

---

# Long-Term Vision

The final platform should resemble a professional quantitative trading system rather than a collection of independent scripts.

It should be capable of supporting:

- Multiple exchanges
- Multiple brokers
- Multiple strategies
- AI-assisted analysis
- Institutional risk management
- Enterprise reporting
- Cloud deployment
- Multi-user SaaS operation

The architecture should remain clean enough that new features can be added without major refactoring.

---

# Final Instructions for Future AI Assistants

Before writing any code:

- Read the documentation.
- Understand the architecture.
- Check the current development phase.
- Review the active task list.
- Reuse existing services.
- Follow SOLID principles.
- Maintain the modular design.

When in doubt, choose the solution that improves long-term maintainability over the one that is merely faster to implement.

The objective is not only to make the software work today, but to build a platform that can continue evolving for many years while remaining understandable, scalable, and production-ready.