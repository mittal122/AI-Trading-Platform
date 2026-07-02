from backend.app.core.strategy_config import strategy_config
from backend.app.schemas.trading_signal import SignalDirection, TradingSignal
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.strategy.base_strategy import BaseStrategy
from backend.app.services.strategy.market_regime import MarketRegime


class CTATrendStrategy(BaseStrategy):
    """
    Systematic Trend Following (CTA-style).

    Composite of 3 EMA-crossover sub-signals (fast/slow pairs at three
    timescales) + 2 time-series momentum sub-signals, averaged into a
    single [-1, +1] score. Direction follows the composite's sign;
    confidence scales with sub-signal agreement and a volatility-targeted
    exposure estimate. Stops/targets are ATR(20)-scaled, independent of
    the regime-based DynamicATR table other strategies use — this
    strategy manages its own risk via volatility targeting instead.
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

        min_bars = max(cfg.CTA_SLOW_EMA_3, cfg.CTA_MOM_LOOKBACK_2, cfg.CTA_VOL_LOOKBACK) + 1
        if len(market) < min_bars:
            return self._flat_signal(
                symbol, interval, market,
                reason=f"Insufficient history for CTA Trend (need {min_bars}+ candles).",
            )

        # Regime context (for TradingSignal.regime + explanation parity with other strategies)
        base_values = self.indicators.calculate_from_dataframe(market)
        regime = self.market_regime.detect(base_values)
        price = base_values["price"]

        cta = self.indicators.calculate_cta_trend(
            market,
            fast_ema_1=cfg.CTA_FAST_EMA_1, slow_ema_1=cfg.CTA_SLOW_EMA_1,
            fast_ema_2=cfg.CTA_FAST_EMA_2, slow_ema_2=cfg.CTA_SLOW_EMA_2,
            fast_ema_3=cfg.CTA_FAST_EMA_3, slow_ema_3=cfg.CTA_SLOW_EMA_3,
            mom_lookback_1=cfg.CTA_MOM_LOOKBACK_1, mom_lookback_2=cfg.CTA_MOM_LOOKBACK_2,
            vol_lookback=cfg.CTA_VOL_LOOKBACK, periods_per_year=cfg.CTA_PERIODS_PER_YEAR,
            atr_period=cfg.CTA_ATR_PERIOD,
        )

        composite = cta["composite"]
        atr = cta["atr"]

        direction = SignalDirection.FLAT
        if composite > cfg.CTA_ENTRY_THRESHOLD:
            direction = SignalDirection.BUY
        elif composite < -cfg.CTA_ENTRY_THRESHOLD:
            direction = SignalDirection.SELL

        # Volatility-targeted exposure — used as a confidence signal, not
        # leverage (position sizing is PositionEngine's job downstream).
        raw_exposure = (cfg.CTA_TARGET_VOL_PCT / cta["annualized_vol"]) if cta["annualized_vol"] > 0 else 1.0
        exposure = min(cfg.CTA_MAX_LEVERAGE, max(0.0, raw_exposure))

        confidence = 0.0
        stop_loss = take_profit = price
        reasons: list[str] = []

        if direction != SignalDirection.FLAT and atr > 0:
            is_buy = direction == SignalDirection.BUY
            conviction_bonus = abs(composite) * 40  # 0–40
            vol_bonus = min(10.0, exposure * 10)     # 0–10
            confidence = min(92.0, 50.0 + conviction_bonus + vol_bonus)

            stop_loss = price - cfg.CTA_SL_ATR_MULTIPLIER * atr if is_buy else price + cfg.CTA_SL_ATR_MULTIPLIER * atr
            take_profit = price + cfg.CTA_TP_ATR_MULTIPLIER * atr if is_buy else price - cfg.CTA_TP_ATR_MULTIPLIER * atr

            ma_aligned = sum(
                1 for s in (cta["ma_signal_1"], cta["ma_signal_2"], cta["ma_signal_3"])
                if s == (1 if is_buy else -1)
            )
            mom_aligned = sum(
                1 for s in (cta["mom_signal_1"], cta["mom_signal_2"])
                if s == (1 if is_buy else -1)
            )
            reasons.append(
                f"Composite {composite:+.2f}: {ma_aligned}/3 EMA pairs + {mom_aligned}/2 momentum "
                f"windows aligned {direction.value}."
            )
            reasons.append(
                f"Annualized vol {cta['annualized_vol']*100:.1f}% → exposure {exposure*100:.0f}% "
                f"of target ({cfg.CTA_TARGET_VOL_PCT*100:.0f}%)."
            )
        else:
            reasons.append(
                f"Composite {composite:+.2f} within ±{cfg.CTA_ENTRY_THRESHOLD} threshold — no edge. "
                f"MA:[{cta['ma_signal_1']},{cta['ma_signal_2']},{cta['ma_signal_3']}] "
                f"Mom:[{cta['mom_signal_1']},{cta['mom_signal_2']}]"
            )

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        risk_reward = reward / risk if risk > 0 else 0.0

        return TradingSignal(
            strategy="CTA Trend",
            symbol=symbol,
            interval=interval,
            timestamp=market.iloc[-1]["timestamps"].isoformat(),
            direction=direction,
            confidence=round(confidence, 2),
            entry=price,
            atr=atr,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=round(risk_reward, 2),
            reasons=reasons,
            regime=regime["regime"],
        )

    def _flat_signal(self, symbol, interval, market, reason: str) -> TradingSignal:
        price = float(market.iloc[-1]["close"])
        return TradingSignal(
            strategy="CTA Trend",
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
