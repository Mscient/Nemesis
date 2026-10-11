"""
Repository functions (thin async DB wrappers) — B3.
One function per query type; no business logic here.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AdjustmentModel, AIAuditLogModel, AnomalyModel,
    ForecastRunModel,
    SalesRecordModel, ScenarioModel, SkuModel,
)


# helper — so we can import without the circular default params dict
SKU_DEFAULT_PARAMS = dict(
    lead_time_days=5,
    lead_time_std_days=0.0,
    unit_cost=1.0,
    order_cost=50.0,
    holding_cost_per_unit_per_year=2.0,
    stockout_penalty_per_unit=6.0,
    moq=1,
    pack_size=1,
    max_storage=None,
    service_level=0.95,
    on_hand=0.0,
    on_order=0.0,
)


# ─── SKU ──────────────────────────────────────────────────────────────────────

async def get_all_skus(db: AsyncSession) -> Sequence[SkuModel]:
    result = await db.execute(select(SkuModel).order_by(SkuModel.sku))
    return result.scalars().all()


async def get_sku(db: AsyncSession, sku: str) -> Optional[SkuModel]:
    result = await db.execute(select(SkuModel).where(SkuModel.sku == sku))
    return result.scalar_one_or_none()


async def upsert_sku(db: AsyncSession, sku: str, **kwargs) -> SkuModel:
    """Create or return existing SKU row; update fields if provided."""
    obj = await get_sku(db, sku)
    if obj is None:
        params = {**SKU_DEFAULT_PARAMS, **kwargs}
        obj = SkuModel(sku=sku, **params)
        db.add(obj)
        await db.flush()
    else:
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await db.flush()
    return obj


async def update_sku_params(db: AsyncSession, sku: str, **kwargs) -> Optional[SkuModel]:
    obj = await get_sku(db, sku)
    if obj is None:
        return None
    for k, v in kwargs.items():
        setattr(obj, k, v)
    await db.flush()
    return obj


# ─── Sales records ────────────────────────────────────────────────────────────

async def get_sales_records(db: AsyncSession, sku: str) -> Sequence[SalesRecordModel]:
    result = await db.execute(
        select(SalesRecordModel)
        .where(SalesRecordModel.sku == sku)
        .order_by(SalesRecordModel.date)
    )
    return result.scalars().all()


async def bulk_insert_sales(db: AsyncSession, rows: list[dict]) -> int:
    """Insert sales records; skips duplicates by catching IntegrityError per row."""
    inserted = 0
    for row in rows:
        existing = await db.execute(
            select(SalesRecordModel).where(
                SalesRecordModel.sku == row["sku"],
                SalesRecordModel.date == row["date"],
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(SalesRecordModel(**row))
            inserted += 1
    await db.flush()
    return inserted


# ─── Anomalies ────────────────────────────────────────────────────────────────

async def get_anomalies(db: AsyncSession, sku: str) -> Sequence[AnomalyModel]:
    result = await db.execute(
        select(AnomalyModel).where(AnomalyModel.sku == sku).order_by(AnomalyModel.date)
    )
    return result.scalars().all()


async def get_anomaly_by_id(db: AsyncSession, anomaly_id: int) -> Optional[AnomalyModel]:
    result = await db.execute(select(AnomalyModel).where(AnomalyModel.id == anomaly_id))
    return result.scalar_one_or_none()


async def get_open_anomalies(db: AsyncSession, sku: str) -> Sequence[AnomalyModel]:
    result = await db.execute(
        select(AnomalyModel).where(AnomalyModel.sku == sku, AnomalyModel.status == "open")
    )
    return result.scalars().all()


async def bulk_insert_anomalies(db: AsyncSession, rows: list[dict]) -> int:
    count = 0
    for row in rows:
        db.add(AnomalyModel(**row))
        count += 1
    await db.flush()
    return count


async def update_anomaly(
    db: AsyncSession,
    anomaly_id: int,
    cls: str,
    status: str,
    source: str = "user",
    rationale: Optional[str] = None,
) -> Optional[AnomalyModel]:
    obj = await get_anomaly_by_id(db, anomaly_id)
    if obj is None:
        return None
    obj.cls = cls
    obj.status = status
    obj.source = source
    obj.rationale = rationale
    await db.flush()
    return obj


# ─── Forecast runs ────────────────────────────────────────────────────────────

async def save_forecast_run(db: AsyncSession, sku: str, data: dict) -> ForecastRunModel:
    obj = ForecastRunModel(
        sku=sku,
        model_used=data["model_used"],
        horizon_days=data.get("horizon_days", 14),
        mu_d=data["mu_d"],
        sigma_d=data["sigma_d"],
        confidence=data["confidence"],
        predictions_json=json.dumps(data.get("predictions", [])),
        metrics_json=json.dumps(data.get("metrics", [])),
        warnings_json=json.dumps(data.get("warnings", [])),
    )
    db.add(obj)
    await db.flush()
    return obj


# ─── Scenarios ────────────────────────────────────────────────────────────────

async def save_scenario(db: AsyncSession, sku: str, params: dict, results: dict) -> ScenarioModel:
    obj = ScenarioModel(
        sku=sku,
        params_json=json.dumps(params, default=str),
        results_json=json.dumps(results, default=str),
    )
    db.add(obj)
    await db.flush()
    return obj


# ─── Adjustments ──────────────────────────────────────────────────────────────

async def get_adjustments(db: AsyncSession, sku: str) -> Sequence[AdjustmentModel]:
    result = await db.execute(
        select(AdjustmentModel).where(AdjustmentModel.sku == sku).order_by(AdjustmentModel.id)
    )
    return result.scalars().all()


async def get_accepted_adjustments(db: AsyncSession, sku: str) -> Sequence[AdjustmentModel]:
    result = await db.execute(
        select(AdjustmentModel).where(
            AdjustmentModel.sku == sku,
            AdjustmentModel.status == "accepted",
        )
    )
    return result.scalars().all()


async def get_adjustment_by_id(db: AsyncSession, adj_id: int) -> Optional[AdjustmentModel]:
    result = await db.execute(select(AdjustmentModel).where(AdjustmentModel.id == adj_id))
    return result.scalar_one_or_none()


async def save_adjustment(db: AsyncSession, row: dict) -> AdjustmentModel:
    obj = AdjustmentModel(**row)
    db.add(obj)
    await db.flush()
    return obj


async def update_adjustment_status(
    db: AsyncSession, adj_id: int, status: str
) -> Optional[AdjustmentModel]:
    obj = await get_adjustment_by_id(db, adj_id)
    if obj is None:
        return None
    obj.status = status
    await db.flush()
    return obj


# ─── AI audit log ─────────────────────────────────────────────────────────────

async def log_ai_call(db: AsyncSession, data: dict) -> AIAuditLogModel:
    obj = AIAuditLogModel(**data)
    db.add(obj)
    await db.flush()
    return obj
