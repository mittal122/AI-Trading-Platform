class TradeDecision:

    def decide(
        self,
        signal_score: dict,
    ) -> dict:

        buy_score = signal_score["buy_score"]
        sell_score = signal_score["sell_score"]

        decision = "FLAT"
        confidence = max(
            buy_score,
            sell_score,
        )

        reason = "No clear edge."

        # -------------------------
        # Strong BUY
        # -------------------------

        if (
            buy_score >= 70
            and
            buy_score >= sell_score + 20
        ):

            decision = "BUY"

            reason = (
                "Strong bullish confirmation."
            )

        # -------------------------
        # Strong SELL
        # -------------------------

        elif (
            sell_score >= 70
            and
            sell_score >= buy_score + 20
        ):

            decision = "SELL"

            reason = (
                "Strong bearish confirmation."
            )

        # -------------------------
        # Weak BUY
        # -------------------------

        elif (
            buy_score >= 50
            and
            buy_score > sell_score
        ):

            decision = "WATCH_BUY"

            reason = (
                "Bullish setup forming."
            )

        # -------------------------
        # Weak SELL
        # -------------------------

        elif (
            sell_score >= 50
            and
            sell_score > buy_score
        ):

            decision = "WATCH_SELL"

            reason = (
                "Bearish setup forming."
            )

        # -------------------------
        # Conflicting signals
        # -------------------------

        elif abs(
            buy_score - sell_score
        ) <= 15:

            decision = "WAIT"

            reason = (
                "Conflicting market signals."
            )

        return {

            "decision": decision,

            "confidence": confidence,

            "reason": reason,

            "buy_score": buy_score,

            "sell_score": sell_score,

        }