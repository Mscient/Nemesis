"""
Monte Carlo simulation — D12.

Implements a seeded vectorised (ROP, Q) policy simulation:

  Each run:
    1. Simulate daily demand drawn from Normal(mu_d, sigma_d).
    2. Simulate lead times drawn from Normal(lead_time_days, lead_time_std_days).
    3. Apply (ROP, Q) policy:
         - When inventory_position ≤ ROP and no order in-flight → place order of Q.
         - After lead-time days the order arrives and is added to on-hand.
    4. Record:
         - Whether any stockout occurred.
         - Total unmet demand units.
         - Average on-hand inventory.
         - Total cost (via cost model).

Outputs P10, P50, P90 of total cost across n_runs.
"""
from __future__ import annotations

import math
import numpy as np

from stocksense_core.types import (
    SkuParams, ForecastResult, RecommendationResult, SimulationResult,
)
from stocksense_core.cost.model import compute_cost


def simulate(
    params: SkuParams,
    forecast: ForecastResult,
    recommendation: RecommendationResult,
    n_runs: int = 1000,
    seed: int = 42,
    horizon_days: int = 90,
) -> SimulationResult:
    """
    Vectorised (ROP, Q) Monte Carlo simulation.

    Parameters
    ----------
    params         : SKU parameters
    forecast       : ForecastResult with mu_d, sigma_d
    recommendation : RecommendationResult with reorder_point, order_quantity
    n_runs         : number of Monte Carlo runs (default 1000)
    seed           : random seed for reproducibility (default 42)
    horizon_days   : simulation horizon in days (default 90)

    Returns
    -------
    SimulationResult with stockout_probability, expected_unmet_units,
    average_inventory, total_cost_p10/p50/p90.
    """
    rng = np.random.default_rng(seed)

    mu_d: float = max(forecast.mu_d, 0.0)
    sigma_d: float = max(forecast.sigma_d, 0.0)
    L: float = float(params.lead_time_days)
    sigma_L: float = float(params.lead_time_std_days)
    rop: float = recommendation.reorder_point
    Q: int = recommendation.order_quantity
    on_hand_init: float = params.on_hand

    # Clip sigma_d to avoid degenerate distributions
    sigma_d_safe = max(sigma_d, 1e-6)

    stockout_flag = np.zeros(n_runs, dtype=bool)
    unmet_units = np.zeros(n_runs, dtype=float)
    avg_inventories = np.zeros(n_runs, dtype=float)
    total_costs = np.zeros(n_runs, dtype=float)

    for run in range(n_runs):
        on_hand = on_hand_init
        on_order = float(params.on_order)
        order_eta: list[int] = []  # days until each pending order arrives
        inv_sum = 0.0
        unmet = 0.0
        n_orders = 0
        had_stockout = False

        for day in range(horizon_days):
            # Receive any pending orders
            new_arrivals: list[int] = []
            for eta in order_eta:
                eta -= 1
                if eta <= 0:
                    on_hand += Q
                    on_order -= Q
                else:
                    new_arrivals.append(eta)
            order_eta = new_arrivals

            # Compute inventory position
            inv_pos = on_hand + on_order

            # Place a new order if needed
            if inv_pos <= rop:
                lt = max(1, round(rng.normal(L, sigma_L) if sigma_L > 0 else L))
                order_eta.append(int(lt))
                on_order += Q
                n_orders += 1

            # Realise demand
            demand = max(0.0, rng.normal(mu_d, sigma_d_safe))
            if demand > on_hand:
                unmet += demand - on_hand
                had_stockout = True
                on_hand = 0.0
            else:
                on_hand -= demand

            inv_sum += on_hand

        if had_stockout:
            stockout_flag[run] = True
        unmet_units[run] = unmet
        avg_inv = inv_sum / horizon_days
        avg_inventories[run] = avg_inv

        cost = compute_cost(
            params=params,
            average_inventory=avg_inv,
            number_of_orders=n_orders,
            unmet_units=unmet,
            days=horizon_days,
        )
        total_costs[run] = cost.total_cost

    return SimulationResult(
        stockout_probability=round(float(np.mean(stockout_flag)), 4),
        expected_unmet_units=round(float(np.mean(unmet_units)), 4),
        average_inventory=round(float(np.mean(avg_inventories)), 4),
        total_cost_p10=round(float(np.percentile(total_costs, 10)), 4),
        total_cost_p50=round(float(np.percentile(total_costs, 50)), 4),
        total_cost_p90=round(float(np.percentile(total_costs, 90)), 4),
    )
