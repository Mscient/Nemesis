"""
SKU endpoints — B5, B6, B8, B9, B10 (adjustments & explain).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.schemas import (
    AdjustmentPatch, AdjustmentRecord, AnomalyRecord, AnomalySuggestRequest,
    EvaluationResponse, ExplainRequest, ExplainResponse,
    ForecastResponse, ProposeAdjustmentsRequest, RecommendationResponse,
    ScenarioRequest, ScenarioResponse, SkuDetail, SkuParams, SkuSummary,
    SkuHistoryResponse,
)
from app.services.mock_mode import load_mock
from app.services import orchestration as svc

router = APIRouter(tags=["skus"])


# ─── B5: SKU list & detail ────────────────────────────────────────────────────

@router.get("/skus", response_model=list[SkuSummary])
async def list_skus(db: AsyncSession = Depends(get_db)):
    """List all SKUs with status (OK / REORDER / AT_RISK)."""
    if settings.mock_mode:
        return load_mock("skus")
    return await svc.list_skus_with_status(db)


@router.get("/skus/{sku}", response_model=SkuDetail)
async def get_sku(sku: str, db: AsyncSession = Depends(get_db)):
    """Get SKU detail including parameters."""
    if settings.mock_mode:
        return SkuDetail(
            sku=sku,
            name=f"{sku} (mock)",
            status="OK",
            params=SkuParams(lead_time_days=5, unit_cost=8.0, order_cost=50, holding_cost_per_unit_per_year=2.0, stockout_penalty_per_unit=6.0),
        )
    result = await svc.get_sku_detail(db, sku)
    if result is None:
        raise HTTPException(status_code=404, detail=f"SKU '{sku}' not found")
    return result


@router.put("/skus/{sku}/params", response_model=SkuDetail)
async def update_sku_params(sku: str, params: SkuParams, db: AsyncSession = Depends(get_db)):
    """Update SKU parameters with validation."""
    if settings.mock_mode:
        return SkuDetail(sku=sku, name=f"{sku} (mock)", status="OK", params=params)
    result = await svc.update_sku_params_service(db, sku, params)
    if result is None:
        raise HTTPException(status_code=404, detail=f"SKU '{sku}' not found")
    return result


@router.get("/skus/{sku}/history", response_model=SkuHistoryResponse)
async def get_sku_history(sku: str, db: AsyncSession = Depends(get_db)):
    """Get cleaned and raw sales history."""
    if settings.mock_mode:
        return SkuHistoryResponse(sku=sku, raw=[], cleaned=[])
    return await svc.get_sku_history(db, sku)


# ─── B6: Forecast & evaluation ────────────────────────────────────────────────

@router.get("/skus/{sku}/forecast", response_model=ForecastResponse)
async def get_forecast(
    sku: str,
    horizon: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Demand forecast + holdout evaluation summary."""
    if settings.mock_mode:
        return load_mock("forecast")
    result = await svc.get_forecast(db, sku, horizon)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for SKU '{sku}'")
    return result


@router.get("/skus/{sku}/evaluation", response_model=EvaluationResponse)
async def get_evaluation(sku: str, db: AsyncSession = Depends(get_db)):
    """Baseline vs proposed holdout comparison."""
    if settings.mock_mode:
        return load_mock("evaluation")
    result = await svc.get_evaluation(db, sku)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for SKU '{sku}'")
    return result


# ─── B8: Recommendation ───────────────────────────────────────────────────────

@router.post("/skus/{sku}/recommendation", response_model=RecommendationResponse)
async def compute_recommendation(sku: str, db: AsyncSession = Depends(get_db)):
    """Compute ROP, SS, order quantity and return the full explainable payload."""
    if settings.mock_mode:
        return load_mock("recommendation")
    result = await svc.compute_recommendation_service(db, sku)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for SKU '{sku}'")
    return result


# ─── B9: Scenarios ────────────────────────────────────────────────────────────

@router.post("/skus/{sku}/scenarios", response_model=ScenarioResponse)
async def run_scenario(sku: str, body: ScenarioRequest, db: AsyncSession = Depends(get_db)):
    """Run a what-if simulation (demand surge / supplier delay / combined)."""
    if settings.mock_mode:
        return load_mock("scenario")
    result = await svc.run_scenario_service(
        db, sku,
        scenario_type=body.scenario_type,
        demand_surge_pct=body.demand_surge_pct,
        demand_surge_days=body.demand_surge_days,
        supplier_delay_days=body.supplier_delay_days,
        supplier_delay_sigma=body.supplier_delay_sigma,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for SKU '{sku}'")
    return result


# ─── B10: Adjustments (proposal list & accept/reject) ─────────────────────────

@router.get("/skus/{sku}/adjustments", response_model=list[AdjustmentRecord])
async def list_adjustments(sku: str, db: AsyncSession = Depends(get_db)):
    """List all adjustments (proposed / accepted / rejected)."""
    if settings.mock_mode:
        return []
    return await svc.list_adjustments_service(db, sku)


@router.post("/skus/{sku}/adjustments/propose", response_model=list[AdjustmentRecord])
async def propose_adjustments(
    sku: str, body: ProposeAdjustmentsRequest, db: AsyncSession = Depends(get_db)
):
    """AI proposes forecast adjustments based on event notes."""
    if settings.mock_mode:
        return []
    return await svc.propose_adjustments_service(db, sku, body.event_notes, body.forecast_summary)


# ─── B10: AI explain ──────────────────────────────────────────────────────────

@router.post("/skus/{sku}/explain", response_model=ExplainResponse)
async def explain_recommendation(
    sku: str, body: ExplainRequest, db: AsyncSession = Depends(get_db)
):
    """AI plain-language explanation of the recommendation (template fallback if AI off)."""
    if settings.mock_mode:
        return ExplainResponse(
            sku=sku,
            explanation="Based on the analysis, the system recommends ordering 428 units.",
            used_fallback=True,
        )
    result = await svc.explain_recommendation_service(db, sku, body.audience, body.recommendation)
    return ExplainResponse(sku=sku, **result)
