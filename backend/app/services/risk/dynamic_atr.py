class DynamicATR:

    # Default fallback multipliers
    DEFAULT_STOP = 1.5
    DEFAULT_TP = 3.0

    # Regime + volatility multiplier table
    # (stop_multiplier, tp_multiplier)
    MULTIPLIERS = {
        ("STRONG_BULL",  "LOW"):    (2.0, 4.5),
        ("STRONG_BULL",  "NORMAL"): (1.8, 4.0),
        ("STRONG_BULL",  "HIGH"):   (2.5, 4.5),
        ("WEAK_BULL",    "LOW"):    (1.5, 3.0),
        ("WEAK_BULL",    "NORMAL"): (1.5, 3.0),
        ("WEAK_BULL",    "HIGH"):   (2.0, 3.5),
        ("STRONG_BEAR",  "LOW"):    (2.0, 4.5),
        ("STRONG_BEAR",  "NORMAL"): (1.8, 4.0),
        ("STRONG_BEAR",  "HIGH"):   (2.5, 4.5),
        ("WEAK_BEAR",    "LOW"):    (1.5, 3.0),
        ("WEAK_BEAR",    "NORMAL"): (1.5, 3.0),
        ("WEAK_BEAR",    "HIGH"):   (2.0, 3.5),
        ("SIDEWAYS",     "LOW"):    (1.0, 2.0),
        ("SIDEWAYS",     "NORMAL"): (1.2, 2.0),
        ("SIDEWAYS",     "HIGH"):   (1.5, 2.5),
    }

    def get_multipliers(
        self,
        regime: dict,
    ) -> tuple[float, float]:
        """
        Returns (stop_multiplier, tp_multiplier) based on regime.
        """

        regime_name = regime.get("regime", "SIDEWAYS")
        volatility = regime.get("volatility", "NORMAL")

        key = (regime_name, volatility)

        stop_mult, tp_mult = self.MULTIPLIERS.get(
            key,
            (self.DEFAULT_STOP, self.DEFAULT_TP),
        )

        print(
            f"Dynamic ATR | Regime={regime_name} Vol={volatility} "
            f"→ SL={stop_mult}x TP={tp_mult}x"
        )

        return stop_mult, tp_mult

    def calculate_levels(
        self,
        direction: str,
        price: float,
        atr: float,
        regime: dict,
    ) -> tuple[float, float]:
        """
        Returns (stop_loss, take_profit) for given direction and regime.
        """

        stop_mult, tp_mult = self.get_multipliers(regime)

        if direction == "BUY":

            stop_loss = price - (stop_mult * atr)
            take_profit = price + (tp_mult * atr)

        elif direction == "SELL":

            stop_loss = price + (stop_mult * atr)
            take_profit = price - (tp_mult * atr)

        else:

            stop_loss = price - (self.DEFAULT_STOP * atr)
            take_profit = price + (self.DEFAULT_TP * atr)

        return stop_loss, take_profit
