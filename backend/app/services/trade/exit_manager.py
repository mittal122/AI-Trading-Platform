from backend.app.core.strategy_config import strategy_config
from backend.app.services.trade.trade_state import TradeState


class ExitManager:

    def check_exit(
        self,
        price: float,
        signal_direction: str,
        trade: TradeState,
        atr: float,
        high: float = None,
        low: float = None,
    ) -> tuple[bool, str, float]:
        """
        Returns (should_exit, reason, exit_price).

        `price` is the candle close (used for decision-based exits and as the
        is_long/peak fallback). `high`/`low` are the same candle's intrabar
        range — when given, resting-order-style exits (STOP_LOSS, TAKE_PROFIT,
        PARTIAL_EXIT, TRAILING_STOP) are detected against the full range
        instead of just the close, since a candle can wick through a level
        and close back on the other side. Decision-style exits (ATR_REVERSAL,
        TIME_EXIT, SIGNAL_REVERSAL) still key off the close — those represent
        a confirmed reversal, not a resting order, so a single wick shouldn't
        trigger them.

        Updates trade state (peak_price, trailing stop, candles_held) in place.
        """

        if not trade or not trade.is_open:
            return False, "", price

        if high is None:
            high = price
        if low is None:
            low = price

        # -------------------------
        # Increment candle counter
        # -------------------------

        trade.candles_held += 1

        # -------------------------
        # Update peak price (off the candle extreme, not just the close)
        # -------------------------

        if trade.peak_price == 0.0:
            trade.peak_price = trade.entry_price

        # For BUY trades, peak = highest price seen
        # For SELL trades, peak = lowest price seen (stored as positive)
        is_long = price > trade.entry_price or trade.stop_loss < trade.entry_price

        if is_long:
            if high > trade.peak_price:
                trade.peak_price = high
        else:
            if low < trade.peak_price or trade.peak_price == trade.entry_price:
                trade.peak_price = low

        # -------------------------
        # Hard Stop Loss — intrabar touch, gap-aware fill
        # -------------------------

        if is_long and low <= trade.stop_loss:
            fill = trade.stop_loss if high >= trade.stop_loss else low
            return True, "STOP_LOSS", fill

        if not is_long and high >= trade.stop_loss:
            fill = trade.stop_loss if low <= trade.stop_loss else high
            return True, "STOP_LOSS", fill

        # -------------------------
        # Take Profit — intrabar touch, capped at target (never overstates a gap)
        # -------------------------

        if is_long and high >= trade.take_profit:
            return True, "TAKE_PROFIT", trade.take_profit

        if not is_long and low <= trade.take_profit:
            return True, "TAKE_PROFIT", trade.take_profit

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
        # Partial Exit — close 50% at 1:1 RR (intrabar touch)
        # -------------------------

        if not trade.partial_exit_done:
            target = trade.entry_price + risk if is_long else trade.entry_price - risk
            if is_long and high >= target:
                trade.partial_exit_done = True
                return True, "PARTIAL_EXIT", target
            elif not is_long and low <= target:
                trade.partial_exit_done = True
                return True, "PARTIAL_EXIT", target

        # -------------------------
        # Trailing Stop
        # Activate after break-even; trail 1.5x ATR behind peak
        # -------------------------

        trail_distance = atr * 1.5

        if is_long:

            # Activate trailing once price > entry + 1 ATR
            if high > trade.entry_price + atr:
                trade.trailing_stop_active = True

            if trade.trailing_stop_active:
                trailing_sl = trade.peak_price - trail_distance
                if trailing_sl > trade.stop_loss:
                    trade.stop_loss = trailing_sl
                    print(f"Trailing stop updated | SL={trade.stop_loss:.2f}")

                if low <= trade.stop_loss:
                    fill = trade.stop_loss if high >= trade.stop_loss else low
                    return True, "TRAILING_STOP", fill

        else:

            if low < trade.entry_price - atr:
                trade.trailing_stop_active = True

            if trade.trailing_stop_active:
                trailing_sl = trade.peak_price + trail_distance
                if trailing_sl < trade.stop_loss:
                    trade.stop_loss = trailing_sl
                    print(f"Trailing stop updated | SL={trade.stop_loss:.2f}")

                if high >= trade.stop_loss:
                    fill = trade.stop_loss if low <= trade.stop_loss else high
                    return True, "TRAILING_STOP", fill

        # -------------------------
        # ATR Reversal Exit — confirmed on close, not a resting order
        # Exit if price reverses > 1.5 ATR from peak
        # -------------------------

        if is_long:
            atr_reversal = trade.peak_price - (atr * 1.5)
            if price < atr_reversal and trade.peak_price > trade.entry_price:
                return True, "ATR_REVERSAL", price

        else:
            atr_reversal = trade.peak_price + (atr * 1.5)
            if price > atr_reversal and trade.peak_price < trade.entry_price:
                return True, "ATR_REVERSAL", price

        # -------------------------
        # Time Exit
        # -------------------------

        if trade.candles_held >= strategy_config.TIME_EXIT_CANDLES:
            return True, "TIME_EXIT", price

        # -------------------------
        # Strategy / Momentum Exit
        # -------------------------

        if is_long and signal_direction == "SELL":
            return True, "SIGNAL_REVERSAL", price

        if not is_long and signal_direction == "BUY":
            return True, "SIGNAL_REVERSAL", price

        return False, "", price
