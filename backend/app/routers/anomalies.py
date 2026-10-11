"""
Anomaly endpoints — B7.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.schemas import AnomalyPatch, AnomalyRecord, AnomalySuggestRequest
from app.services.mock_mode import load_mock
from app.services import orchestration as svc

router = APIRouter(tags=["anomalies"])


@router.get("/skus/{sku}/anomalies", response_model=list[AnomalyRecord])
async def list_anomalies(sku: str, db: AsyncSession = Depends(get_db)):
    """List all flagged anomalies for a SKU."""
    if settings.mock_mode:
        return load_mock("anomalies")
    return await svc.list_anomalies(db, sku)


@router.post("/skus/{sku}/anomalies/suggest", response_model=list[AnomalyRecord])
async def suggest_anomaly_labels(
    sku: str,
    body: AnomalySuggestRequest = AnomalySuggestRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Request AI label suggestions for open anomalies (stored as source='ai')."""
    if settings.mock_mode:
        return load_mock("anomalies")
    return await svc.suggest_anomaly_labels_service(db, sku, body.anomaly_ids)


@router.patch("/anomalies/{anomaly_id}", response_model=AnomalyRecord)
async def reclassify_anomaly(
    anomaly_id: int,
    body: AnomalyPatch,
    db: AsyncSession = Depends(get_db),
):
    """User confirms or reclassifies an anomaly (stored as source='user')."""
    if settings.mock_mode:
        return {
            "id": anomaly_id, "sku": "WATER-500", "date": "2026-09-03",
            "value": 35.0, "expected_value": 10.0, "robust_z": 4.2,
            "flags": ["high_spike"], "cls": body.cls, "treatment": "keep_with_promo_flag",
            "source": "user", "status": body.status, "rationale": body.rationale,
        }
    result = await svc.reclassify_anomaly(db, anomaly_id, body.cls, body.status, body.rationale)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")
    return result
