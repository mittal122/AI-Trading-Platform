from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.api.v1.router import api_router
from backend.app.core.ai import kronos
from backend.app.core.rate_limit import limiter
from backend.app.core.saas_config import saas_config
from backend.app.db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    kronos.load()
    await create_tables()
    print("Database tables ready")

    yield

    print("Shutting down...")


app = FastAPI(
    title="AI Trading Platform",
    description="AI-powered trading platform using Kronos Foundation Model",
    version="1.0.0",
    lifespan=lifespan,
)

# Per-tier rate limiting — applied via @limiter.limit(tier_rate_limit) decorators
# on individual routes (auth + AI + trading endpoints). No global middleware:
# slowapi's SlowAPIMiddleware only supports static default limits, not
# per-request dynamic ones — see backend/app/core/rate_limit.py.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=saas_config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get(
    "/",
    tags=["Health"],
)
def root():

    return {
        "status": "running",
        "service": "AI Trading Platform",
        "version": "1.0.0",
    }