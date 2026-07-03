from concurrent.futures import ThreadPoolExecutor

from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.trading_signal import SignalDirection, TradingSignal
from backend.app.services.market_service import MarketService
from backend.app.services.strategy.eta_estimator import TimeToTargetEstimator
from backend.app.services.strategy.strategy_factory import StrategyFactory


class SignalScanner:
    """
    Batch signal generation — the auto-scan layer on top of individual
    strategies. Two modes:
      - scan_all_strategies: every registered strategy, one symbol/interval —
        "what does every strategy think about this market right now?"
      - scan_timeframes: one strategy, every timeframe — "which timeframe
        does this strategy actually work on right now?"

    Each unit of work (one strategy, or one timeframe) runs independently and
    is wrapped so a single failure (bad data, strategy bug) doesn't take down
    the rest of the batch — it comes back as a FLAT signal with `error` set.
    Units run concurrently since a couple of strategies (Turtle) are slow
    enough that running 8 of them serially would make the scan feel broken.
    """

    def __init__(self):
        self.market = MarketService()
        self.eta_estimator = TimeToTargetEstimator()

    def scan_all_strategies(
        self,
        symbol: str,
        interval: str,
        limit: int = 250,
    ) -> list[TradingSignal]:
        market = self.market.get_market_data(symbol=symbol, interval=interval, limit=limit)
        strategy_keys = StrategyFactory.list_strategies()

        with ThreadPoolExecutor(max_workers=strategy_config.SCAN_MAX_WORKERS) as pool:
            futures = [
                pool.submit(self._run_strategy_key, key, market, symbol, interval)
                for key in strategy_keys
            ]
            return [f.result() for f in futures]

    def scan_timeframes(
        self,
        strategy: str,
        symbol: str,
        intervals: list[str] = None,
        limit: int = 250,
    ) -> list[TradingSignal]:
        intervals = intervals or strategy_config.SCAN_DEFAULT_INTERVALS

        with ThreadPoolExecutor(max_workers=strategy_config.SCAN_MAX_WORKERS) as pool:
            futures = [
                pool.submit(self._run_timeframe, strategy, symbol, tf, limit)
                for tf in intervals
            ]
            return [f.result() for f in futures]

    # ------------------------------------------------------------------

    def _run_strategy_key(self, key: str, market, symbol: str, interval: str) -> TradingSignal:
        try:
            engine = StrategyFactory.get_strategy(key)
            signal = engine.generate_signal(market=market, symbol=symbol, interval=interval)
            return self._attach_eta(signal, interval)
        except Exception as exc:
            return self._error_signal(key, symbol, interval, str(exc))

    def _run_timeframe(self, strategy: str, symbol: str, interval: str, limit: int) -> TradingSignal:
        try:
            engine = StrategyFactory.get_strategy(strategy)
            market = self.market.get_market_data(symbol=symbol, interval=interval, limit=limit)
            signal = engine.generate_signal(market=market, symbol=symbol, interval=interval)
            return self._attach_eta(signal, interval)
        except Exception as exc:
            return self._error_signal(strategy, symbol, interval, str(exc))

    def _attach_eta(self, signal: TradingSignal, interval: str) -> TradingSignal:
        if signal.direction == SignalDirection.FLAT:
            return signal
        eta_candles, eta_display = self.eta_estimator.estimate(
            entry=signal.entry,
            take_profit=signal.take_profit,
            atr=signal.atr or 0.0,
            interval=interval,
            regime=signal.regime,
        )
        return signal.model_copy(update={"eta_candles": eta_candles, "eta_display": eta_display})

    @staticmethod
    def _error_signal(strategy: str, symbol: str, interval: str, error: str) -> TradingSignal:
        return TradingSignal(
            strategy=strategy, symbol=symbol, interval=interval, timestamp="",
            direction=SignalDirection.FLAT, confidence=0.0, entry=0.0,
            stop_loss=0.0, take_profit=0.0, risk_reward=0.0,
            reasons=[f"Scan failed: {error}"], error=error,
        )
