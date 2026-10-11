"""
conftest.py — force SQLite for all backend tests (no PostgreSQL needed).
"""
import os

SQLITE_URL = "sqlite+aiosqlite:///./test_stocksense.db"

# Set env vars FIRST — before any app module is imported
os.environ["DATABASE_URL"] = SQLITE_URL
os.environ["AI_ENABLED"] = "false"
os.environ["MOCK_MODE"] = "false"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["LLM_API_KEY"] = "mock-key"

# Monkey-patch settings object in case it was already instantiated
import importlib
try:
    from app import config as _cfg
    object.__setattr__(_cfg.settings, "database_url", SQLITE_URL)
except Exception:
    pass  # app not yet imported — env vars above will take effect

# Re-create the engine with SQLite URL so session.py picks it up
try:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.db import session as _sess
    _new_engine = create_async_engine(SQLITE_URL, echo=False, future=True)
    _sess.engine = _new_engine
    _sess.AsyncSessionLocal = async_sessionmaker(
        bind=_new_engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception:
    pass
