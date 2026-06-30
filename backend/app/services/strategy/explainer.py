class Explainer:

    def explain(
        self,
        direction: str,
        score: dict,
        regime: dict,
        values: dict,
        quality: dict,
    ) -> str:
        """
        Returns human-readable trade explanation.
        """

        lines = []

        # -------------------------
        # Summary line
        # -------------------------

        summary = self._summary(direction, score, quality)
        lines.append(summary)
        lines.append("")

        # -------------------------
        # Market context
        # -------------------------

        regime_name = regime.get("regime", "UNKNOWN")
        trend_strength = regime.get("trend_strength", 0)
        volatility = regime.get("volatility", "NORMAL")

        lines.append(
            f"Market: {regime_name.replace('_', ' ')} "
            f"(trend strength {trend_strength:.0f}/100, "
            f"{volatility.lower()} volatility)"
        )

        # -------------------------
        # Key indicators
        # -------------------------

        rsi = values["rsi14"]
        adx = values["adx14"]
        rel_vol = values["relative_volume"]

        lines.append(
            f"RSI={rsi:.1f}  ADX={adx:.1f}  "
            f"RelVol={rel_vol:.2f}x  "
            f"RR={quality.get('breakdown', {}).get('risk_reward', 0)}"
        )

        lines.append("")

        # -------------------------
        # Signal reasons
        # -------------------------

        if direction == "BUY":

            reasons = score.get("buy_reasons", [])
            lines.append("Why BUY:")

        elif direction == "SELL":

            reasons = score.get("sell_reasons", [])
            lines.append("Why SELL:")

        else:

            reasons = score.get("buy_reasons", []) + score.get("sell_reasons", [])
            lines.append("Why WAIT:")

        for reason in reasons:
            lines.append(f"  • {reason}")

        if not reasons:
            lines.append("  • No strong signal detected.")

        # -------------------------
        # Quality note
        # -------------------------

        lines.append("")

        grade = quality.get("quality_grade", "?")
        q_score = quality.get("quality_score", 0)
        lines.append(f"Trade quality: {q_score:.0f}/100 [{grade}]")

        return "\n".join(lines)

    def _summary(
        self,
        direction: str,
        score: dict,
        quality: dict,
    ) -> str:

        confidence = score.get("confidence", 0)
        q_score = quality.get("quality_score", 0)

        if direction == "BUY":

            if confidence >= 80 and q_score >= 75:
                return "STRONG BUY — High confidence, excellent setup."
            elif confidence >= 60:
                return "BUY — Moderate confidence."
            else:
                return "WEAK BUY — Low confidence, use caution."

        elif direction == "SELL":

            if confidence >= 80 and q_score >= 75:
                return "STRONG SELL — High confidence, excellent setup."
            elif confidence >= 60:
                return "SELL — Moderate confidence."
            else:
                return "WEAK SELL — Low confidence, use caution."

        else:

            return "WAIT — No clear edge. Conflicting or insufficient signals."
