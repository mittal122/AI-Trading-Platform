import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.ai import kronos
from backend.app.core.rate_limit import limiter
from backend.app.core.saas_config import saas_config
from backend.app.core.security_config import security_config
from backend.app.db.database import create_tables

logger = logging.getLogger("uvicorn.error")


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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak raw exception text (DB constraints, dependency/upstream
    internals) to clients. The full traceback goes to the server log; the
    client gets a generic 500 unless DEBUG_ERRORS is explicitly on."""
    logger.error("Unhandled error on %s %s\n%s", request.method, request.url.path,
                 "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    detail = str(exc) if security_config.DEBUG_ERRORS else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers on every response. The API serves JSON, not
    HTML, so a strict CSP + nosniff + frame-deny cost nothing and block the
    common clickjacking / MIME-sniffing / referrer-leak vectors. The SPA is
    served by nginx, which sets its own headers (docker/nginx.conf)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Global static rate-limit floor (applies to every route as a DoS/cost
# backstop). Per-tier @limiter.limit decorators still add stricter dynamic
# caps on top for specific routes.
app.add_middleware(SlowAPIMiddleware)

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