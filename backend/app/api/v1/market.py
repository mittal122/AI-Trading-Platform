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

from backend.app.services.market_service import MarketService

router = APIRouter(
    prefix="/market",
    tags=["Market"],
)

market_service = MarketService()


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
):

    df = market_service.get_market_data(
        symbol=symbol,
        interval=interval,
        limit=limit,
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