from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    tier: str  # "pro" or "enterprise"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionStatusResponse(BaseModel):
    tier: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    is_active: bool
