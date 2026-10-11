"""Pydantic v2 schemas owned by Member C."""
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal


class AnomalyContext(BaseModel):
    anomaly_id: int
    sku: str
    date: date
    value: float
    expected_value: float
    robust_z: float
    flags: list[str]


class AnomalySuggestion(BaseModel):
    anomaly_id: int
    cls: Literal["promotion", "data_error", "stockout_censored", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    source: Literal["ai"] = "ai"


class AnomalySuggestionBatch(BaseModel):
    suggestions: list[AnomalySuggestion]


class ExplainRequest(BaseModel):
    sku: str
    audience: Literal["shop_owner", "planner"] = "planner"
    recommendation: dict       # the full RecommendationResult as dict


class ExplainResult(BaseModel):
    explanation: str
    used_fallback: bool = False


class AdjustmentRequest(BaseModel):
    sku: str
    event_notes: str
    forecast_summary: dict


class AdjustmentProposal(BaseModel):
    start_date: date
    end_date: date
    multiplier: float = Field(ge=0.5, le=2.0)
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["proposed"] = "proposed"
    source: Literal["ai"] = "ai"


class AdjustmentProposalBatch(BaseModel):
    proposals: list[AdjustmentProposal]


class AIStatus(BaseModel):
    enabled: bool
    provider: str
    model: str


class AIAuditRecord(BaseModel):
    task: str
    model: str
    prompt_version: str
    latency_ms: float
    validation_outcome: str
