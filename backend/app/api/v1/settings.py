"""User-facing exchange credential storage — lets a Binance account's own
API key/secret be entered from the Settings page instead of only .env.
Global row (not per-user) since no login UI exists yet — see
ExchangeCredentials model docstring."""

from fastapi import APIRouter, Depends

from backend.app.api.deps import require_admin
from backend.app.schemas.exchange_credentials import BinanceKeyStatus, SaveBinanceKeysRequest
from backend.app.services.db_service import DatabaseService

router = APIRouter(prefix="/settings", tags=["settings"])


# Writing/deleting exchange credentials is admin-gated (see require_admin):
# open on single-operator localhost, locked when ADMIN_API_TOKEN is set.
@router.post("/binance-keys", response_model=BinanceKeyStatus, dependencies=[Depends(require_admin)])
async def save_binance_keys(req: SaveBinanceKeysRequest) -> BinanceKeyStatus:
    svc = DatabaseService()
    preview = await svc.save_exchange_credentials(req.api_key.strip(), req.api_secret.strip())
    return BinanceKeyStatus(configured=True, key_preview=preview)


@router.get("/binance-keys/status", response_model=BinanceKeyStatus)
async def get_binance_key_status() -> BinanceKeyStatus:
    # Status only exposes a masked preview (never the raw secret), so it
    # stays readable — the UI needs it to show "configured / not configured".
    svc = DatabaseService()
    status = await svc.get_exchange_credentials_status()
    return BinanceKeyStatus(**status)


@router.delete("/binance-keys", response_model=BinanceKeyStatus, dependencies=[Depends(require_admin)])
async def delete_binance_keys() -> BinanceKeyStatus:
    svc = DatabaseService()
    await svc.delete_exchange_credentials()
    return BinanceKeyStatus(configured=False, key_preview=None)
