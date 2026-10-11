"""
Scenario simulation — D13.

`run_scenario` modifies SkuParams and/or ForecastResult to reflect a
what-if scenario (demand surge, supplier delay, or combined), then
runs two Monte Carlo simulations (before vs after) and returns a
ScenarioComparison with before/after SimulationResults, delta metrics,
and a recommended action string.

Scenarios supported (from spec §9.3):
  demand_surge    : mu_d increased by X% for N days; affects sigma_d proportionally
  supplier_delay  : lead_time_days increased by Y days; sigma_L increased if specified
  combined        : both at once
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from stocksense_core.types import (
    ForecastResult,
    RecommendationResult,
    ScenarioComparison,
    ScenarioSpec,
    SimulationResult,
    SkuParams,
)
from stocksense_core.engine.recommendation import compute_recommendation
from stocksense_core.simulation.monte_carlo import simulate


def _apply_demand_surge(
    forecast: ForecastResult,
    surge_pct: float,
    surge_days: int,
    horizon_days: int,
) -> ForecastResult:
    """Return a modified ForecastResult with mu_d increased during the surge window."""
    preds = list(forecast.predictions)
    surge_factor = 1.0 + surge_pct / 100.0
    for i in range(min(surge_days, len(preds))):
        preds[i] = preds[i] * surge_factor

    # Compute new mu_d / sigma_d over the whole horizon
    arr = np.array(preds, dtype=float)
    new_mu_d = float(np.mean(arr))
    # sigma_d grows proportionally during the surge (heuristic)
    new_sigma_d = forecast.sigma_d * (
        1 + (surge_factor - 1) * surge_days / max(horizon_days, 1)
    )

    return ForecastResult(
        sku=forecast.sku,
        predictions=tuple(preds),
        mu_d=new_mu_d,
        sigma_d=new_sigma_d,
        model_used=forecast.model_used,
        evaluation=forecast.evaluation,
        confidence=forecast.confidence,
        warnings=forecast.warnings,
    )


def _apply_supplier_delay(
    params: SkuParams,
    delay_days: int,
    delay_sigma: float,
) -> SkuParams:
    """Return modified SkuParams with extended lead time."""
    new_lt = params.lead_time_days + delay_days
    new_sigma_l = math.sqrt(params.lead_time_std_days ** 2 + delay_sigma ** 2) if delay_sigma else params.lead_time_std_days

    # SkuParams is frozen — rebuild it
    return SkuParams(
        sku=params.sku,
        lead_time_days=max(1, new_lt),
        lead_time_std_days=new_sigma_l,
        unit_cost=params.unit_cost,
        order_cost=params.order_cost,
        holding_cost_per_unit_per_year=params.holding_cost_per_unit_per_year,
        stockout_penalty_per_unit=params.stockout_penalty_per_unit,
        moq=params.moq,
        pack_size=params.pack_size,
        max_storage=params.max_storage,
        service_level=params.service_level,
        on_hand=params.on_hand,
        on_order=params.on_order,
    )


def _action_string(before: SimulationResult, after: SimulationResult, spec: ScenarioSpec) -> str:
    """Generate a plain-language recommended action from the scenario comparison."""
    parts: list[str] = []

    if spec.demand_surge_pct > 0:
        parts.append(
            f"Demand surge of +{spec.demand_surge_pct:.0f}% for {spec.demand_surge_days} days"
        )
    if spec.supplier_delay_days > 0:
        parts.append(f"Supplier delay of +{spec.supplier_delay_days} days")

    delta_so = after.stockout_probability - before.stockout_probability
    scenario_desc = " + ".join(parts) if parts else "Scenario"

    if delta_so > 0.1:
        urgency = "URGENT: Stockout risk increases significantly."
    elif delta_so > 0.03:
        urgency = "Consider increasing safety stock or placing an early order."
    else:
        urgency = "Minimal impact; continue current replenishment plan."

    return (
        f"{scenario_desc}. "
        f"Stockout risk: {before.stockout_probability:.1%} → {after.stockout_probability:.1%}. "
        f"Total cost (P50): {before.total_cost_p50:.0f} → {after.total_cost_p50:.0f}. "
        f"{urgency}"
    )


def run_scenario(
    params: SkuParams,
    forecast: ForecastResult,
    scenario: ScenarioSpec,
    n_runs: int = 1000,
    seed: int = 42,
    horizon_days: int = 90,
) -> ScenarioComparison:
    """
    Run a before-vs-after scenario comparison.

    Parameters
    ----------
    params       : baseline SKU parameters
    forecast     : baseline ForecastResult
    scenario     : ScenarioSpec describing the what-if
    n_runs       : Monte Carlo runs (default 1000)
    seed         : random seed
    horizon_days : simulation horizon

    Returns
    -------
    ScenarioComparison with before/after SimulationResults, delta_rop,
    delta_safety_stock, and recommended_action string.
    """
    # ── Baseline (before) simulation ─────────────────────────────────────────
    before_rec: RecommendationResult = compute_recommendation(params, forecast)
    before_sim: SimulationResult = simulate(
        params, forecast, before_rec, n_runs=n_runs, seed=seed, horizon_days=horizon_days
    )

    # ── Apply scenario modifications ─────────────────────────────────────────
    after_params = params
    after_forecast = forecast

    stype = scenario.scenario_type.lower()

    if stype in ("demand_surge", "combined") and scenario.demand_surge_pct > 0:
        after_forecast = _apply_demand_surge(
            forecast,
            surge_pct=scenario.demand_surge_pct,
            surge_days=scenario.demand_surge_days,
            horizon_days=horizon_days,
        )

    if stype in ("supplier_delay", "combined") and scenario.supplier_delay_days > 0:
        after_params = _apply_supplier_delay(
            params,
            delay_days=scenario.supplier_delay_days,
            delay_sigma=scenario.supplier_delay_sigma,
        )

    # ── After simulation ──────────────────────────────────────────────────────
    after_rec: RecommendationResult = compute_recommendation(after_params, after_forecast)
    after_sim: SimulationResult = simulate(
        after_params, after_forecast, after_rec,
        n_runs=n_runs, seed=seed, horizon_days=horizon_days,
    )

    delta_rop = after_rec.reorder_point - before_rec.reorder_point
    delta_ss = float(after_rec.safety_stock) - float(before_rec.safety_stock)

    return ScenarioComparison(
        before=before_sim,
        after=after_sim,
        delta_rop=round(delta_rop, 4),
        delta_safety_stock=round(delta_ss, 4),
        recommended_action=_action_string(before_sim, after_sim, scenario),
    )
