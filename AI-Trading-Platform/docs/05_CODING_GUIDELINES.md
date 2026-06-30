# AI Trading Platform

# Coding Guidelines

---

# Purpose

This document defines the coding standards for the entire project.

Every contributor (human or AI) must follow these rules.

The goal is to keep the project:

- Clean
- Consistent
- Modular
- Maintainable
- Scalable
- Production Ready

These rules take priority over personal coding style.

---

# Project Philosophy

The project should resemble a professional software product rather than a collection of scripts.

Every new feature should be:

- Reusable
- Independent
- Testable
- Easy to understand
- Easy to extend

Always think about long-term maintainability.

---

# Architecture Rules

Always respect the existing architecture.

Never bypass the service layer.

The standard flow is

Market

↓

Indicators

↓

Strategy

↓

Signal Score

↓

Trade Decision

↓

Trading Engine

↓

Trade Manager

↓

Execution

↓

Portfolio

↓

Recorder

↓

Backtest

Do not move logic into incorrect layers.

---

# SOLID Principles

Follow SOLID whenever possible.

## Single Responsibility Principle

Each class should have one responsibility.

Example

IndicatorService

Responsible only for calculating indicators.

Not responsible for trading decisions.

---

TradeManager

Responsible only for exit logic.

Not indicator calculations.

---

Portfolio

Responsible only for balances and positions.

Not signal generation.

---

## Open / Closed Principle

Prefer extending the system instead of modifying existing behavior.

Example

Good

Add

EMAStrategy

instead of modifying

RSIStrategy

to behave differently.

---

## Liskov Substitution Principle

Every strategy must inherit

BaseStrategy

Every execution engine must inherit

BaseExecutionEngine

Factories should work without modification.

---

## Interface Segregation Principle

Small focused interfaces.

Avoid giant classes.

---

## Dependency Inversion Principle

Depend on abstractions.

Not concrete implementations.

Use Factory classes.

---

# Folder Structure

Every module should live inside its proper folder.

Example

services/

strategy/

execution/

portfolio/

trade/

backtest/

market/

position/

schemas/

tests/

Never place unrelated files together.

---

# Naming Convention

Use descriptive names.

Good

calculate_position_size()

generate_signal()

should_exit()

record_trade()

calculate_indicators()

Bad

calc()

run()

test()

value()

---

Variables

Good

current_price

entry_price

stop_loss

take_profit

account_equity

Bad

a

b

temp

data1

value2

---

# Function Size

Prefer small functions.

Ideal

10–40 lines

Acceptable

50–80 lines

Avoid

200+ line functions.

Break large functions into helper methods.

---

# Class Size

Classes should stay focused.

If a class grows beyond approximately

300–500 lines

consider splitting it.

---

# Code Formatting

Use Black formatting style.

One argument per line when appropriate.

Example

Good

execution = self.execution.execute(
    side=OrderSide.BUY,
    price=price,
    quantity=quantity,
)

Avoid long unreadable lines.

---

# Comments

Write comments that explain

WHY

not

WHAT.

Bad

# Increment i

i += 1

Good

# Skip trade because confidence is too low

---

# Magic Numbers

Avoid hardcoded values.

Bad

if confidence > 73:

Good

MIN_CONFIDENCE = 70

if confidence > MIN_CONFIDENCE:

Store configurable values in constants or configuration files.

---

# Configuration

Do not hardcode values inside business logic.

Examples

Risk %

ATR Multiplier

Confidence Threshold

Volume Threshold

ADX Threshold

Should eventually come from configuration.

---

# Error Handling

Handle failures gracefully.

Avoid

Bare except statements.

Good

try:

...

except Exception as e:

log error

return meaningful response

---

# Logging

Prefer logging over print.

Current

print()

Future

Python logging module.

Eventually

Structured logging

JSON logs

Log levels

INFO

WARNING

ERROR

CRITICAL

---

# Testing

Every major module should have tests.

Examples

test_indicator_service.py

test_trade_manager.py

test_backtest_service.py

test_execution_engine.py

test_portfolio.py

Tests should remain simple and reproducible.

---

# Code Reuse

Never duplicate business logic.

Example

If RSI is calculated inside IndicatorService

Do NOT calculate RSI again inside Strategy.

Always reuse existing services.

---

# Factory Pattern

Continue using Factory classes.

Good

StrategyFactory

ExecutionFactory

PortfolioFactory

PositionFactory

BacktestFactory

Future factories

BrokerFactory

AIProviderFactory

NotificationFactory

Avoid creating objects directly throughout the codebase.

---

# Dependency Injection

Prefer dependency injection over creating objects inside methods.

Good

Pass dependencies through constructors when appropriate.

This improves testing.

---

# Performance

Avoid unnecessary calculations.

Example

Bad

Calculate indicators five times.

Good

Calculate once.

Reuse results.

---

# Documentation

Every public class should include a short description.

Every complex function should explain

Purpose

Parameters

Returns

Important assumptions

---

# Git Workflow

Every meaningful feature should be committed separately.

Examples

feat(strategy): improve RSI confirmation

feat(indicators): add ADX calculation

feat(risk): implement trailing stop

fix(backtest): correct portfolio valuation

Avoid giant commits.

---

# Branch Strategy

Recommended

main

Stable production branch.

develop

Current development.

feature/...

Individual features.

Examples

feature/market-regime

feature/trailing-stop

feature/paper-trading

---

# Pull Requests

Every completed feature should include

What changed

Why it changed

Testing performed

Future improvements

Even when working alone, documenting these points keeps the project organized.

---

# Future Refactoring

Do not prematurely optimize.

Write clean code first.

Refactor only when

Duplication appears

Complexity increases

Architecture becomes unclear

Performance issues are confirmed

---

# AI Development Rules

Future AI assistants should

Read existing code before writing new code.

Reuse existing services.

Avoid duplicate implementations.

Maintain naming consistency.

Follow the architecture.

Write modular code.

Write testable code.

Do not remove working functionality unless replacing it with a better implementation.

---

# Final Principle

The objective is not just to make the project work.

The objective is to build a professional, enterprise-grade AI trading platform that remains understandable, maintainable, and extensible for years to come.

Every line of code should move the project closer to that goal.