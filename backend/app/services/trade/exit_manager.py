from backend.app.core.strategy_config import strategy_config
from backend.app.services.trade.trade_state import TradeState


class ExitManager:

    def check_exit(
        self,
        price: float,
        signal_direction: str,
        trade: TradeState,
        atr: float,
    ) -> tuple[bool, str]:
        """
        Returns (should_exit, reason).
        Updates trade state (peak_price, trailing stop, candles_held) in place.
        """

        if not trade or not trade.is_open:
            return False, ""

        # -------------------------
        # Increment candle counter
        # -------------------------

        trade.candles_held += 1

        # -------------------------
        # Update peak price
        # -------------------------

        if trade.peak_price == 0.0:
            trade.peak_price = trade.entry_price

        # For BUY trades, peak = highest price seen
        # For SELL trades, peak = lowest price seen (stored as positive)
        is_long = price > trade.entry_price or trade.stop_loss < trade.entry_price

        if is_long:
            if price > trade.peak_price:
                trade.peak_price = price
        else:
            if price < trade.peak_price or trade.peak_price == trade.entry_price:
                trade.peak_price = price

        # -------------------------
        # Hard Stop Loss
        # -------------------------

        if is_long and price <= trade.stop_loss:
            return True, "STOP_LOSS"

        if not is_long and price >= trade.stop_loss:
            return True, "STOP_LOSS"

        # -------------------------
        # Take Profit
        # -------------------------

        if is_long and price >= trade.take_profit:
            return True, "TAKE_PROFIT"

        if not is_long and price <= trade.take_profit:
            return True, "TAKE_PROFIT"

        # -------------------------
        # Break-even activation
        # Activate when trade reaches 1:1 RR
        # -------------------------

        risk = abs(trade.entry_price - trade.stop_loss)

        if is_long:
            breakeven_trigger = trade.entry_price + risk
            if price >= breakeven_trigger and trade.stop_loss < trade.entry_price:
                # Move SL to entry (break-even)
                trade.stop_loss = trade.entry_price
                print(f"Break-even activated | SL moved to {trade.entry_price:.2f}")

        else:
            breakeven_trigger = trade.entry_price - risk
            if price <= breakeven_trigger and trade.stop_loss > trade.entry_price:
                trade.stop_loss = trade.entry_price
                print(f"Break-even activated | SL moved to {trade.entry_price:.2f}")

        # -------------------------
        # Trailing Stop
        # Activate after break-even; trail 1.5x ATR behind peak
        # -------------------------

        trail_distance = atr * 1.5

        if is_long:

            # Activate trailing once price > entry + 1 ATR
            if price > trade.entry_price + atr:
                trade.trailing_stop_active = True

            if trade.trailing_stop_active:
                trailing_sl = trade.peak_price - trail_distance
                if trailing_sl > trade.stop_loss:
                    trade.stop_loss = trailing_sl
                    print(f"Trailing stop updated | SL={trade.stop_loss:.2f}")

                if price <= trade.stop_loss:
                    return True, "TRAILING_STOP"

        else:

            if price < trade.entry_price - atr:
                trade.trailing_stop_active = True

            if trade.trailing_stop_active:
                trailing_sl = trade.peak_price + trail_distance
                if trailing_sl < trade.stop_loss:
                    trade.stop_loss = trailing_sl
                    print(f"Trailing stop updated | SL={trade.stop_loss:.2f}")

                if price >= trade.stop_loss:
                    return True, "TRAILING_STOP"

        # -------------------------
        # ATR Reversal Exit
        # Exit if price reverses > 1.5 ATR from peak
        # -------------------------

        if is_long:
            atr_reversal = trade.peak_price - (atr * 1.5)
            if price < atr_reversal and trade.peak_price > trade.entry_price:
                return True, "ATR_REVERSAL"

        else:
            atr_reversal = trade.peak_price + (atr * 1.5)
            if price > atr_reversal and trade.peak_price < trade.entry_price:
                return True, "ATR_REVERSAL"

        # -------------------------
        # Time Exit
        # -------------------------

        if trade.candles_held >= strategy_config.TIME_EXIT_CANDLES:
            return True, "TIME_EXIT"

        # -------------------------
        # Strategy / Momentum Exit
        # -------------------------

        if is_long and signal_direction == "SELL":
            return True, "SIGNAL_REVERSAL"

        if not is_long and signal_direction == "BUY":
            return True, "SIGNAL_REVERSAL"

        return False, ""
