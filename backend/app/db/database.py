"""
Async SQLAlchemy engine + session factory.

DATABASE_URL env var controls the backend:
  - Not set → SQLite (sqlite+aiosqlite:///./trading.db)  — zero-config default
  - Set      → use as-is (postgresql+asyncpg://... for production)
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./trading.db")

# connect_args only needed for SQLite
_connect_args = {"check_same_thread": False} if "sqlite" in _DATABASE_URL else {}

engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables() -> None:
    """Create all tables if they don't exist. Called at app startup."""
    from backend.app.db import models  # noqa: F401 — registers models with Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
