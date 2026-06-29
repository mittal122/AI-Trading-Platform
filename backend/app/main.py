from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.v1.router import api_router
from backend.app.core.ai import kronos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    """

    kronos.load()

    yield

    print("Shutting down...")


app = FastAPI(
    title="AI Trading Platform",
    description="AI-powered trading platform using Kronos Foundation Model",
    version="1.0.0",
    lifespan=lifespan,
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