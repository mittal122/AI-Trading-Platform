"""
Phase 5 — AI Integration tests (NVIDIA NIM, multi-model).

All 7 services route through NVIDIA NIM's single OpenAI-compatible endpoint,
each addressed by its own model slug (see backend/app/core/ai_provider_config.py).
One API key (NVIDIA_API_KEY) covers all of them — tests all skip together if unset.

Run: PYTHONPATH=. NVIDIA_API_KEY=<key> .venv/bin/python tests/test_ai_service.py
"""

import os
import sys

from backend.app.schemas.ai import (
    BacktestExplainRequest,
    ChatMessage,
    ChatRequest,
    MarketAnalysisRequest,
    RiskReviewRequest,
    SentimentRequest,
    StrategySelectionRequest,
    TradeValidationRequest,
)
from backend.app.services.ai.ai_factory import AIFactory


def _skip(env_var: str, service_name: str) -> bool:
    if not os.getenv(env_var):
        print(f"\n--- {service_name} ---\n{env_var} not set — skipping")
        return True
    return False


def test_market_analyst():
    if _skip("NVIDIA_API_KEY", "MarketAnalyst (nemotron-3-super)"):
        return True
    print("\n--- MarketAnalyst (nemotron-3-super) ---")
    service = AIFactory.get_market_analyst()
    req = MarketAnalysisRequest(
        symbol="BTCUSDT",
        interval="5m",
        regime="STRONG_BULL",
        price=65000.0,
        rsi=62.5,
        macd=120.3,
        histogram=45.1,
        atr=850.0,
        bb_upper=66200.0,
        bb_lower=63800.0,
        vwap=64750.0,
    )
    result = service.analyze(req)
    print(f"Symbol    : {result.symbol}")
    print(f"Sentiment : {result.sentiment}")
    print(f"Analysis  : {result.analysis}")
    assert result.sentiment in ("BULLISH", "BEARISH", "NEUTRAL")
    print("PASS")


def test_strategy_selector():
    if _skip("NVIDIA_API_KEY", "StrategySelector (glm-5.1)"):
        return True
    print("\n--- StrategySelector (glm-5.1) ---")
    service = AIFactory.get_strategy_selector()
    req = StrategySelectionRequest(
        regime="STRONG_BULL",
        volatility="NORMAL",
        available_strategies=["rsi", "ema", "macd", "breakout", "supertrend"],
        recent_performance={"rsi": 12.4, "ema": 8.1, "macd": 15.2, "breakout": 6.3},
    )
    result = service.select(req)
    print(f"Recommended : {result.recommended_strategy}")
    print(f"Confidence  : {result.confidence:.2f}")
    assert result.recommended_strategy in req.available_strategies
    assert 0.0 <= result.confidence <= 1.0
    print("PASS")


def test_trade_validator():
    if _skip("NVIDIA_API_KEY", "TradeValidator (deepseek-v4-pro)"):
        return True
    print("\n--- TradeValidator (deepseek-v4-pro) ---")
    service = AIFactory.get_trade_validator()
    req = TradeValidationRequest(
        symbol="BTCUSDT",
        direction="BUY",
        entry=65000.0,
        stop_loss=64000.0,
        take_profit=67000.0,
        risk_reward=2.0,
        confidence=0.72,
        regime="STRONG_BULL",
        quality_grade="B",
        reasons=[
            "RSI(14) = 62.5 — momentum strong",
            "MACD crossover bullish",
            "Price above VWAP",
            "ADX = 28 — trend confirmed",
        ],
    )
    result = service.validate(req)
    print(f"Decision    : {result.decision}")
    print(f"Reason      : {result.reason}")
    assert result.decision in ("APPROVE", "REJECT")
    print("PASS")


def test_risk_manager():
    if _skip("NVIDIA_API_KEY", "AIRiskManager (glm-5.1)"):
        return True
    print("\n--- AIRiskManager (glm-5.1) ---")
    service = AIFactory.get_risk_manager()
    req = RiskReviewRequest(
        symbol="BTCUSDT",
        direction="BUY",
        entry_price=63000.0,
        current_price=65000.0,
        stop_loss=62000.0,
        take_profit=67000.0,
        position_size=0.1,
        unrealized_pnl=200.0,
        equity=10000.0,
        candles_held=8,
    )
    result = service.review(req)
    print(f"Action    : {result.action}")
    print(f"Reasoning : {result.reasoning}")
    assert result.action in ("HOLD", "REDUCE", "CLOSE", "TIGHTEN_STOP")
    print("PASS")


def test_sentiment_analyzer():
    if _skip("NVIDIA_API_KEY", "SentimentAnalyzer (minimax-m3)"):
        return True
    print("\n--- SentimentAnalyzer (minimax-m3) ---")
    service = AIFactory.get_sentiment_analyzer()
    req = SentimentRequest(
        symbol="BTCUSDT",
        headlines=[
            "Bitcoin hits new ATH as institutional demand surges",
            "BlackRock BTC ETF sees record inflows",
            "Federal Reserve signals rate cuts ahead",
            "Crypto markets rally on positive macro data",
        ],
    )
    result = service.analyze(req)
    print(f"Sentiment : {result.sentiment}")
    print(f"Score     : {result.score:.2f}")
    assert result.sentiment in ("BULLISH", "BEARISH", "NEUTRAL")
    assert -1.0 <= result.score <= 1.0
    print("PASS")


def test_chat_assistant():
    if _skip("NVIDIA_API_KEY", "ChatAssistant (kimi-k2.5)"):
        return True
    print("\n--- ChatAssistant (kimi-k2.5) ---")
    service = AIFactory.get_chat_assistant()
    req = ChatRequest(
        message="What does a high RSI reading of 75 mean for my BTC position?",
        history=[
            ChatMessage(role="user", content="I'm trading BTCUSDT on the 5m chart."),
            ChatMessage(role="assistant", content="Got it — BTCUSDT 5m. What would you like to know?"),
        ],
    )
    result = service.chat(req)
    print(f"Reply: {result.reply[:200]}...")
    assert len(result.reply) > 10
    print("PASS")


def test_backtest_explainer():
    if _skip("NVIDIA_API_KEY", "BacktestExplainer (minimax-m2.7)"):
        return True
    print("\n--- BacktestExplainer (minimax-m2.7) ---")
    service = AIFactory.get_backtest_explainer()
    req = BacktestExplainRequest(
        strategy="rsi",
        symbol="BTCUSDT",
        interval="5m",
        total_return=8.5,
        total_trades=42,
        win_rate=58.3,
        profit_factor=1.62,
        sharpe_ratio=1.21,
        sortino_ratio=1.45,
        calmar_ratio=0.9,
        max_drawdown=4.2,
        expectancy=2.31,
    )
    result = service.explain(req)
    print(f"Summary    : {result.summary}")
    print(f"Strengths  : {result.strengths}")
    print(f"Weaknesses : {result.weaknesses}")
    print(f"Suggestion : {result.suggestion}")
    assert len(result.summary) > 5
    print("PASS")


if __name__ == "__main__":
    tests = [
        test_market_analyst,
        test_strategy_selector,
        test_trade_validator,
        test_risk_manager,
        test_sentiment_analyzer,
        test_chat_assistant,
        test_backtest_explainer,
    ]

    passed = 0
    failed = 0
    skipped = 0
    for t in tests:
        try:
            result = t()
            if result is True:
                skipped += 1
            else:
                passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1

    print(f"\n========== RESULTS: {passed} passed, {failed} failed, {skipped} skipped ==========")
    sys.exit(0 if failed == 0 else 1)
