"""User-facing exchange credential storage — lets a Binance account's own
API key/secret be entered from the Settings page instead of only .env.
Global row (not per-user) since no login UI exists yet — see
ExchangeCredentials model docstring."""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import require_admin
from backend.app.schemas.exchange_credentials import BinanceKeyStatus, SaveBinanceKeysRequest
from backend.app.services.db_service import DatabaseService
from backend.app.services.providers.binance_provider import configure_credentials

router = APIRouter(prefix="/settings", tags=["settings"])


# Writing/deleting exchange credentials is admin-gated (see require_admin):
# open on single-operator localhost, locked when ADMIN_API_TOKEN is set.
@router.post("/binance-keys", response_model=BinanceKeyStatus, dependencies=[Depends(require_admin)])
async def save_binance_keys(req: SaveBinanceKeysRequest) -> BinanceKeyStatus:
    svc = DatabaseService()
    try:
        preview = await svc.save_exchange_credentials(req.api_key.strip(), req.api_secret.strip())
    except RuntimeError as exc:
        # Missing ENCRYPTION_KEY/JWT_SECRET — surface the reason instead of a
        # masked 500 (the frontend shows `detail` verbatim).
        raise HTTPException(status_code=503, detail=str(exc))
    # Apply immediately — market data fetching switches to these keys now,
    # not on next restart.
    configure_credentials(req.api_key.strip(), req.api_secret.strip())
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
    configure_credentials()  # revert to env keys or keyless
    return BinanceKeyStatus(configured=False, key_preview=None)
