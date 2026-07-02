import os


class SaaSConfig:

    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]

    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    API_KEY_PREFIX = "sk_live_"

    # Rate limits — requests per minute, by subscription tier
    RATE_LIMIT_FREE = os.getenv("RATE_LIMIT_FREE", "60/minute")
    RATE_LIMIT_PRO = os.getenv("RATE_LIMIT_PRO", "300/minute")
    RATE_LIMIT_ENTERPRISE = os.getenv("RATE_LIMIT_ENTERPRISE", "2000/minute")

    # Stripe price IDs per tier (configure in Stripe dashboard, paste IDs here via env)
    STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")
    STRIPE_PRICE_ENTERPRISE = os.getenv("STRIPE_PRICE_ENTERPRISE", "")

    VALID_TIERS = ("free", "pro", "enterprise")


saas_config = SaaSConfig()
