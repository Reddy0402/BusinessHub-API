"""Database connection and table definitions.

Production uses Supabase Postgres: set DATABASE_URL to the project's connection
string (Railway Variables / a local .env file - never commit it).

Without DATABASE_URL the app falls back to an in-memory SQLite database, so tests
and CI need no database or secrets. Data in that mode is lost on restart.

The Postgres tables are created by db/schema.sql (it also enables Row Level
Security). create_all() below only runs for SQLite.
"""

import os
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

SQLITE_MEMORY_URL = "sqlite+pysqlite:///:memory:"

# BIGINT identity in Postgres; plain INTEGER in SQLite so it auto-increments.
Id = BigInteger().with_variant(Integer, "sqlite")


def database_url() -> str:
    """Return the configured database URL, normalised for SQLAlchemy + psycopg 3."""
    url = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'")
    if not url:
        return SQLITE_MEMORY_URL
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _make_engine(url: str):
    if url.startswith("sqlite"):
        # One shared connection, so every request sees the same in-memory database.
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(
        url,
        pool_pre_ping=True,  # drop dead connections (Supabase closes idle ones)
        pool_size=5,
        max_overflow=5,
        # prepare_threshold=None keeps psycopg compatible with Supabase's transaction pooler.
        connect_args={"prepare_threshold": None},
    )


engine = _make_engine(database_url())
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


class Base(DeclarativeBase):
    pass


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Id, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(10), default="pending")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    subtasks: Mapped[list["SubtaskRow"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="SubtaskRow.id"
    )


class SubtaskRow(Base):
    __tablename__ = "subtasks"

    id: Mapped[int] = mapped_column(Id, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(10), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[TaskRow] = relationship(back_populates="subtasks")


class AILogRow(Base):
    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(Id, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(100))
    input_text: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


if is_sqlite():
    Base.metadata.create_all(engine)
