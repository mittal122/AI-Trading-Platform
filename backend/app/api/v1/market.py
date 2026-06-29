from fastapi import APIRouter, Query

from backend.app.schemas.market import LiveMarketResponse
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