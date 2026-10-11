"""
Pydantic v2 API schemas — owned by Member B.
All field names are snake_case per the project convention.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Error envelope ───────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    timestamp: str


# ─── AI status ────────────────────────────────────────────────────────────────

class AIStatusResponse(BaseModel):
    enabled: bool
    provider: str
    model: str


# ─── Datasets / Upload ────────────────────────────────────────────────────────

class RowError(BaseModel):
    row: int
    message: str


class DatasetUploadResponse(BaseModel):
    filename: str
    status: str  # "accepted" | "rejected"
    rows_ingested: int
    skus_created: int
    anomalies_detected: int
    errors: list[RowError] = Field(default_factory=list)


# ─── SKU ──────────────────────────────────────────────────────────────────────

class SkuParams(BaseModel):
    lead_time_days: int = Field(..., gt=0)
    lead_time_std_days: float = Field(default=0.0, ge=0)
    unit_cost: float = Field(..., gt=0)
    order_cost: float = Field(..., gt=0)
    holding_cost_per_unit_per_year: float = Field(..., gt=0)
    stockout_penalty_per_unit: float = Field(..., ge=0)
    moq: int = Field(default=1, ge=1)
    pack_size: int = Field(default=1, ge=1)
    max_storage: Optional[int] = None
    service_level: float = Field(default=0.95, gt=0, lt=1)
    on_hand: float = Field(default=0.0, ge=0)
    on_order: float = Field(default=0.0, ge=0)


class SkuSummary(BaseModel):
    sku: str
    name: Optional[str] = None
    status: Literal["OK", "REORDER", "AT_RISK"]
    inventory_position: float
    reorder_point: Optional[float] = None
    on_hand: float
    on_order: float
    is_synthetic: bool = False


class SkuDetail(BaseModel):
    sku: str
    name: Optional[str] = None
    status: Literal["OK", "REORDER", "AT_RISK"]
    params: SkuParams
    is_synthetic: bool = False
    created_at: Optional[datetime] = None


# ─── History ──────────────────────────────────────────────────────────────────

class SalesPoint(BaseModel):
    date: date
    units_sold: float
    on_hand: Optional[float] = None
    promo_flag: Optional[int] = None
    is_anomaly: bool = False
    is_cleaned: bool = False


class SkuHistoryResponse(BaseModel):
    sku: str
    raw: list[SalesPoint]
    cleaned: list[SalesPoint]


# ─── Anomalies ────────────────────────────────────────────────────────────────

class AnomalyRecord(BaseModel):
    id: int
    sku: str
    date: date
    value: float
    expected_value: float
    robust_z: float
    flags: list[str]
    cls: Literal["promotion", "data_error", "stockout_censored", "unknown"]
    treatment: str
    source: Literal["rule", "ai", "user"]
    status: Literal["open", "confirmed", "dismissed"]
    rationale: Optional[str] = None


class AnomalyPatch(BaseModel):
    cls: Literal["promotion", "data_error", "stockout_censored", "unknown"]
    status: Literal["confirmed", "dismissed"]
    rationale: Optional[str] = None


class AnomalySuggestRequest(BaseModel):
    anomaly_ids: Optional[list[int]] = None   # None = all open for this SKU


# ─── Forecast ─────────────────────────────────────────────────────────────────

class EvaluationMetrics(BaseModel):
    model_name: str
    mae: float
    rmse: float
    wape: float
    bias: float


class ForecastResponse(BaseModel):
    sku: str
    horizon_days: int
    model_used: str
    avg_daily_demand: float
    sigma_daily: float
    predictions: list[float]
    confidence: str
    warnings: list[str]
    evaluation: list[EvaluationMetrics]


class EvaluationResponse(BaseModel):
    sku: str
    holdout_start: Optional[date] = None
    holdout_end: Optional[date] = None
    baseline_wins: bool
    metrics: list[EvaluationMetrics]


# ─── Recommendation ───────────────────────────────────────────────────────────

class ForecastSummary(BaseModel):
    model: str
    avg_daily_demand: float
    sigma_daily: float


class RecommendationInputs(BaseModel):
    service_level: float
    z_factor: float
    lead_time_days: int
    lead_time_std_days: float


class RecommendationResponse(BaseModel):
    sku: str
    as_of: date
    action: Literal["ORDER_NOW", "HOLD", "AT_RISK"]
    order_quantity: int
    inventory_position: float
    reorder_point: float
    safety_stock: float
    forecast: ForecastSummary
    inputs: RecommendationInputs
    formulas: dict[str, str]
    assumptions: list[str]
    ai_adjustments: list[Any]
    warnings: list[str]
    confidence: str


# ─── Scenarios ────────────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    scenario_type: Literal["demand_surge", "supplier_delay", "combined"]
    demand_surge_pct: float = Field(default=0.0, ge=0)
    demand_surge_days: int = Field(default=0, ge=0)
    supplier_delay_days: int = Field(default=0, ge=0)
    supplier_delay_sigma: float = Field(default=0.0, ge=0)


class SimulationSummary(BaseModel):
    stockout_probability: float
    expected_unmet_units: float
    average_inventory: float
    total_cost_p10: float
    total_cost_p50: float
    total_cost_p90: float


class ScenarioResponse(BaseModel):
    sku: str
    scenario_type: str
    before: SimulationSummary
    after: SimulationSummary
    delta_rop: float
    delta_safety_stock: float
    recommended_action: str


# ─── Adjustments ──────────────────────────────────────────────────────────────

class AdjustmentRecord(BaseModel):
    id: int
    sku: str
    start_date: date
    end_date: date
    multiplier: float
    rationale: Optional[str] = None
    confidence: Optional[float] = None
    source: Literal["ai", "user"]
    status: Literal["proposed", "accepted", "rejected"]


class AdjustmentPatch(BaseModel):
    status: Literal["accepted", "rejected"]


class ProposeAdjustmentsRequest(BaseModel):
    event_notes: str
    forecast_summary: Optional[dict] = None


# ─── Explain ──────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    audience: Literal["shop_owner", "planner"] = "planner"
    recommendation: Optional[dict] = None  # if None, fetched from DB


class ExplainResponse(BaseModel):
    sku: str
    explanation: str
    used_fallback: bool
