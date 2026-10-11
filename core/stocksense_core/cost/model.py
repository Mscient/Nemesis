"""
Cost model — D12.

Implements the cost formula from spec §9.1:
  Holding cost  = H_daily × average_inventory × days
  Ordering cost = S × number_of_orders
  Stockout cost = P × unmet_units
  Total cost    = Holding + Ordering + Stockout

Used by the Monte Carlo simulation to price each simulated run.
"""
from __future__ import annotations

from dataclasses import dataclass

from stocksense_core.types import SkuParams


@dataclass
class CostBreakdown:
    holding_cost: float
    ordering_cost: float
    stockout_cost: float
    total_cost: float


def compute_cost(
    params: SkuParams,
    average_inventory: float,
    number_of_orders: float,
    unmet_units: float,
    days: int,
) -> CostBreakdown:
    """
    Compute holding, ordering, and stockout cost over `days` days.

    Parameters
    ----------
    params            : SKU parameters (order_cost, holding_cost_per_unit_per_year,
                        stockout_penalty_per_unit)
    average_inventory : mean on-hand level during the simulation period
    number_of_orders  : number of replenishment orders placed
    unmet_units       : total unmet demand (stockouts)
    days              : simulation horizon in days
    """
    h_daily = params.holding_cost_per_unit_per_year / 365.0
    holding = h_daily * average_inventory * days
    ordering = params.order_cost * number_of_orders
    stockout = params.stockout_penalty_per_unit * unmet_units
    total = holding + ordering + stockout

    return CostBreakdown(
        holding_cost=round(holding, 4),
        ordering_cost=round(ordering, 4),
        stockout_cost=round(stockout, 4),
        total_cost=round(total, 4),
    )
