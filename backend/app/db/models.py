"""SQLAlchemy ORM models for the AI Trading Platform."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Trade(Base):
    """Closed trade record — paper, live, or backtest."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY / SELL
    mode: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # PAPER / LIVE / BACKTEST
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, nullable=False)
    pnl_percent: Mapped[float] = mapped_column(Float, nullable=False)
    exit_reason: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    entry_timestamp: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    exit_timestamp: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    __table_args__ = (
        Index("ix_trades_symbol_strategy", "symbol", "strategy"),
        Index("ix_trades_mode_created", "mode", "created_at"),
    )


class BacktestRun(Base):
    """Persisted backtest result — summary columns + full detail analytics."""

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    interval: Mapped[str] = mapped_column(String(5), nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)
    final_balance: Mapped[float] = mapped_column(Float, nullable=False)
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    # Detail analytics — shown in the frontend's expandable detail row
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_win: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_loss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expectancy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sortino_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calmar_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Avg candles winning trades took to hit target, at this interval — lets
    # users compare which timeframe a strategy resolves fastest/most reliably on
    avg_candles_to_win: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_time_to_win_display: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )


class Position(Base):
    """Open position snapshot (optional persistence)."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(4), nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    take_profit: Mapped[float] = mapped_column(Float, nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class Portfolio(Base):
    """Portfolio equity snapshot (time-series)."""

    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class Strategy(Base):
    """Strategy configuration registry."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class User(Base):
    """User account — SaaS phase."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class ApiKey(Base):
    """User-issued API key. Only the hash is stored — the raw key is shown once at creation."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)  # shown in UI for identification
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
