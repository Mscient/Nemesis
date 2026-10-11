"""Safety stock, ROP, EOQ, and recommendation composition."""
from __future__ import annotations
import math
from datetime import date
from stocksense_core.types import SkuParams, ForecastResult, RecommendationResult
from stocksense_core.engine.z_factor import service_level_to_z


def safety_stock(z: float, sigma_d: float, L: int, mu_d: float, sigma_L: float) -> float:
    """Variable or constant lead-time safety stock formula."""
    if sigma_L > 0:
        ss = z * math.sqrt(L * sigma_d**2 + mu_d**2 * sigma_L**2)
    else:
        ss = z * sigma_d * math.sqrt(L)
    return math.ceil(ss)


def reorder_point(mu_d: float, L: int, ss: float) -> float:
    return mu_d * L + ss


def eoq(D_annual: float, S: float, H: float) -> float:
    if S <= 0 or H <= 0:
        raise ValueError("order_cost and holding_cost must be > 0 to compute EOQ")
    return math.sqrt(2 * D_annual * S / H)


def constrained_order_qty(raw_eoq: float, moq: int, pack_size: int, max_storage: int | None) -> int:
    qty = math.ceil(raw_eoq)            # round up
    qty = max(qty, moq)                 # enforce MOQ
    if pack_size > 1:
        qty = math.ceil(qty / pack_size) * pack_size   # round to pack size
    if max_storage is not None:
        qty = min(qty, max_storage)
    return qty


def compute_recommendation(params: SkuParams, forecast: ForecastResult) -> RecommendationResult:
    z = service_level_to_z(params.service_level)
    L = params.lead_time_days
    sigma_L = params.lead_time_std_days
    mu_d = forecast.mu_d
    sigma_d = forecast.sigma_d

    ss = safety_stock(z, sigma_d, L, mu_d, sigma_L)
    rop = reorder_point(mu_d, L, ss)
    inv_pos = params.on_hand + params.on_order

    D_annual = mu_d * 365
    raw = eoq(D_annual, params.order_cost, params.holding_cost_per_unit_per_year)
    qty = constrained_order_qty(raw, params.moq, params.pack_size, params.max_storage)

    action = "ORDER_NOW" if inv_pos <= rop else "HOLD"
    if inv_pos <= rop * 0.5:
        action = "AT_RISK"

    warnings: list[str] = list(forecast.warnings)
    if sigma_d == 0:
        warnings.append("No demand variability observed — safety stock is 0.")

    return RecommendationResult(
        sku=params.sku,
        as_of=date.today(),
        action=action,
        order_quantity=qty,
        inventory_position=inv_pos,
        reorder_point=rop,
        safety_stock=ss,
        z_factor=round(z, 3),
        formulas={
            "safety_stock": f"z × σd × √L = {z:.3f} × {sigma_d} × √{L} = {ss}",
            "reorder_point": f"(μd × L) + SS = ({mu_d} × {L}) + {ss} = {rop}",
            "order_quantity": f"EOQ = √(2DS/H) = {raw:.1f} → {qty}",
        },
        assumptions=(
            f"Demand ~ Normal(μ={mu_d:.2f}, σ={sigma_d:.2f})",
            f"Lead time = {L} days (σL={sigma_L})",
            f"Service level = {params.service_level*100:.0f}% → z={z:.3f}",
        ),
        ai_adjustments=(),
        warnings=tuple(warnings),
        confidence=forecast.confidence,
    )
