from backend.app.services.ai.analysis_explainer import AnalysisExplainer
from backend.app.services.ai.backtest_explainer import BacktestExplainer
from backend.app.services.ai.chat_assistant import ChatAssistant
from backend.app.services.ai.market_analyst import MarketAnalyst
from backend.app.services.ai.pattern_explainer import PatternExplainer
from backend.app.services.ai.risk_manager import AIRiskManager
from backend.app.services.ai.sentiment_analyzer import SentimentAnalyzer
from backend.app.services.ai.strategy_selector import StrategySelector
from backend.app.services.ai.trade_validator import TradeValidator


class AIFactory:

    @staticmethod
    def get_market_analyst() -> MarketAnalyst:
        return MarketAnalyst()

    @staticmethod
    def get_strategy_selector() -> StrategySelector:
        return StrategySelector()

    @staticmethod
    def get_trade_validator() -> TradeValidator:
        return TradeValidator()

    @staticmethod
    def get_risk_manager() -> AIRiskManager:
        return AIRiskManager()

    @staticmethod
    def get_sentiment_analyzer() -> SentimentAnalyzer:
        return SentimentAnalyzer()

    @staticmethod
    def get_chat_assistant() -> ChatAssistant:
        return ChatAssistant()

    @staticmethod
    def get_backtest_explainer() -> BacktestExplainer:
        return BacktestExplainer()

    @staticmethod
    def get_pattern_explainer() -> PatternExplainer:
        return PatternExplainer()

    @staticmethod
    def get_analysis_explainer() -> AnalysisExplainer:
        return AnalysisExplainer()
