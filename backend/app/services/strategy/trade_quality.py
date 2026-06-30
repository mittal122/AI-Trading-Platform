from backend.app.core.strategy_config import strategy_config


class TradeQuality:

    def score(
        self,
        values: dict,
        score: dict,
        regime: dict,
        risk_reward: float,
    ) -> dict:
        """
        Returns quality score 0-100 across 5 categories.
        """

        trend_pts = self._score_trend(regime)
        momentum_pts = self._score_momentum(values, score)
        volume_pts = self._score_volume(values)
        rr_pts = self._score_risk_reward(risk_reward)
        regime_pts = self._score_regime_alignment(score, regime)

        total = trend_pts + momentum_pts + volume_pts + rr_pts + regime_pts

        grade = self._grade(total)

        print("\n========== TRADE QUALITY ==========")
        print(f"{'Trend':<20}: {trend_pts}/25")
        print(f"{'Momentum':<20}: {momentum_pts}/20")
        print(f"{'Volume':<20}: {volume_pts}/20")
        print(f"{'Risk/Reward':<20}: {rr_pts}/20")
        print(f"{'Regime Alignment':<20}: {regime_pts}/15")
        print(f"{'TOTAL':<20}: {total}/100  [{grade}]")
        print()

        return {
            "quality_score": float(total),
            "quality_grade": grade,
            "breakdown": {
                "trend": trend_pts,
                "momentum": momentum_pts,
                "volume": volume_pts,
                "risk_reward": rr_pts,
                "regime": regime_pts,
            },
        }

    def _score_trend(
        self,
        regime: dict,
    ) -> int:

        regime_name = regime.get("regime", "SIDEWAYS")
        trend_strength = regime.get("trend_strength", 0)

        if regime_name in ("STRONG_BULL", "STRONG_BEAR"):
            base = 22
        elif regime_name in ("WEAK_BULL", "WEAK_BEAR"):
            base = 14
        else:
            base = 5

        # Bonus up to 3 pts for very strong ADX
        bonus = 3 if trend_strength >= 50 else 0

        return min(base + bonus, 25)

    def _score_momentum(
        self,
        values: dict,
        score: dict,
    ) -> int:

        pts = 0

        rsi = values["rsi14"]
        prev_rsi = values["previous_rsi14"]

        # RSI signal
        if prev_rsi < 30 and rsi > 30:
            pts += 10
        elif prev_rsi > 70 and rsi < 70:
            pts += 10
        elif 40 <= rsi <= 60:
            pts += 5  # neutral zone

        # MACD signal
        if values["histogram"] > 0:
            pts += 10

        return min(pts, 20)

    def _score_volume(
        self,
        values: dict,
    ) -> int:

        rel_vol = values["relative_volume"]

        if rel_vol >= 1.5:
            return 20
        elif rel_vol >= 1.2:
            return 12
        elif rel_vol >= 0.8:
            return 6
        else:
            return 0

    def _score_risk_reward(
        self,
        risk_reward: float,
    ) -> int:

        if risk_reward >= strategy_config.QUALITY_GREAT_RR:
            return 20
        elif risk_reward >= strategy_config.QUALITY_GOOD_RR:
            return 14
        elif risk_reward >= strategy_config.QUALITY_MIN_RR:
            return 8
        else:
            return 2

    def _score_regime_alignment(
        self,
        score: dict,
        regime: dict,
    ) -> int:

        direction = score.get("direction", "FLAT")
        regime_name = regime.get("regime", "SIDEWAYS")

        aligned = (
            (direction == "BUY" and "BULL" in regime_name)
            or
            (direction == "SELL" and "BEAR" in regime_name)
        )

        if aligned and "STRONG" in regime_name:
            return 15
        elif aligned:
            return 10
        elif regime_name == "SIDEWAYS":
            return 5
        else:
            return 0

    def _grade(
        self,
        total: int,
    ) -> str:

        if total >= 85:
            return "A+"
        elif total >= 75:
            return "A"
        elif total >= 65:
            return "B"
        elif total >= 50:
            return "C"
        elif total >= 35:
            return "D"
        else:
            return "F"
