"""Frozen dataclasses used as the type contract between core and backend."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class SalesRecord:
    date: date
    sku: str
    units_sold: float
    on_hand: Optional[float] = None
    promo_flag: Optional[int] = None


@dataclass(frozen=True)
class SkuParams:
    sku: str
    lead_time_days: int
    lead_time_std_days: float
    unit_cost: float
    order_cost: float
    holding_cost_per_unit_per_year: float
    stockout_penalty_per_unit: float
    moq: int
    pack_size: int
    max_storage: Optional[int]
    service_level: float
    on_hand: float
    on_order: float = 0.0


@dataclass(frozen=True)
class AnomalyFlag:
    date: date
    value: float
    expected_value: float
    robust_z: float
    flags: tuple[str, ...]
    cls: str              # promotion | data_error | stockout_censored | unknown
    default_treatment: str
    rationale: str


@dataclass(frozen=True)
class Adjustment:
    start_date: date
    end_date: date
    multiplier: float
    source: str           # ai | user


@dataclass(frozen=True)
class CleanedSeries:
    records: tuple[SalesRecord, ...]


@dataclass(frozen=True)
class EvaluationMetrics:
    mae: float
    rmse: float
    wape: float
    bias: float
    model_name: str


@dataclass(frozen=True)
class ForecastResult:
    sku: str
    predictions: tuple[float, ...]   # daily, horizon_days length
    mu_d: float
    sigma_d: float
    model_used: str
    evaluation: tuple[EvaluationMetrics, ...]   # baseline + proposed
    confidence: str                              # high | medium | low
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationResult:
    sku: str
    as_of: date
    action: str               # ORDER_NOW | HOLD | AT_RISK
    order_quantity: int
    inventory_position: float
    reorder_point: float
    safety_stock: float
    z_factor: float
    formulas: dict
    assumptions: tuple[str, ...]
    ai_adjustments: tuple
    warnings: tuple[str, ...]
    confidence: str


@dataclass(frozen=True)
class SimulationResult:
    stockout_probability: float
    expected_unmet_units: float
    average_inventory: float
    total_cost_p10: float
    total_cost_p50: float
    total_cost_p90: float


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_type: str          # demand_surge | supplier_delay | combined
    demand_surge_pct: float = 0.0
    demand_surge_days: int = 0
    supplier_delay_days: int = 0
    supplier_delay_sigma: float = 0.0


@dataclass(frozen=True)
class ScenarioComparison:
    before: SimulationResult
    after: SimulationResult
    delta_rop: float
    delta_safety_stock: float
    recommended_action: str
