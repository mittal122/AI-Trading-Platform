class MarketRegime:

    # ADX thresholds for trend classification
    STRONG_TREND_ADX = 40
    TREND_ADX = 20

    # ATR as % of price thresholds for volatility
    HIGH_VOL_ATR_PCT = 3.0
    LOW_VOL_ATR_PCT = 1.0

    # Bollinger Width as % of price thresholds
    HIGH_VOL_BB_PCT = 6.0
    LOW_VOL_BB_PCT = 2.0

    def detect(
        self,
        values: dict,
    ) -> dict:

        regime = self._classify_regime(values)

        trend_strength = self._trend_strength(values)

        volatility = self._volatility_level(values)

        print("\n========== MARKET REGIME ==========")
        print(f"{'Regime':<20}: {regime}")
        print(f"{'Trend Strength':<20}: {trend_strength}")
        print(f"{'Volatility':<20}: {volatility}")
        print()

        return {
            "regime": regime,
            "trend_strength": trend_strength,
            "volatility": volatility,
        }

    def _classify_regime(
        self,
        values: dict,
    ) -> str:

        adx = values["adx14"]
        trend = values["trend"]

        # Below trend threshold — no directional conviction
        if adx < self.TREND_ADX:
            return "SIDEWAYS"

        if trend == "BULLISH":

            if adx >= self.STRONG_TREND_ADX:
                return "STRONG_BULL"

            return "WEAK_BULL"

        if trend == "BEARISH":

            if adx >= self.STRONG_TREND_ADX:
                return "STRONG_BEAR"

            return "WEAK_BEAR"

        return "SIDEWAYS"

    def _trend_strength(
        self,
        values: dict,
    ) -> float:

        adx = values["adx14"]

        # ADX is already 0-100; clip and round
        return round(min(float(adx), 100.0), 1)

    def _volatility_level(
        self,
        values: dict,
    ) -> str:

        price = values["price"]
        atr = values["atr14"]
        bb_width = values["bollinger_width"]

        if price <= 0:
            return "NORMAL"

        atr_pct = (atr / price) * 100
        bb_pct = (bb_width / price) * 100

        if (
            atr_pct >= self.HIGH_VOL_ATR_PCT
            or
            bb_pct >= self.HIGH_VOL_BB_PCT
        ):
            return "HIGH"

        if (
            atr_pct <= self.LOW_VOL_ATR_PCT
            and
            bb_pct <= self.LOW_VOL_BB_PCT
        ):
            return "LOW"

        return "NORMAL"
