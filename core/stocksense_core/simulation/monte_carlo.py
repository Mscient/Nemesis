"""Stubs — Monte Carlo simulation and scenario comparison."""
from __future__ import annotations
from stocksense_core.types import (
    SkuParams, ForecastResult, RecommendationResult,
    SimulationResult, ScenarioSpec, ScenarioComparison,
)


def simulate(
    params: SkuParams,
    forecast: ForecastResult,
    recommendation: RecommendationResult,
    n_runs: int = 1000,
    seed: int = 42,
    horizon_days: int = 90,
) -> SimulationResult:
    """Stub Monte Carlo simulation."""
    return SimulationResult(
        stockout_probability=0.05,
        expected_unmet_units=2.0,
        average_inventory=float(recommendation.safety_stock),
        total_cost_p10=0.0,
        total_cost_p50=0.0,
        total_cost_p90=0.0,
    )


def run_scenario(
    params: SkuParams,
    forecast: ForecastResult,
    scenario: ScenarioSpec,
) -> ScenarioComparison:
    """Stub scenario comparison."""
    base = simulate(params, forecast, __import__("stocksense_core").compute_recommendation(params, forecast))
    return ScenarioComparison(
        before=base,
        after=base,
        delta_rop=0.0,
        delta_safety_stock=0.0,
        recommended_action="No change (stub).",
    )
