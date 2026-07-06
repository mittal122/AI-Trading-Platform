from typing import Optional

from fastapi import APIRouter, Query

from backend.app.schemas.market import LiveMarketResponse
from backend.app.schemas.history import (
    HistoricalMarketResponse,
    HistoricalCandle,
)
from backend.app.schemas.exchange import (
    SymbolsResponse,
    IntervalsResponse,
    ProvidersResponse,
)
from backend.app.schemas.market_overview import (
    BuyPressureResponse,
    DepthPressureResponse,
    FundingResponse,
    MarketOverviewResponse,
    Ticker24h,
    VolumeScanResponse,
    VolumeScanRow,
    WatchlistResponse,
)

from backend.app.services.market_service import MarketService
from backend.app.services.market_scanner import VolumeScanner

# Breadth/movers ignore pairs below this 24h quote volume — thousands of
# near-dead micro-caps would otherwise dominate the statistics.
_OVERVIEW_MIN_QUOTE_VOLUME = 1_000_000.0

# Stablecoin-vs-USDT pairs (USDC/USDT etc.) always top volume rankings and
# never move — pure noise in movers/volume-leader lists.
_STABLE_BASES = {"USDC", "FDUSD", "TUSD", "DAI", "BUSD", "USDP", "EUR", "AEUR", "XUSD"}

# Volume-spike scanner bounds — averaging window (candle count) and how many
# symbols one scan may cover (each symbol is one Binance klines call).
_VOLUME_SCAN_MAX_SYMBOLS = 50

router = APIRouter(
    prefix="/market",
    tags=["Market"],
)

market_service = MarketService()
volume_scanner = VolumeScanner()


@router.get(
    "/live",
    response_model=LiveMarketResponse,
)
def live_market(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
):

    df = market_service.get_market_data(
        symbol=symbol,
        interval=interval,
        limit=1,
    )

    candle = df.iloc[-1]

    return LiveMarketResponse(
        symbol=symbol,
        interval=interval,
        timestamp=candle["timestamps"].isoformat(),
        open=float(candle["open"]),
        high=float(candle["high"]),
        low=float(candle["low"]),
        close=float(candle["close"]),
        volume=float(candle["volume"]),
        amount=float(candle["amount"]),
    )


@router.get(
    "/history",
    response_model=HistoricalMarketResponse,
)
def historical_market(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
    limit: int = Query(
        default=500,
        ge=1,
        le=1000,
    ),
    end_time: Optional[int] = Query(
        default=None,
        description="Unix ms — return `limit` candles ending at/before this timestamp instead of the most recent ones (for loading older history).",
    ),
):

    df = market_service.get_market_data(
        symbol=symbol,
        interval=interval,
        limit=limit,
        end_time=end_time,
    )

    candles = []

    for _, row in df.iterrows():

        candles.append(
            HistoricalCandle(
                timestamp=row["timestamps"].isoformat(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                amount=float(row["amount"]),
            )
        )

    return HistoricalMarketResponse(
        symbol=symbol,
        interval=interval,
        candles=candles,
    )


@router.get(
    "/symbols",
    response_model=SymbolsResponse,
)
def get_symbols():

    return SymbolsResponse(
        provider=market_service.get_provider_name(),
        symbols=market_service.get_symbols(),
    )


@router.get(
    "/intervals",
    response_model=IntervalsResponse,
)
def get_intervals():

    return IntervalsResponse(
        provider=market_service.get_provider_name(),
        intervals=market_service.get_supported_intervals(),
    )


@router.get(
    "/providers",
    response_model=ProvidersResponse,
)
def get_providers():

    return ProvidersResponse(
        providers=[
            market_service.get_provider_name(),
        ]
    )

# ── Market overview / order-flow endpoints (advanced Dashboard) ──────────────


@router.get(
    "/overview",
    response_model=MarketOverviewResponse,
)
def market_overview():
    """Whole-market snapshot from one cached 24h-ticker pull: BTC/ETH,
    breadth (advancers vs decliners), average move, top movers, and volume
    leaders — the "is the market risk-on or risk-off right now" read."""
    tickers = [Ticker24h(**t) for t in market_service.get_tickers_24h()]
    liquid = [
        t for t in tickers
        if t.quote_volume >= _OVERVIEW_MIN_QUOTE_VOLUME
        and t.symbol[:-4] not in _STABLE_BASES  # strip 'USDT' suffix
    ]
    by_symbol = {t.symbol: t for t in tickers}

    advancers = sum(1 for t in liquid if t.price_change_pct > 0)
    decliners = sum(1 for t in liquid if t.price_change_pct < 0)
    avg_change = sum(t.price_change_pct for t in liquid) / len(liquid) if liquid else 0.0

    by_change = sorted(liquid, key=lambda t: t.price_change_pct, reverse=True)
    by_volume = sorted(liquid, key=lambda t: t.quote_volume, reverse=True)

    return MarketOverviewResponse(
        btc=by_symbol.get("BTCUSDT"),
        eth=by_symbol.get("ETHUSDT"),
        advancers=advancers,
        decliners=decliners,
        avg_change_pct=round(avg_change, 2),
        total_quote_volume=round(sum(t.quote_volume for t in liquid), 2),
        counted_pairs=len(liquid),
        top_gainers=by_change[:8],
        top_losers=by_change[-8:][::-1],
        volume_leaders=by_volume[:8],
    )


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
)
def watchlist_tickers(
    symbols: str = Query(description="Comma-separated symbols, e.g. BTCUSDT,ETHUSDT"),
):
    """24h stats for exactly the requested symbols (order preserved)."""
    wanted = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    by_symbol = {t["symbol"]: t for t in market_service.get_tickers_24h()}
    return WatchlistResponse(
        tickers=[Ticker24h(**by_symbol[s]) for s in wanted if s in by_symbol],
    )


