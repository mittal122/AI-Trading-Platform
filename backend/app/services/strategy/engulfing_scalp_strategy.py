from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.trading_signal import SignalDirection, TradingSignal
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.market_regime import MarketRegime


class EngulfingScalpStrategy(BaseStrategy):
    """
    Engulfing Scalp — long-only.

    Trend filter (price > EMA200) + momentum filter (RSI > midline) + a
    bullish engulfing candle on the last CLOSED bar. Stop/target are sized
    off the engulfing candle's own range, not ATR. Confidence gets a bonus
    if the last two RSI swing lows show bullish divergence against price.
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
        min_bars = cfg.ENGULF_EMA_PERIOD + cfg.ENGULF_RSI_PERIOD + 2

        if len(market) < min_bars:
            return self._flat_signal(
                symbol, interval, market,
                reason=f"Insufficient history for Engulfing Scalp (need {min_bars}+ candles).",
            )

        base_values = self.indicators.calculate_from_dataframe(market)
        regime = self.market_regime.detect(base_values)
        price = base_values["price"]
        ema200 = base_values["ema200"]
        rsi_current = base_values["rsi14"]

        if price <= ema200:
            return self._flat_signal(symbol, interval, market, reason=f"Price ${price:.2f} not above EMA{cfg.ENGULF_EMA_PERIOD} (${ema200:.2f}).")

        if rsi_current <= cfg.ENGULF_RSI_MIDLINE:
            return self._flat_signal(symbol, interval, market, reason=f"RSI {rsi_current:.1f} not above midline {cfg.ENGULF_RSI_MIDLINE}.")

        prev = market.iloc[-2]
        curr = market.iloc[-1]

        prev_bearish = prev["close"] < prev["open"]
        curr_bullish = curr["close"] > curr["open"]
        opens_at_or_below = curr["open"] <= prev["close"]
        closes_above = curr["close"] > prev["open"]

        prev_body = abs(prev["open"] - prev["close"])
        curr_body = abs(curr["open"] - curr["close"])
        body_ratio_ok = prev_body > 0 and (curr_body / prev_body) >= cfg.ENGULF_MIN_BODY_RATIO

        is_bullish_engulfing = prev_bearish and curr_bullish and opens_at_or_below and closes_above and body_ratio_ok
        if not is_bullish_engulfing:
            return self._flat_signal(symbol, interval, market, reason="No bullish engulfing pattern on the last closed candle.")

        candle_range = curr["high"] - curr["low"]
        if candle_range <= 0:
            return self._flat_signal(symbol, interval, market, reason="Engulfing candle has zero range.")

        entry = price
        risk = candle_range * cfg.ENGULF_SL_RANGE_MULTIPLIER
        reward = risk * cfg.ENGULF_RR_RATIO
        stop_loss = entry - risk
        take_profit = entry + reward

        divergence_bonus = self._rsi_divergence_bonus(market, base_values)

        confidence = 65.0
        confidence += min(15.0, round((rsi_current - cfg.ENGULF_RSI_MIDLINE) / 2))
        confidence += min(10.0, round((price / ema200 - 1) * 500))
        confidence += divergence_bonus
        confidence = min(95.0, max(65.0, confidence))

        body_ratio = curr_body / prev_body if prev_body > 0 else 0.0
        reasons = [
            f"Price ${price:.2f} > EMA{cfg.ENGULF_EMA_PERIOD} (${ema200:.2f}).",
            f"RSI{cfg.ENGULF_RSI_PERIOD} = {rsi_current:.1f} > {cfg.ENGULF_RSI_MIDLINE}.",
            f"Bullish engulfing closed (body ratio {body_ratio:.2f}x). Range = {candle_range:.2f}.",
        ]
        if divergence_bonus > 0:
            reasons.append("RSI bullish divergence detected on recent swing lows.")

        risk_reward = reward / risk if risk > 0 else 0.0

        return TradingSignal(
            strategy="Engulfing Scalp",
            symbol=symbol,
            interval=interval,
            timestamp=market.iloc[-1]["timestamps"].isoformat(),
            direction=SignalDirection.BUY,
            confidence=round(confidence, 2),
            entry=entry,
            atr=base_values["atr14"],
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=round(risk_reward, 2),
            reasons=reasons,
            regime=regime["regime"],
        )

    def _rsi_divergence_bonus(self, market, base_values) -> float:
        """Bullish divergence: the last two RSI swing lows show price making
        a lower low while RSI makes a higher low."""
        cfg = strategy_config
        lookback = min(cfg.ENGULF_DIVERGENCE_LOOKBACK, len(market) - 2)
        if lookback < 3:
            return 0.0

        rsi_series = self.indicators.calculate_rsi_series(market, cfg.ENGULF_RSI_PERIOD)
        low = market["low"].to_numpy()
        n = len(market)

        swing_lows = []
        for i in range(n - lookback, n - 3):
            if i < 1:
                continue
            if i >= len(rsi_series) - 1:
                continue
            rsi_val = rsi_series.iloc[i]
            if rsi_val != rsi_val:  # NaN guard (RSI warmup period)
                continue
            if low[i] < low[i - 1] and low[i] < low[i + 1]:
                swing_lows.append((low[i], float(rsi_val)))

        if len(swing_lows) < 2:
            return 0.0

        (price_1, rsi_1), (price_2, rsi_2) = swing_lows[-2], swing_lows[-1]
        price_made_lower_low = price_2 < price_1
        rsi_made_higher_low = rsi_2 > rsi_1

        return cfg.ENGULF_DIVERGENCE_BONUS if (price_made_lower_low and rsi_made_higher_low) else 0.0

    def _flat_signal(self, symbol, interval, market, reason: str) -> TradingSignal:
        price = float(market.iloc[-1]["close"])
        return TradingSignal(
            strategy="Engulfing Scalp",
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
