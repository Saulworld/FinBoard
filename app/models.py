from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("symbol", "market", name="uq_watchlist_symbol_market"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    input_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


Watchlist = WatchlistItem


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("symbol", "market", name="uq_holding_symbol_market"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    input_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class DailyBriefing(Base):
    __tablename__ = "daily_briefings"
    __table_args__ = (UniqueConstraint("date", "ticker", name="uq_briefing_date_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # YYYY-MM-DD
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_range: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_file: Mapped[str] = mapped_column(String(128), default="", nullable=False)


class DailyReport(Base):
    __tablename__ = "daily_reports"
    __table_args__ = (UniqueConstraint("title", "file_type", name="uq_report_title_file_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # YYYY-MM-DD
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # AI, 传统行业, 总览, 其他
    file_type: Mapped[str] = mapped_column(String(8), nullable=False)  # txt, html
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class HoldingTransaction(Base):
    __tablename__ = "holding_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # '加仓', '减仓', '平仓'
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)



