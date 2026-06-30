from backend.app.core.strategy_config import strategy_config


class EntryFilter:

    # Critical checks must ALL pass for entry to be valid
    # At least MIN_CONFIRMATIONS of all checks must pass

    def check_buy(
        self,
        values: dict,
    ) -> tuple[bool, list[str]]:
        """
        Returns (is_valid, failed_check_names).
        Critical: trend + ADX must both pass.
        Soft: MACD, VWAP, RSI — need >= MIN_BUY_CONFIRMATIONS total.
        """

        checks = [
            ("Bullish EMA trend",      values["trend"] == "BULLISH"),
            ("ADX trending",           values["adx14"] > strategy_config.ADX_THRESHOLD),
            ("MACD bullish",           values["histogram"] > 0),
            ("Price above VWAP",       values["price"] > values["vwap"]),
            ("RSI not overbought",     values["rsi14"] < strategy_config.RSI_OVERBOUGHT),
        ]

        failed = [
            name
            for name, passed in checks
            if not passed
        ]

        passed_count = len(checks) - len(failed)

        # Both critical checks must pass
        critical_pass = (
            values["trend"] == "BULLISH"
            and
            values["adx14"] > strategy_config.ADX_THRESHOLD
        )

        is_valid = (
            critical_pass
            and
            passed_count >= strategy_config.MIN_BUY_CONFIRMATIONS
        )

        self._print_check("BUY", checks, passed_count, is_valid)

        return is_valid, failed

    def check_sell(
        self,
        values: dict,
    ) -> tuple[bool, list[str]]:
        """
        Returns (is_valid, failed_check_names).
        Critical: trend + ADX must both pass.
        Soft: MACD, VWAP, RSI — need >= MIN_SELL_CONFIRMATIONS total.
        """

        checks = [
            ("Bearish EMA trend",      values["trend"] == "BEARISH"),
            ("ADX trending",           values["adx14"] > strategy_config.ADX_THRESHOLD),
            ("MACD bearish",           values["histogram"] < 0),
            ("Price below VWAP",       values["price"] < values["vwap"]),
            ("RSI not oversold",       values["rsi14"] > strategy_config.RSI_OVERSOLD),
        ]

        failed = [
            name
            for name, passed in checks
            if not passed
        ]

        passed_count = len(checks) - len(failed)

        critical_pass = (
            values["trend"] == "BEARISH"
            and
            values["adx14"] > strategy_config.ADX_THRESHOLD
        )

        is_valid = (
            critical_pass
            and
            passed_count >= strategy_config.MIN_SELL_CONFIRMATIONS
        )

        self._print_check("SELL", checks, passed_count, is_valid)

        return is_valid, failed

    def _print_check(
        self,
        direction: str,
        checks: list,
        passed_count: int,
        is_valid: bool,
    ):

        print(f"\n--- Entry Filter [{direction}] ---")

        for name, passed in checks:
            mark = "✓" if passed else "✗"
            print(f"  {mark} {name}")

        status = "PASS" if is_valid else "BLOCKED"
        print(f"  Result: {status} ({passed_count}/{len(checks)} checks passed)")
