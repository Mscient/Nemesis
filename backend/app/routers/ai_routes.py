"""
AI status endpoint — B10.
POST /api/skus/{sku}/anomalies/suggest is in anomalies.py.
POST /api/skus/{sku}/explain is in skus.py.
POST /api/skus/{sku}/adjustments/propose is in skus.py.
"""
from __future__ import annotations

from fastapi import APIRouter
from app.config import settings
from app.schemas import AIStatusResponse

router = APIRouter(tags=["ai"])


@router.get("/ai/status", response_model=AIStatusResponse)
def ai_status():
    """Return AI enabled status, provider and model name."""
    return AIStatusResponse(
        enabled=settings.ai_enabled,
        provider=settings.llm_provider,
        model=settings.llm_model,
    )
