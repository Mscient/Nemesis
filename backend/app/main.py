import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import setup_logging
from app.db import init_db
from app.routes import chat, health, items


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    setup_logging()
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Hackathon API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Read allowed origins from CORS_ORIGINS env var (comma-separated), defaulting to http://localhost:5173
    cors_raw = os.getenv("CORS_ORIGINS", settings.cors_origins)
    allowed_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
    if not allowed_origins:
        allowed_origins = ["http://localhost:5173"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(items.router, prefix="/api", tags=["items"])

    return app


app = create_app()
