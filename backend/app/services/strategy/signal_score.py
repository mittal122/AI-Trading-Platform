class SignalScore:

    # Adaptive weights — total max = 100
    WEIGHT_TREND = 30
    WEIGHT_REGIME = 25
    WEIGHT_MOMENTUM = 20       # RSI 10 + MACD 10
    WEIGHT_VOLATILITY = 15     # ADX direction quality
    WEIGHT_VOLUME = 10

    def score(
        self,
        values: dict,
        regime: dict = None,
    ) -> dict:

        print("\n========== INDICATORS ==========")

        for key, value in values.items():
            print(f"{key:20}: {value}")

        print()

        buy_score = 0
        sell_score = 0

        buy_reasons = []
        sell_reasons = []

        # -------------------------
        # Trend (30 pts)
        # -------------------------

        trend = values["trend"]

        if trend == "BULLISH":

            buy_score += self.WEIGHT_TREND
            print(f"✓ Bullish Trend +{self.WEIGHT_TREND}")

            buy_reasons.append(
                "Bullish EMA trend (EMA20 > EMA50 > EMA200)."
            )

        elif trend == "BEARISH":

            sell_score += self.WEIGHT_TREND
            print(f"✓ Bearish Trend +{self.WEIGHT_TREND}")

            sell_reasons.append(
                "Bearish EMA trend (EMA20 < EMA50 < EMA200)."
            )

        # -------------------------
        # Market Regime (25 pts)
        # -------------------------

        if regime:

            regime_buy, regime_sell, r_buy_reasons, r_sell_reasons = (
                self._score_regime(regime)
            )

            buy_score += regime_buy
            sell_score += regime_sell

            buy_reasons.extend(r_buy_reasons)
            sell_reasons.extend(r_sell_reasons)

        # -------------------------
        # Momentum — RSI (10 pts)
        # -------------------------

        rsi = values["rsi14"]
        previous_rsi = values["previous_rsi14"]

        if previous_rsi < 30 and rsi > 30:

            buy_score += 10
            print("✓ RSI Recovery +10")

            buy_reasons.append(
                "RSI recovered from oversold."
            )

        elif previous_rsi > 70 and rsi < 70:

            sell_score += 10
            print("✓ RSI Rejection +10")

            sell_reasons.append(
                "RSI rejected from overbought."
            )

        # -------------------------
        # Momentum — MACD (10 pts)
        # -------------------------

        if values["histogram"] > 0:

            buy_score += 10
            print("✓ MACD Bullish +10")

            buy_reasons.append(
                "Positive MACD histogram."
            )

        else:

            sell_score += 10
            print("✓ MACD Bearish +10")

            sell_reasons.append(
                "Negative MACD histogram."
            )

        # -------------------------
        # Volatility / Trend Quality — ADX (15 pts)
        # -------------------------

        if values["adx14"] > 25:

            if values["plus_di"] > values["minus_di"]:

                buy_score += self.WEIGHT_VOLATILITY
                print(f"✓ Strong Bull ADX +{self.WEIGHT_VOLATILITY}")

                buy_reasons.append(
                    "Strong bullish directional trend (ADX/DI)."
                )

            else:

                sell_score += self.WEIGHT_VOLATILITY
                print(f"✓ Strong Bear ADX +{self.WEIGHT_VOLATILITY}")

                sell_reasons.append(
                    "Strong bearish directional trend (ADX/DI)."
                )

        # -------------------------
        # Volume (10 pts)
        # -------------------------

        if values["relative_volume"] > 1.2:

            if buy_score >= sell_score:

                buy_score += self.WEIGHT_VOLUME
                print(f"✓ High Buy Volume +{self.WEIGHT_VOLUME}")

                buy_reasons.append(
                    "High relative buying volume."
                )

            else:

                sell_score += self.WEIGHT_VOLUME
                print(f"✓ High Sell Volume +{self.WEIGHT_VOLUME}")

                sell_reasons.append(
                    "High relative selling volume."
                )

        # -------------------------
        # Confidence
        # -------------------------

        confidence = self._calculate_confidence(
            buy_score=buy_score,
            sell_score=sell_score,
            values=values,
            regime=regime,
        )

        # -------------------------
        # Direction
        # -------------------------

        if buy_score > sell_score:
            direction = "BUY"

        elif sell_score > buy_score:
            direction = "SELL"

        else:
            direction = "FLAT"

        print()
        print(f"BUY SCORE  : {buy_score}")
        print(f"SELL SCORE : {sell_score}")
        print(f"CONFIDENCE : {confidence:.1f}")
        print(f"DIRECTION  : {direction}")
        print("-----------------------------------")

        return {
            "direction": direction,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "confidence": confidence,
            "buy_reasons": buy_reasons,
            "sell_reasons": sell_reasons,
        }

    def _score_regime(
        self,
        regime: dict,
    ) -> tuple:

        regime_name = regime["regime"]

        buy_pts = 0
        sell_pts = 0
        buy_reasons = []
        sell_reasons = []

        if regime_name == "STRONG_BULL":

            buy_pts = self.WEIGHT_REGIME
            print(f"✓ Strong Bull Regime +{buy_pts}")

            buy_reasons.append(
                "Strong bull market regime confirmed."
            )

        elif regime_name == "WEAK_BULL":

            buy_pts = int(self.WEIGHT_REGIME * 0.6)
            print(f"✓ Weak Bull Regime +{buy_pts}")

            buy_reasons.append(
                "Weak bull market regime."
            )

        elif regime_name == "STRONG_BEAR":

            sell_pts = self.WEIGHT_REGIME
            print(f"✓ Strong Bear Regime +{sell_pts}")

            sell_reasons.append(
                "Strong bear market regime confirmed."
            )

        elif regime_name == "WEAK_BEAR":

            sell_pts = int(self.WEIGHT_REGIME * 0.6)
            print(f"✓ Weak Bear Regime +{sell_pts}")

            sell_reasons.append(
                "Weak bear market regime."
            )

        elif regime_name == "SIDEWAYS":

            print("⚠ Sideways Regime — no regime points awarded")

        return buy_pts, sell_pts, buy_reasons, sell_reasons

    def _calculate_confidence(
        self,
        buy_score: int,
        sell_score: int,
        values: dict,
        regime: dict = None,
    ) -> float:

        raw_score = max(buy_score, sell_score)
        score_gap = abs(buy_score - sell_score)

        # Signal agreement: larger gap = stronger conviction
        if score_gap >= 40:
            agreement_multiplier = 1.15

        elif score_gap >= 20:
            agreement_multiplier = 1.05

        elif score_gap <= 5:
            # Conflicting signals — reduce confidence
            agreement_multiplier = 0.80

        else:
            agreement_multiplier = 1.0

        # Regime quality adjustment
        regime_multiplier = 1.0

        if regime:

            r = regime["regime"]

            if r in ("STRONG_BULL", "STRONG_BEAR"):
                regime_multiplier = 1.10

            elif r == "SIDEWAYS":
                # Sideways markets produce unreliable directional signals
                regime_multiplier = 0.85

            # High volatility increases uncertainty
            if regime.get("volatility") == "HIGH":
                regime_multiplier *= 0.90

        final_confidence = (
            raw_score
            * agreement_multiplier
            * regime_multiplier
        )

        return round(min(final_confidence, 100.0), 1)
