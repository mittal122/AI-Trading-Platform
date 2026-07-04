"""User-facing exchange credential storage — lets a Binance account's own
API key/secret be entered from the Settings page instead of only .env.
Global row (not per-user) since no login UI exists yet — see
ExchangeCredentials model docstring."""

from fastapi import APIRouter

from backend.app.schemas.exchange_credentials import BinanceKeyStatus, SaveBinanceKeysRequest
from backend.app.services.db_service import DatabaseService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.post("/binance-keys", response_model=BinanceKeyStatus)
async def save_binance_keys(req: SaveBinanceKeysRequest) -> BinanceKeyStatus:
    svc = DatabaseService()
    preview = await svc.save_exchange_credentials(req.api_key.strip(), req.api_secret.strip())
    return BinanceKeyStatus(configured=True, key_preview=preview)


@router.get("/binance-keys/status", response_model=BinanceKeyStatus)
async def get_binance_key_status() -> BinanceKeyStatus:
    svc = DatabaseService()
    status = await svc.get_exchange_credentials_status()
    return BinanceKeyStatus(**status)


@router.delete("/binance-keys", response_model=BinanceKeyStatus)
async def delete_binance_keys() -> BinanceKeyStatus:
    svc = DatabaseService()
    await svc.delete_exchange_credentials()
    return BinanceKeyStatus(configured=False, key_preview=None)
