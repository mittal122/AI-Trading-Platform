"""StripeService — checkout sessions + webhook-driven subscription sync.

Requires STRIPE_SECRET_KEY (and STRIPE_WEBHOOK_SECRET for webhook verification).
Raises RuntimeError if unconfigured — callers surface this as 503, same pattern
as backend/app/services/ai/llm_client.py.
"""

import os

import stripe

from backend.app.core.saas_config import saas_config
from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import User
from backend.app.db.repository.user_repo import UserRepository

_PRICE_BY_TIER = {
    "pro": saas_config.STRIPE_PRICE_PRO,
    "enterprise": saas_config.STRIPE_PRICE_ENTERPRISE,
}


class StripeService:

    def __init__(self) -> None:
        secret_key = os.getenv("STRIPE_SECRET_KEY")
        if not secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY environment variable not set")
        stripe.api_key = secret_key
        self._webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    def create_checkout_session(
        self, user: User, tier: str, success_url: str, cancel_url: str
    ) -> str:
        price_id = _PRICE_BY_TIER.get(tier)
        if not price_id:
            raise ValueError(f"No Stripe price configured for tier '{tier}'")

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user.email if not user.stripe_customer_id else None,
            customer=user.stripe_customer_id or None,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(user.id),
            metadata={"user_id": str(user.id), "tier": tier},
        )
        return session.url

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        if not self._webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET environment variable not set")
        event = stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        return event

    async def handle_webhook_event(self, event: dict) -> None:
        """Sync user tier + Stripe IDs from subscription lifecycle events."""
        event_type = event["type"]
        obj = event["data"]["object"]

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)

            if event_type == "checkout.session.completed":
                user_id = int(obj["metadata"]["user_id"])
                tier = obj["metadata"]["tier"]
                user = await repo.get_by_id(user_id)
                if user:
                    await repo.update_stripe_ids(
                        user,
                        customer_id=obj.get("customer"),
                        subscription_id=obj.get("subscription"),
                    )
                    await repo.update_tier(user, tier)

            elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
                if obj.get("status") in ("canceled", "unpaid", "incomplete_expired"):
                    user = await repo.get_by_stripe_customer_id(obj["customer"])
                    if user:
                        await repo.update_tier(user, "free")
