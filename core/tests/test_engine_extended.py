"""
Additional engine tests — EOQ constraints, action thresholds, variable lead time SS.
Extends the existing test_engine.py without duplicating it.
"""
from __future__ import annotations
import math
import pytest
from stocksense_core.engine.z_factor import service_level_to_z
from stocksense_core.engine.recommendation import (
    safety_stock, reorder_point, eoq, constrained_order_qty, compute_recommendation
)
from stocksense_core.types import SkuParams, ForecastResult, EvaluationMetrics


# ── z-factor edge cases ───────────────────────────────────────────────────────

def test_z_factor_non_table_value():
    """Arbitrary service levels use scipy, not table interpolation."""
    z = service_level_to_z(0.92)
    assert 1.282 < z < 1.645   # between 90% and 95%


def test_z_factor_rejects_zero():
    with pytest.raises(ValueError):
        service_level_to_z(0.0)


def test_z_factor_rejects_one():
    with pytest.raises(ValueError):
        service_level_to_z(1.0)


# ── Variable lead-time safety stock ──────────────────────────────────────────

def test_variable_lead_time_ss_greater_than_constant():
    """When sigma_L > 0, SS must be >= the constant lead-time formula."""
    z = service_level_to_z(0.95)
    ss_constant = safety_stock(z=z, sigma_d=4, L=5, mu_d=10, sigma_L=0)
    ss_variable = safety_stock(z=z, sigma_d=4, L=5, mu_d=10, sigma_L=2)
    assert ss_variable >= ss_constant


def test_variable_lead_time_formula():
    """SS = ceil(z × √(L×σd² + μd²×σL²))"""
    z = 1.645
    sigma_d, L, mu_d, sigma_L = 4.0, 5, 10.0, 2.0
    expected_raw = z * math.sqrt(L * sigma_d**2 + mu_d**2 * sigma_L**2)
    result = safety_stock(z=z, sigma_d=sigma_d, L=L, mu_d=mu_d, sigma_L=sigma_L)
    assert result == math.ceil(expected_raw)


# ── EOQ constraints ───────────────────────────────────────────────────────────

def test_moq_enforced_when_eoq_smaller():
    """If raw EOQ < MOQ, result must be MOQ."""
    raw = 10.0
    result = constrained_order_qty(raw, moq=50, pack_size=1, max_storage=None)
    assert result >= 50


def test_pack_size_rounding():
    """qty=13, pack_size=6 → 18."""
    result = constrained_order_qty(13.0, moq=1, pack_size=6, max_storage=None)
    assert result == 18


def test_max_storage_cap():
    """If EOQ > max_storage, cap at max_storage."""
    result = constrained_order_qty(1000.0, moq=1, pack_size=1, max_storage=500)
    assert result == 500


def test_moq_and_pack_size_combined():
    """MOQ=24, pack_size=12, raw=10 → must be at least 24 and a multiple of 12."""
    result = constrained_order_qty(10.0, moq=24, pack_size=12, max_storage=None)
    assert result >= 24
    assert result % 12 == 0


# ── Action thresholds ─────────────────────────────────────────────────────────

def _make_forecast(mu_d=10.0, sigma_d=2.0) -> ForecastResult:
    metrics = EvaluationMetrics(mae=1.0, rmse=1.2, wape=0.1, bias=0.0, model_name="naive")
    return ForecastResult(
        sku="TEST",
        predictions=tuple([mu_d] * 14),
        mu_d=mu_d,
        sigma_d=sigma_d,
        model_used="naive",
        evaluation=(metrics,),
        confidence="medium",
        warnings=(),
    )


def _make_params(on_hand: float, on_order: float = 0.0) -> SkuParams:
    return SkuParams(
        sku="TEST",
        lead_time_days=5,
        lead_time_std_days=0.0,
        unit_cost=8.0,
        order_cost=50.0,
        holding_cost_per_unit_per_year=2.0,
        stockout_penalty_per_unit=6.0,
        moq=1,
        pack_size=1,
        max_storage=None,
        service_level=0.95,
        on_hand=on_hand,
        on_order=on_order,
    )


def test_action_hold_when_well_stocked():
    """inventory_position >> ROP → HOLD."""
    params = _make_params(on_hand=9999.0)
    rec = compute_recommendation(params, _make_forecast())
    assert rec.action == "HOLD"


def test_action_order_now_when_at_rop():
    """inventory_position just at ROP → ORDER_NOW."""
    forecast = _make_forecast(mu_d=10.0, sigma_d=2.0)
    # ROP = mu_d*L + SS ≈ 50 + 5 = 55
    params = _make_params(on_hand=55.0)
    rec = compute_recommendation(params, forecast)
    assert rec.action in ("ORDER_NOW", "AT_RISK")


def test_action_at_risk_when_critically_low():
    """inventory_position ≤ ROP × 0.5 → AT_RISK."""
    forecast = _make_forecast(mu_d=10.0, sigma_d=2.0)
    params = _make_params(on_hand=5.0)   # very low
    rec = compute_recommendation(params, forecast)
    assert rec.action == "AT_RISK"


# ── Recommendation payload completeness ───────────────────────────────────────

def test_recommendation_has_all_required_fields():
    params = _make_params(on_hand=200.0)
    rec = compute_recommendation(params, _make_forecast())
    assert rec.sku == "TEST"
    assert rec.order_quantity > 0
    assert rec.reorder_point > 0
    assert rec.safety_stock >= 0
    assert rec.z_factor > 0
    assert "safety_stock" in rec.formulas
    assert "reorder_point" in rec.formulas
    assert len(rec.assumptions) >= 2
    assert rec.confidence in ("low", "medium", "high")


def test_zero_sigma_d_warning():
    """When sigma_d=0, recommendation must include variability warning."""
    params = _make_params(on_hand=200.0)
    rec = compute_recommendation(params, _make_forecast(sigma_d=0.0))
    assert rec.safety_stock == 0
    assert any("variability" in w.lower() for w in rec.warnings)
