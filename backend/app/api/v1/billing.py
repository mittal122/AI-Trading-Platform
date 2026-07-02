from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.api.deps import get_current_user
from backend.app.core.saas_config import saas_config
from backend.app.db.models import User
from backend.app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionStatusResponse,
)
from backend.app.services.billing.stripe_service import StripeService

router = APIRouter(prefix="/billing", tags=["billing"])


def _get_stripe() -> StripeService:
    try:
        return StripeService()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    req: CheckoutRequest, user: User = Depends(get_current_user)
) -> CheckoutResponse:
    if req.tier not in ("pro", "enterprise"):
        raise HTTPException(status_code=400, detail="tier must be 'pro' or 'enterprise'")
    stripe_service = _get_stripe()
    try:
        url = stripe_service.create_checkout_session(
            user, req.tier, req.success_url, req.cancel_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CheckoutResponse(checkout_url=url)


@router.get("/subscription", response_model=SubscriptionStatusResponse)
def get_subscription(user: User = Depends(get_current_user)) -> SubscriptionStatusResponse:
    return SubscriptionStatusResponse(
        tier=user.tier,
        stripe_customer_id=user.stripe_customer_id,
        stripe_subscription_id=user.stripe_subscription_id,
        is_active=bool(user.is_active),
    )


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request) -> dict:
    stripe_service = _get_stripe()
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = stripe_service.verify_webhook(payload, signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook verification failed: {e}")

    await stripe_service.handle_webhook_event(event)
    return {"received": True}


@router.get("/tiers", include_in_schema=True)
def get_tier_info() -> dict:
    """Public — subscription tier catalog, no auth required."""
    return {
        "tiers": [
            {"name": "free", "rate_limit": saas_config.RATE_LIMIT_FREE},
            {"name": "pro", "rate_limit": saas_config.RATE_LIMIT_PRO},
            {"name": "enterprise", "rate_limit": saas_config.RATE_LIMIT_ENTERPRISE},
        ]
    }
