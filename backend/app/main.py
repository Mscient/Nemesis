"""
FastAPI application entry-point — B1, B11.
Sets up CORS, logging, global error handlers, and mounts all routers.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import create_tables
from app.routers import health, skus, datasets, anomalies, scenarios, ai_routes

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (SQLite dev mode). Use Alembic for Postgres."""
    if "sqlite" in settings.database_url:
        await create_tables()
    yield


app = FastAPI(
    title="StockSense API",
    version="1.0.0",
    description=(
        "Adaptive Inventory Replenishment Engine — "
        "FastAPI backend exposing demand forecasting, "
        "anomaly detection, reorder recommendations and scenario simulation."
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:80", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global error handlers (B11) ──────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Map Pydantic validation errors to the standard error envelope."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first.get("loc", [])) if first else None
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": first.get("msg", "Validation error"),
                "field": field,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — return 500 with the standard error envelope."""
    logging.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "field": None,
            }
        },
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(health.router, prefix="/api")
app.include_router(skus.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(anomalies.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(ai_routes.router, prefix="/api")
