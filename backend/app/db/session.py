"""
SQLAlchemy async session factory and table-creation helper — B3.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings
from app.db.models import Base

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_tables() -> None:
    """Create all tables (used at startup for SQLite dev; use Alembic for Postgres)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
