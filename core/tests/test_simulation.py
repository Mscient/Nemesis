"""
Tests for Monte Carlo simulation and scenario comparison — D12, D13.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from stocksense_core.types import (
    CleanedSeries, ForecastResult, EvaluationMetrics, RecommendationResult,
    ScenarioSpec, SalesRecord, SkuParams,
)
from stocksense_core.simulation.monte_carlo import simulate
from stocksense_core.simulation.scenarios import run_scenario
from stocksense_core.forecast.runner import run_forecast
from stocksense_core.engine.recommendation import compute_recommendation


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_params(**overrides) -> SkuParams:
    defaults = dict(
        sku="TEST",
        lead_time_days=5,
        lead_time_std_days=1.0,
        unit_cost=8.0,
        order_cost=50.0,
        holding_cost_per_unit_per_year=2.0,
        stockout_penalty_per_unit=6.0,
        moq=24,
        pack_size=12,
        max_storage=None,
        service_level=0.95,
        on_hand=120.0,
        on_order=0.0,
    )
    defaults.update(overrides)
    return SkuParams(**defaults)


def _make_forecast(mu_d=10.0, sigma_d=2.0, horizon=14) -> ForecastResult:
    dummy_eval = EvaluationMetrics(mae=1.0, rmse=1.2, wape=0.1, bias=0.0, model_name="test")
    return ForecastResult(
        sku="TEST",
        predictions=tuple([mu_d] * horizon),
        mu_d=mu_d,
        sigma_d=sigma_d,
        model_used="test",
        evaluation=(dummy_eval,),
        confidence="medium",
        warnings=(),
    )


def _make_cleaned(n: int = 90, mu: float = 10.0) -> CleanedSeries:
    start = date(2026, 1, 1)
    records = tuple(
        SalesRecord(date=start + timedelta(days=i), sku="TEST", units_sold=mu, on_hand=120.0, promo_flag=0)
        for i in range(n)
    )
    return CleanedSeries(records=records)


# ── Monte Carlo basic sanity ──────────────────────────────────────────────────

def test_simulate_outputs_valid_probabilities():
    params = _make_params()
    forecast = _make_forecast(mu_d=10.0, sigma_d=2.0)
    rec = compute_recommendation(params, forecast)
    result = simulate(params, forecast, rec, n_runs=200, seed=42, horizon_days=30)
    assert 0 <= result.stockout_probability <= 1.0
    assert result.expected_unmet_units >= 0
    assert result.average_inventory >= 0


def test_simulate_cost_ordering():
    """P10 ≤ P50 ≤ P90."""
    params = _make_params()
    forecast = _make_forecast(mu_d=10.0, sigma_d=2.0)
    rec = compute_recommendation(params, forecast)
    result = simulate(params, forecast, rec, n_runs=500, seed=42, horizon_days=60)
    assert result.total_cost_p10 <= result.total_cost_p50
    assert result.total_cost_p50 <= result.total_cost_p90


def test_simulate_reproducible_with_same_seed():
    """Same seed → same result."""
    params = _make_params()
    forecast = _make_forecast()
    rec = compute_recommendation(params, forecast)
    r1 = simulate(params, forecast, rec, n_runs=200, seed=99, horizon_days=30)
    r2 = simulate(params, forecast, rec, n_runs=200, seed=99, horizon_days=30)
    assert r1.stockout_probability == r2.stockout_probability
    assert r1.total_cost_p50 == r2.total_cost_p50


def test_simulate_high_demand_raises_stockout_risk():
    """Very high demand relative to on_hand should raise stockout probability."""
    params = _make_params(on_hand=5.0)  # very low stock
    forecast_low = _make_forecast(mu_d=1.0, sigma_d=0.1)
    forecast_high = _make_forecast(mu_d=20.0, sigma_d=3.0)
    rec_low = compute_recommendation(params, forecast_low)
    rec_high = compute_recommendation(params, forecast_high)
    r_low = simulate(params, forecast_low, rec_low, n_runs=300, seed=42, horizon_days=30)
    r_high = simulate(params, forecast_high, rec_high, n_runs=300, seed=42, horizon_days=30)
    # High demand scenario should have higher or equal stockout probability
    assert r_high.stockout_probability >= r_low.stockout_probability


# ── Scenario: demand surge raises ROP ────────────────────────────────────────

def test_demand_surge_increases_rop():
    params = _make_params()
    forecast = _make_forecast(mu_d=10.0, sigma_d=2.0)
    spec = ScenarioSpec(
        scenario_type="demand_surge",
        demand_surge_pct=30.0,
        demand_surge_days=14,
    )
    comparison = run_scenario(params, forecast, spec, n_runs=200, seed=42, horizon_days=30)
    assert comparison.delta_rop >= 0, "Demand surge should not decrease ROP"


def test_supplier_delay_increases_rop():
    params = _make_params()
    forecast = _make_forecast(mu_d=10.0, sigma_d=2.0)
    spec = ScenarioSpec(
        scenario_type="supplier_delay",
        supplier_delay_days=5,
    )
    comparison = run_scenario(params, forecast, spec, n_runs=200, seed=42, horizon_days=30)
    assert comparison.delta_rop > 0, "Supplier delay should increase ROP"


def test_combined_scenario_increases_rop_more():
    params = _make_params()
    forecast = _make_forecast(mu_d=10.0, sigma_d=2.0)
    spec_surge = ScenarioSpec(scenario_type="demand_surge", demand_surge_pct=30.0, demand_surge_days=14)
    spec_delay = ScenarioSpec(scenario_type="supplier_delay", supplier_delay_days=5)
    spec_combined = ScenarioSpec(
        scenario_type="combined",
        demand_surge_pct=30.0,
        demand_surge_days=14,
        supplier_delay_days=5,
    )
    c_combined = run_scenario(params, forecast, spec_combined, n_runs=200, seed=42, horizon_days=30)
    c_surge = run_scenario(params, forecast, spec_surge, n_runs=200, seed=42, horizon_days=30)
    # Combined should be more impactful than just demand surge
    assert c_combined.delta_rop >= c_surge.delta_rop


def test_scenario_recommended_action_is_string():
    params = _make_params()
    forecast = _make_forecast()
    spec = ScenarioSpec(scenario_type="demand_surge", demand_surge_pct=50.0, demand_surge_days=7)
    comparison = run_scenario(params, forecast, spec, n_runs=100, seed=42, horizon_days=30)
    assert isinstance(comparison.recommended_action, str)
    assert len(comparison.recommended_action) > 10


# ── Scenario: no-op (zero parameters) ────────────────────────────────────────

def test_noop_scenario_near_zero_deltas():
    params = _make_params()
    forecast = _make_forecast()
    spec = ScenarioSpec(scenario_type="demand_surge", demand_surge_pct=0.0, demand_surge_days=0)
    comparison = run_scenario(params, forecast, spec, n_runs=100, seed=42, horizon_days=30)
    assert abs(comparison.delta_rop) < 1e-6
    assert abs(comparison.delta_safety_stock) < 1e-6


# ── Cost model sanity ─────────────────────────────────────────────────────────

def test_cost_model_basic():
    from stocksense_core.cost.model import compute_cost
    params = _make_params()
    cost = compute_cost(params, average_inventory=100, number_of_orders=5, unmet_units=0, days=90)
    assert cost.holding_cost > 0
    assert cost.ordering_cost > 0
    assert cost.stockout_cost == 0
    assert cost.total_cost == pytest.approx(cost.holding_cost + cost.ordering_cost + cost.stockout_cost, rel=1e-4)
