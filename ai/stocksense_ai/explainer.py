"""Stub — recommendation explainer with template fallback."""
from stocksense_ai.schemas import ExplainRequest, ExplainResult


_TEMPLATE = (
    "Based on the analysis, the system recommends ordering {order_quantity} units. "
    "The reorder point is {reorder_point} units, calculated using a service level of "
    "{service_level}% and a lead time of {lead_time_days} days. "
    "Safety stock of {safety_stock} units protects against demand variability."
)


async def explain_recommendation(req: ExplainRequest) -> ExplainResult:
    """Template fallback explanation (AI disabled stub)."""
    rec = req.recommendation
    text = _TEMPLATE.format(
        order_quantity=rec.get("order_quantity", "?"),
        reorder_point=rec.get("reorder_point", "?"),
        service_level=round(rec.get("inputs", {}).get("service_level", 0) * 100, 0),
        lead_time_days=rec.get("inputs", {}).get("lead_time_days", "?"),
        safety_stock=rec.get("safety_stock", "?"),
    )
    return ExplainResult(explanation=text, used_fallback=True)
