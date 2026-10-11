"""
SQLAlchemy 2.x ORM models — owned by Member B (B3).
Uses async-compatible declarative base. Table creation is handled at startup.
"""
from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ─── skus ─────────────────────────────────────────────────────────────────────

class SkuModel(Base):
    __tablename__ = "skus"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=True)
    is_synthetic = Column(Boolean, default=False, nullable=False)

    # SKU parameters (denormalised for simplicity)
    lead_time_days = Column(Integer, default=5, nullable=False)
    lead_time_std_days = Column(Float, default=0.0, nullable=False)
    unit_cost = Column(Float, default=1.0, nullable=False)
    order_cost = Column(Float, default=50.0, nullable=False)
    holding_cost_per_unit_per_year = Column(Float, default=2.0, nullable=False)
    stockout_penalty_per_unit = Column(Float, default=6.0, nullable=False)
    moq = Column(Integer, default=1, nullable=False)
    pack_size = Column(Integer, default=1, nullable=False)
    max_storage = Column(Integer, nullable=True)
    service_level = Column(Float, default=0.95, nullable=False)
    on_hand = Column(Float, default=0.0, nullable=False)
    on_order = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # relationships
    sales_records = relationship("SalesRecordModel", back_populates="sku_rel", cascade="all, delete-orphan")
    anomalies = relationship("AnomalyModel", back_populates="sku_rel", cascade="all, delete-orphan")
    forecast_runs = relationship("ForecastRunModel", back_populates="sku_rel", cascade="all, delete-orphan")
    scenarios = relationship("ScenarioModel", back_populates="sku_rel", cascade="all, delete-orphan")
    adjustments = relationship("AdjustmentModel", back_populates="sku_rel", cascade="all, delete-orphan")


# ─── sales_records ────────────────────────────────────────────────────────────

class SalesRecordModel(Base):
    __tablename__ = "sales_records"
    __table_args__ = (UniqueConstraint("sku", "date", name="uq_sales_sku_date"),)

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), ForeignKey("skus.sku", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    units_sold = Column(Float, nullable=False)
    on_hand = Column(Float, nullable=True)
    promo_flag = Column(Integer, nullable=True)  # 0 or 1

    sku_rel = relationship("SkuModel", back_populates="sales_records")


# ─── anomalies ────────────────────────────────────────────────────────────────

class AnomalyModel(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), ForeignKey("skus.sku", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    robust_z = Column(Float, nullable=False)
    flags_json = Column(Text, default="[]")       # JSON list[str]
    cls = Column(String(32), nullable=False)       # promotion|data_error|stockout_censored|unknown
    treatment = Column(String(64), nullable=False)
    source = Column(String(8), default="rule")     # rule|ai|user
    status = Column(String(16), default="open")    # open|confirmed|dismissed
    rationale = Column(Text, nullable=True)

    sku_rel = relationship("SkuModel", back_populates="anomalies")

    @property
    def flags(self) -> list:
        try:
            return json.loads(self.flags_json or "[]")
        except Exception:
            return []

    @flags.setter
    def flags(self, value: list) -> None:
        self.flags_json = json.dumps(value)


# ─── forecast_runs ────────────────────────────────────────────────────────────

class ForecastRunModel(Base):
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), ForeignKey("skus.sku", ondelete="CASCADE"), nullable=False, index=True)
    model_used = Column(String(64), nullable=False)
    horizon_days = Column(Integer, nullable=False, default=14)
    mu_d = Column(Float, nullable=False)
    sigma_d = Column(Float, nullable=False)
    confidence = Column(String(8), nullable=False)
    predictions_json = Column(Text, default="[]")  # JSON list[float]
    metrics_json = Column(Text, default="[]")       # JSON list[EvaluationMetrics dict]
    warnings_json = Column(Text, default="[]")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    sku_rel = relationship("SkuModel", back_populates="forecast_runs")


# ─── scenarios ────────────────────────────────────────────────────────────────

class ScenarioModel(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), ForeignKey("skus.sku", ondelete="CASCADE"), nullable=False, index=True)
    params_json = Column(Text, nullable=False)   # ScenarioRequest dict
    results_json = Column(Text, nullable=False)  # ScenarioResponse dict
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    sku_rel = relationship("SkuModel", back_populates="scenarios")


# ─── adjustments ──────────────────────────────────────────────────────────────

class AdjustmentModel(Base):
    __tablename__ = "adjustments"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), ForeignKey("skus.sku", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    multiplier = Column(Float, nullable=False)
    rationale = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    source = Column(String(8), nullable=False)   # ai|user
    status = Column(String(16), default="proposed")  # proposed|accepted|rejected
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    sku_rel = relationship("SkuModel", back_populates="adjustments")


# ─── ai_audit_log ─────────────────────────────────────────────────────────────

class AIAuditLogModel(Base):
    __tablename__ = "ai_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    task = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    prompt_version = Column(String(32), nullable=False)
    latency_ms = Column(Float, nullable=False)
    validation_outcome = Column(String(32), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ─── users ────────────────────────────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

