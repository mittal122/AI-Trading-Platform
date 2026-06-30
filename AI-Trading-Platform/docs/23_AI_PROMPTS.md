# AI Trading Platform

# AI Prompt Library

---

# Purpose

This document contains all AI prompts used throughout the platform.

Instead of hardcoding prompts inside application code, every prompt should be designed here first and later stored in dedicated prompt files or a database.

The platform should support multiple AI providers, including:

- OpenAI
- Anthropic Claude
- Google Gemini
- Ollama
- NVIDIA NIM
- Other future LLM providers

Every provider should use the same prompt templates to ensure consistent behavior.

---

# AI Prompt Design Principles

Every prompt should:

- Produce deterministic outputs whenever possible.
- Explain its reasoning.
- Never fabricate market data.
- Never assume unavailable information.
- Return structured responses.
- Be concise but informative.
- Focus on trading and financial analysis.
- Avoid emotional language.
- Remain provider-independent.

---

# Prompt Categories

The platform will contain prompts for:

- Market Analysis
- Trade Explanation
- Portfolio Analysis
- Strategy Evaluation
- Risk Analysis
- Backtest Analysis
- News Analysis
- Sentiment Analysis
- AI Chat Assistant
- Strategy Optimization
- Trade Journal Review
- Performance Review

---

# Prompt 1 — Market Analysis

Purpose

Analyze the current market using technical indicators.

Input

- Price
- EMA
- RSI
- MACD
- ATR
- ADX
- VWAP
- Relative Volume
- Market Regime

Prompt

```
You are a professional quantitative trading analyst.

Analyze the supplied market indicators.

Determine:

- Current trend
- Momentum
- Volatility
- Market regime
- Overall market quality

Do not generate BUY or SELL recommendations.

Only explain the market condition.

Return structured JSON.
```

Expected Output

```json
{
    "trend":"Bearish",
    "strength":"Strong",
    "volatility":"Medium",
    "market_regime":"Trending",
    "summary":"Strong bearish trend with increasing momentum."
}
```

---

# Prompt 2 — Trade Explanation

Purpose

Explain why a trade occurred.

Prompt

```
Explain why this trade was executed.

Include

- Trend
- RSI
- MACD
- ADX
- Volume
- Confidence
- Stop Loss
- Take Profit

Explain the reasoning in simple language suitable for traders.
```

Expected Output

```json
{
    "summary":"BUY signal confirmed.",
    "reasons":[
        "...",
        "...",
        "..."
    ]
}
```

---

# Prompt 3 — Trade Review

Purpose

Evaluate a completed trade.

Prompt

```
Review this completed trade.

Identify:

- Good decisions
- Mistakes
- Risk quality
- Entry quality
- Exit quality
- Suggestions for improvement

Do not invent data.

Only analyze the supplied trade.
```

---

# Prompt 4 — Strategy Review

Purpose

Analyze an entire strategy.

Prompt

```
Analyze the supplied strategy statistics.

Evaluate:

- Win Rate
- Profit Factor
- Drawdown
- Risk
- Expectancy

Suggest improvements.

Avoid changing the trading rules unless justified.
```

---

# Prompt 5 — Portfolio Review

Purpose

Review overall portfolio health.

Prompt

```
Analyze this trading portfolio.

Evaluate:

- Exposure
- Diversification
- Cash allocation
- Risk concentration
- Open positions
- Drawdown

Provide recommendations without executing trades.
```

---

# Prompt 6 — Risk Analysis

Purpose

Evaluate trade risk.

Prompt

```
Evaluate the proposed trade.

Consider:

- Risk/Reward
- Volatility
- ATR
- Trend
- Confidence
- Portfolio exposure

Return

- Risk Level
- Suggested Position Size
- Warnings
```

---

# Prompt 7 — Backtest Review

Purpose

Review a completed backtest.

Prompt

```
Analyze this backtest report.

Explain:

- Overall performance
- Win rate
- Drawdown
- Strategy strengths
- Strategy weaknesses
- Improvement suggestions

Avoid making unsupported claims.
```

---

# Prompt 8 — Market Regime Analysis

Purpose

Classify market conditions.

Prompt

```
Using the supplied indicators, determine whether the market is:

- Strong Bull
- Weak Bull
- Strong Bear
- Weak Bear
- Sideways
- High Volatility
- Low Volatility

Explain the reasoning.
```

---

# Prompt 9 — News Analysis

Purpose

Analyze financial news.

Prompt

```
Summarize the supplied financial news.

Identify:

- Bullish events
- Bearish events
- Potential market impact
- Confidence level

Do not speculate beyond the available information.
```

---

# Prompt 10 — Sentiment Analysis

Purpose

Analyze social sentiment.

Prompt

```
Review the supplied social media and news content.

Determine:

- Bullish sentiment
- Bearish sentiment
- Neutral sentiment

Return confidence and supporting reasons.
```

---

# Prompt 11 — AI Chat Assistant

Purpose

Answer user questions.

Example Questions

```
Why did we buy BTC?

Why did we reject this trade?

Which strategy performed best?

What caused today's losses?

Explain today's market.

Should I reduce risk?
```

The assistant should answer using project data rather than making assumptions.

---

# Prompt 12 — Strategy Optimization

Purpose

Suggest strategy improvements.

Prompt

```
Review historical strategy performance.

Identify recurring weaknesses.

Suggest parameter improvements.

Do not automatically modify strategy logic.

Explain why each suggestion may improve results.
```

---

# Prompt 13 — Trade Journal Analysis

Purpose

Review historical trading behavior.

Prompt

```
Analyze the supplied trade journal.

Identify:

- Common mistakes
- Winning patterns
- Losing patterns
- Emotional behavior indicators
- Risk management issues

Provide recommendations.
```

---

# Prompt 14 — Daily Trading Report

Purpose

Generate a daily report.

Prompt

```
Generate today's trading summary.

Include:

- Trades executed
- Win rate
- Profit/Loss
- Portfolio value
- Best trade
- Worst trade
- Recommendations

Keep the report concise and professional.
```

---

# Prompt 15 — Weekly Performance Report

Purpose

Generate weekly analytics.

Prompt

```
Summarize this week's trading activity.

Include:

- Total trades
- Win rate
- Total return
- Drawdown
- Strategy performance
- Portfolio growth
- Suggested improvements
```

---

# Future Prompt Categories

Future prompt groups may include:

- AI Coach
- Portfolio Rebalancing
- Multi-Strategy Comparison
- Broker Diagnostics
- Infrastructure Monitoring
- DevOps Assistant
- Database Optimization
- Performance Tuning
- Cloud Cost Analysis

---

# Prompt Storage

Prompts should eventually move from documentation into a dedicated directory.

Example

```
backend/

app/

ai/

prompts/

market_analysis.md

trade_review.md

portfolio_review.md

risk_analysis.md

backtest_review.md

chat_assistant.md

news_analysis.md

strategy_optimizer.md
```

Prompt loading should be dynamic so they can be updated without changing application code.

---

# Prompt Versioning

Every prompt should include:

- Version
- Last Updated
- Author
- Purpose
- Expected Inputs
- Expected Outputs

This makes prompts maintainable as the AI system evolves.

---

# Long-Term Vision

The AI Prompt Library should become the central knowledge base for every AI-powered feature in the platform.

Rather than embedding prompts directly into services, all prompts should be maintained, versioned, tested, and documented in one place. This approach makes it easy to switch between AI providers, improve prompt quality over time, and ensure consistent behavior across all AI modules while keeping the application's business logic clean and independent of any specific language model.