@router.get(
    "/depth-pressure",
    response_model=DepthPressureResponse,
)
def depth_pressure(
    symbol: str = Query(default="BTCUSDT"),
    limit: int = Query(default=100, ge=5, le=500),
):
    """Order-book imbalance: resting bid vs ask notional near the touch,
    plus the single biggest wall on each side."""
    return DepthPressureResponse(**market_service.get_depth_summary(symbol, limit=limit))


@router.get(
    "/buy-pressure",
    response_model=BuyPressureResponse,
)
def buy_pressure(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
    limit: int = Query(default=20, ge=5, le=200),
):
    """Aggressive (taker) buy share of traded volume over the last N candles
    — who is hitting the market: buyers or sellers."""
    return BuyPressureResponse(**market_service.get_buy_pressure(symbol, interval, limit=limit))


@router.get(
    "/volume-scan",
    response_model=VolumeScanResponse,
)
def volume_scan(
    symbols: str = Query(description="Comma-separated symbols, e.g. BTCUSDT,ETHUSDT"),
    interval: str = Query(default="5m"),
    window: int = Query(default=20, ge=5, le=200),
):
    """Volume-spike + order-push scan across a watchlist on one timeframe.

    One row per symbol: last closed candle's volume vs the prior `window`
    candles' mean (spike ratio), how many orders (trades) were pushed, and the
    biggest single-candle push in the window. Rows come back sorted by spike
    ratio (hottest first) so the maximum order push floats to the top. A symbol
    that fails to fetch returns a row with `error` set — it never kills the batch.
    """
    wanted = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    wanted = wanted[:_VOLUME_SCAN_MAX_SYMBOLS]

    rows: list[VolumeScanRow] = []
    for sym in wanted:
        try:
            rows.append(VolumeScanRow(**market_service.get_volume_scan(sym, interval, window=window)))
        except Exception as exc:  # per-symbol isolation — a delisted/typo symbol can't 500 the scan
            rows.append(VolumeScanRow(
                symbol=sym, interval=interval, time="", ltp=0.0,
                volume_window=0.0, volume_average=0.0, spike_ratio=0.0,
                orders=0, avg_orders=0.0, max_push_volume=0.0, max_push_ratio=0.0,
                error=str(exc) or "scan failed",
            ))

    rows.sort(key=lambda r: r.spike_ratio, reverse=True)
    return VolumeScanResponse(interval=interval, window=window, rows=rows)


@router.get(
    "/volume-scan/market",
    response_model=VolumeScanResponse,
)
def volume_scan_market(
    interval: str = Query(default="5m"),
    window: int = Query(default=20, ge=5, le=200),
    top: int = Query(default=300, ge=10, le=400),
    limit: int = Query(default=40, ge=1, le=100),
):
    """Whole-market order-push scan: read the top `top` liquid USDT pairs, rank
    by blended surge x size, return the `limit` hottest. Heavier than the
    watchlist scan (one Binance klines call per coin, run concurrently) — meant
    to be triggered on demand, not polled every few seconds."""
    return VolumeScanResponse(**volume_scanner.scan_market(
        interval=interval, window=window, top=top, limit=limit))


@router.get(
    "/funding",
    response_model=FundingResponse | None,
)
def funding(symbol: str = Query(default="BTCUSDT")):
    """Perpetual funding rate + mark price (positioning read). Null when the
    symbol has no perp market or futures data is unreachable."""
    data = market_service.get_funding(symbol)
    return FundingResponse(**data) if data else None
