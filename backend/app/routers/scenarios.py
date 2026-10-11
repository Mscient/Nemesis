"""
Scenario endpoints — B9.
POST /api/skus/{sku}/scenarios is defined in skus.py.
This router handles the adjustment patch endpoint (B10).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.schemas import AdjustmentPatch, AdjustmentRecord
from app.services import orchestration as svc

router = APIRouter(tags=["adjustments"])


@router.patch("/adjustments/{adjustment_id}", response_model=AdjustmentRecord)
async def update_adjustment(
    adjustment_id: int,
    body: AdjustmentPatch,
    db: AsyncSession = Depends(get_db),
):
    """User accepts or rejects an AI-proposed adjustment."""
    if settings.mock_mode:
        return {
            "id": adjustment_id, "sku": "WATER-500",
            "start_date": "2026-10-15", "end_date": "2026-10-22",
            "multiplier": 1.3, "rationale": "Mock event", "confidence": 0.75,
            "source": "ai", "status": body.status,
        }
    result = await svc.update_adjustment_service(db, adjustment_id, body.status)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Adjustment {adjustment_id} not found")
    return result
