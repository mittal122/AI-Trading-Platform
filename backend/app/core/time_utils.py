from datetime import datetime, timezone


INTERVAL_MINUTES = {
    "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480, "12h": 720,
    "1d": 1440, "3d": 4320, "1w": 10080, "1M": 43200,
}


def interval_to_minutes(interval: str) -> float:
    """Binance kline interval string -> minutes. Falls back to parsing the
    numeric prefix + unit suffix for anything not in the lookup table."""
    if interval in INTERVAL_MINUTES:
        return INTERVAL_MINUTES[interval]

    unit = interval[-1]
    try:
        value = float(interval[:-1])
    except ValueError:
        return 5.0  # unknown format — assume 5m rather than crash

    unit_minutes = {"m": 1, "h": 60, "d": 1440, "w": 10080, "M": 43200}
    return value * unit_minutes.get(unit, 1)


def candles_to_display(candles: float, interval: str) -> str:
    """Human-readable duration for a candle count at a given interval,
    e.g. (8, '15m') -> '~2 hr' or (500, '5m') -> '~1.7 days'."""
    total_minutes = candles * interval_to_minutes(interval)

    if total_minutes < 60:
        return f"~{round(total_minutes)} min"
    if total_minutes < 1440:
        hours = total_minutes / 60
        return f"~{hours:.1f} hr" if hours < 10 else f"~{round(hours)} hr"
    days = total_minutes / 1440
    return f"~{days:.1f} days" if days < 10 else f"~{round(days)} days"


def trade_duration_display(entry_timestamp: str, exit_timestamp: str) -> str:
    """Wall-clock duration between two ISO timestamps, e.g. '2 hr 14 min'.
    Returns '' if either timestamp is missing or unparseable."""
    if not entry_timestamp or not exit_timestamp:
        return ""
    try:
        entry_dt = datetime.fromisoformat(entry_timestamp.replace("Z", "+00:00"))
        exit_dt = datetime.fromisoformat(exit_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return ""

    # entry/exit can come from different sources with different tz-awareness
    # (candle timestamps are naive, DB-recorded exit times are UTC-aware) —
    # treat naive as UTC rather than crash on the subtraction.
    if entry_dt.tzinfo is None:
        entry_dt = entry_dt.replace(tzinfo=timezone.utc)
    if exit_dt.tzinfo is None:
        exit_dt = exit_dt.replace(tzinfo=timezone.utc)

    total_minutes = (exit_dt - entry_dt).total_seconds() / 60
    if total_minutes < 0:
        return ""
    if total_minutes < 60:
        return f"{round(total_minutes)} min"
    if total_minutes < 1440:
        hours, minutes = divmod(round(total_minutes), 60)
        return f"{hours} hr {minutes} min" if minutes else f"{hours} hr"
    days, rem_minutes = divmod(round(total_minutes), 1440)
    hours = rem_minutes // 60
    return f"{days}d {hours}hr" if hours else f"{days}d"
