"""
Dataset upload endpoint — B4.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.schemas import DatasetUploadResponse
from app.services.mock_mode import load_mock
from app.services.ingestion import ingest_csv

router = APIRouter(tags=["datasets"])


@router.post("/datasets", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload sales.csv: structural validation, persistence, and anomaly detection."""
    if settings.mock_mode:
        return DatasetUploadResponse(
            filename=file.filename or "sales.csv",
            status="accepted",
            rows_ingested=365,
            skus_created=3,
            anomalies_detected=5,
            errors=[],
        )

    content = await file.read()
    filename = file.filename or "upload.csv"
    is_synthetic = "synthetic" in filename.lower() or "sample" in filename.lower()
    return await ingest_csv(db, filename, content, is_synthetic=is_synthetic)
