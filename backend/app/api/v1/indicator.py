from fastapi import APIRouter, Query

from backend.app.schemas.indicator import (
    IndicatorResponse,
    IndicatorValues,
)
from backend.app.services.indicator_service import (
    IndicatorService,
)

router = APIRouter(
    prefix="/indicator",
    tags=["Indicators"],
)

indicator_service = IndicatorService()


@router.get(
    "",
    response_model=IndicatorResponse,
)
def get_indicators(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="5m"),
):

    values = indicator_service.calculate(
        symbol=symbol,
        interval=interval,
    )

    return IndicatorResponse(
        symbol=symbol,
        interval=interval,
        indicators=IndicatorValues(**values),
    )