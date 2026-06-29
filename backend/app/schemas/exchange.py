from pydantic import BaseModel


class ExchangeSymbol(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str


class SymbolsResponse(BaseModel):
    provider: str
    symbols: list[ExchangeSymbol]


class IntervalsResponse(BaseModel):
    provider: str
    intervals: list[str]


class ProvidersResponse(BaseModel):
    providers: list[str]