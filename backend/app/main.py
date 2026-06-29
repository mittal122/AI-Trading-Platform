from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.core.ai import kronos


@asynccontextmanager
async def lifespan(app: FastAPI):

    kronos.load()

    yield

    print("Shutting down...")


app = FastAPI(
    title="AI Trading Platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():

    return {
        "status": "running"
    }