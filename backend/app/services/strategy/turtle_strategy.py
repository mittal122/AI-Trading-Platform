from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.trading_signal import SignalDirection, TradingSignal
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.market_regime import MarketRegime


class TurtleStrategy(BaseStrategy):
    """
    Turtle Trading System (Richard Dennis-style dual breakout).

    System 1: 20-bar breakout, filtered — skipped if the *previous* System-1
    breakout in the same direction was a winner (mean-reversion after a win),
    unless price also breaks the (unfiltered) 55-bar channel as a failsafe.
    System 2: 55-bar breakout, always taken, no filter.

    N (the Turtle "volatility unit") is ATR over TURTLE_N_PERIOD. Stops/targets
    are N-multiples, independent of the regime-based DynamicATR table other
    strategies use.
    """

    def __init__(self):
        self.indicators = IndicatorService()
        self.market_regime = MarketRegime()

    def generate_signal(
        self,
        market,
        symbol: str,
        interval: str,
    ) -> TradingSignal:

        cfg = strategy_config
        min_bars = max(cfg.TURTLE_N_PERIOD, cfg.TURTLE_SYS2_ENTRY_PERIOD) + 10

        if len(market) < min_bars:
            return self._flat_signal(
                symbol, interval, market,
                reason=f"Insufficient history for Turtle (need {min_bars}+ candles).",
            )

        base_values = self.indicators.calculate_from_dataframe(market)
        regime = self.market_regime.detect(base_values)
        price = base_values["price"]

        n_value = self.indicators.calculate_atr_at_period(market, cfg.TURTLE_N_PERIOD)
        if not n_value or n_value <= 0:
            return self._flat_signal(symbol, interval, market, reason="ATR(N) unavailable or zero.")

        unit_size = (cfg.TURTLE_RISK_PERCENT / 100 * 10000) / (2 * n_value)  # informational, equity=10000 reference

        active_system = cfg.TURTLE_ACTIVE_SYSTEM
        entry_period = cfg.TURTLE_SYS1_ENTRY_PERIOD if active_system == 1 else cfg.TURTLE_SYS2_ENTRY_PERIOD

        sys1_high, sys1_low = self.indicators.rolling_channel(market, cfg.TURTLE_SYS1_ENTRY_PERIOD)
        sys2_high, sys2_low = self.indicators.rolling_channel(market, cfg.TURTLE_SYS2_ENTRY_PERIOD)

        direction = SignalDirection.FLAT
        confidence = 0.0
        reasons: list[str] = []
        filtered = False

        if active_system == 1:
            if price > sys1_high:
                last_was_loss = self._last_sys1_breakout_was_loss(market, entry_period, cfg.TURTLE_SYS1_EXIT_PERIOD, "BUY")
                if last_was_loss:
                    direction = SignalDirection.BUY
                    confidence = min(88.0, 65.0 + min(23.0, (price - sys1_high) / n_value * 15))
                    reasons.append(f"Turtle S1 BUY: broke {entry_period}-bar high ${sys1_high:.0f}. Last breakout was a loss — signal taken.")
                elif price > sys2_high:
                    direction = SignalDirection.BUY
                    confidence = min(85.0, 70.0 + min(15.0, (price - sys2_high) / n_value * 15))
                    reasons.append(f"Turtle S1 failsafe BUY: last breakout won, but {cfg.TURTLE_SYS2_ENTRY_PERIOD}-bar high also broken.")
                else:
                    filtered = True
                    reasons.append(f"Turtle S1 FILTERED: broke {entry_period}-bar high ${sys1_high:.0f} but last breakout was a WINNER — waiting for next losing breakout.")
            elif price < sys1_low:
                last_was_loss = self._last_sys1_breakout_was_loss(market, entry_period, cfg.TURTLE_SYS1_EXIT_PERIOD, "SELL")
                if last_was_loss:
                    direction = SignalDirection.SELL
                    confidence = min(88.0, 65.0 + min(23.0, (sys1_low - price) / n_value * 15))
                    reasons.append(f"Turtle S1 SELL: broke {entry_period}-bar low ${sys1_low:.0f}. Last breakout was a loss — signal taken.")
                elif price < sys2_low:
                    direction = SignalDirection.SELL
                    confidence = min(85.0, 70.0 + min(15.0, (sys2_low - price) / n_value * 15))
                    reasons.append(f"Turtle S1 failsafe SELL: last breakout won, but {cfg.TURTLE_SYS2_ENTRY_PERIOD}-bar low also broken.")
                else:
                    filtered = True
                    reasons.append(f"Turtle S1 FILTERED: broke {entry_period}-bar low ${sys1_low:.0f} but last breakout was a WINNER — waiting.")
            else:
                reasons.append(f"Turtle S1: inside {entry_period}-bar range [${sys1_low:.0f}-${sys1_high:.0f}]. N={n_value:.0f}, unit={unit_size:.4f}")
        else:
            if price > sys2_high:
                direction = SignalDirection.BUY
                confidence = min(92.0, 65.0 + min(27.0, (price - sys2_high) / n_value * 15))
                reasons.append(f"Turtle S2 BUY: broke {entry_period}-bar high ${sys2_high:.0f} (no filter).")
            elif price < sys2_low:
                direction = SignalDirection.SELL
                confidence = min(92.0, 65.0 + min(27.0, (sys2_low - price) / n_value * 15))
                reasons.append(f"Turtle S2 SELL: broke {entry_period}-bar low ${sys2_low:.0f} (no filter).")
            else:
                reasons.append(f"Turtle S2: inside {entry_period}-bar range [${sys2_low:.0f}-${sys2_high:.0f}]. N={n_value:.0f}, unit={unit_size:.4f}")

        final_direction = SignalDirection.FLAT if filtered else direction

        stop_loss = take_profit = price
        if final_direction == SignalDirection.BUY:
            stop_loss = price - cfg.TURTLE_SL_N_MULTIPLIER * n_value
            take_profit = price + cfg.TURTLE_TP_N_MULTIPLIER * n_value
        elif final_direction == SignalDirection.SELL:
            stop_loss = price + cfg.TURTLE_SL_N_MULTIPLIER * n_value
            take_profit = price - cfg.TURTLE_TP_N_MULTIPLIER * n_value

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        risk_reward = reward / risk if risk > 0 else 0.0

        return TradingSignal(
            strategy="Turtle Trading",
            symbol=symbol,
            interval=interval,
            timestamp=market.iloc[-1]["timestamps"].isoformat(),
            direction=final_direction,
            confidence=round(0.0 if filtered else confidence, 2),
            entry=price,
            atr=n_value,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=round(risk_reward, 2),
            reasons=reasons,
            regime=regime["regime"],
        )

    def _last_sys1_breakout_was_loss(
        self, market, entry_period: int, exit_period: int, direction: str
    ) -> bool:
        """
        Scan backward for the most recent System-1 breakout in `direction` and
        determine whether it lost. True = take the current signal (no prior
        breakout, or the last one lost). False = filter it (last one won or
        is still open).
        """
        high = market["high"].to_numpy()
        low = market["low"].to_numpy()
        close = market["close"].to_numpy()
        n = len(market)

        search_end = max(entry_period + exit_period + 5, n - strategy_config.TURTLE_BACKWARD_SCAN_BARS)

        for i in range(n - 3, search_end, -1):
            if i - entry_period < 0:
                break

            prior_high = high[i - entry_period:i].max()
            prior_low = low[i - entry_period:i].min()
            bar_close = close[i]
            is_breakout = bar_close > prior_high if direction == "BUY" else bar_close < prior_low
            if not is_breakout:
                continue

            entry_price = bar_close

            for j in range(i + 1, n - 1):
                if j - exit_period < 0:
                    continue
                exit_low_slice = low[j - exit_period:j]
                exit_high_slice = high[j - exit_period:j]
                if len(exit_low_slice) < exit_period:
                    continue
                exit_level = exit_low_slice.min() if direction == "BUY" else exit_high_slice.max()
                exit_fired = close[j] < exit_level if direction == "BUY" else close[j] > exit_level
                if exit_fired:
                    return (close[j] < entry_price) if direction == "BUY" else (close[j] > entry_price)

            return False  # breakout found, no exit yet — still running, treat as potential winner

        return True  # no prior breakout found — take the current signal

    def _flat_signal(self, symbol, interval, market, reason: str) -> TradingSignal:
        price = float(market.iloc[-1]["close"])
        return TradingSignal(
            strategy="Turtle Trading",
            symbol=symbol,
            interval=interval,
            timestamp=market.iloc[-1]["timestamps"].isoformat(),
            direction=SignalDirection.FLAT,
            confidence=0.0,
            entry=price,
            atr=0.0,
            stop_loss=price,
            take_profit=price,
            risk_reward=0.0,
            reasons=[reason],
        )
