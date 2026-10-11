"""
Recommendation explainer (C6).

Generates a plain-language explanation of a recommendation for the chosen
audience ('shop_owner' or 'planner').

Guardrails (number-consistency check):
- Extract all numbers from the LLM output.
- Every number in the output must appear somewhere in the input recommendation.
- On failure, fall back to the deterministic template.

Never raises. Sets used_fallback=True when the template is used.
"""
from __future__ import annotations

import json
import logging
import re
import time

from stocksense_ai.ai_status import is_enabled
from stocksense_ai.client import complete, LLMError
from stocksense_ai.config import get_config
from stocksense_ai.prompts.templates import EXPLAIN_PROMPT, PROMPT_VERSION
from stocksense_ai.schemas import AIAuditRecord, ExplainRequest, ExplainResult

logger = logging.getLogger(__name__)

# ─── Deterministic template fallback ──────────────────────────────────────────

_TEMPLATE_PLANNER = (
    "For SKU {sku}, the system recommends action: {action}. "
    "Order {order_quantity} units. "
    "The reorder point is {reorder_point} (inventory position: {inventory_position}). "
    "Safety stock of {safety_stock} units is held to cover demand variability "
    "over the {lead_time_days}-day lead time at a {service_level_pct}% service level "
    "(z={z_factor})."
)

_TEMPLATE_SHOP_OWNER = (
    "You should {action_friendly} — order {order_quantity} units of {sku}. "
    "You currently have {inventory_position} units (including on order). "
    "When stock drops to {reorder_point} units, it is time to reorder. "
    "We keep a buffer of {safety_stock} extra units to handle surprises in demand."
)

_ACTION_FRIENDLY = {
    "ORDER_NOW": "place an order now",
    "MONITOR": "keep monitoring stock",
    "OK": "hold — stock levels are fine",
}


def _template_fallback(req: ExplainRequest) -> str:
    rec = req.recommendation
    inputs = rec.get("inputs", {})
    action = rec.get("action", "MONITOR")

    if req.audience == "shop_owner":
        return _TEMPLATE_SHOP_OWNER.format(
            sku=rec.get("sku", req.sku),
            action_friendly=_ACTION_FRIENDLY.get(action, action.lower()),
            order_quantity=rec.get("order_quantity", "?"),
            inventory_position=rec.get("inventory_position", "?"),
            reorder_point=rec.get("reorder_point", "?"),
            safety_stock=rec.get("safety_stock", "?"),
        )
    else:
        return _TEMPLATE_PLANNER.format(
            sku=rec.get("sku", req.sku),
            action=action,
            order_quantity=rec.get("order_quantity", "?"),
            reorder_point=rec.get("reorder_point", "?"),
            inventory_position=rec.get("inventory_position", "?"),
            safety_stock=rec.get("safety_stock", "?"),
            lead_time_days=inputs.get("lead_time_days", "?"),
            service_level_pct=round(inputs.get("service_level", 0) * 100, 0),
            z_factor=inputs.get("z_factor", "?"),
        )


# ─── Number-consistency check ─────────────────────────────────────────────────

def _extract_numbers(text: str) -> set[float]:
    """Extract all decimal/integer numbers from a string."""
    return {float(m) for m in re.findall(r"\b\d+(?:\.\d+)?\b", text)}


def _numbers_from_rec(rec: dict) -> set[float]:
    """Flatten a nested recommendation dict into its numeric values."""
    nums: set[float] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, (int, float)):
            nums.add(float(obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                _walk(item)
        elif isinstance(obj, str):
            for m in re.findall(r"\b\d+(?:\.\d+)?\b", obj):
                nums.add(float(m))

    _walk(rec)
    return nums


def _check_number_consistency(explanation: str, rec: dict) -> bool:
    """Return True if every number in *explanation* appears in the recommendation data."""
    output_nums = _extract_numbers(explanation)
    allowed_nums = _numbers_from_rec(rec)
    rogue = output_nums - allowed_nums
    if rogue:
        logger.warning(
            "Number-consistency check failed — numbers in explanation not in input: %s",
            rogue,
        )
        return False
    return True


# ─── Public function ──────────────────────────────────────────────────────────

async def explain_recommendation(req: ExplainRequest) -> ExplainResult:
    """
    Generate a plain-language explanation for the recommendation.

    Falls back to the deterministic template when:
    - AI is disabled
    - LLM call fails
    - LLM output contains numbers not present in the input (hallucination check)
    """
    cfg = get_config()
    used_fallback = False

    if not is_enabled():
        return ExplainResult(
            explanation=_template_fallback(req),
            used_fallback=True,
        )

    prompt = EXPLAIN_PROMPT.format(
        audience=req.audience,
        recommendation_json=json.dumps(req.recommendation, default=str, indent=2),
    )

    t0 = time.monotonic()
    validation_outcome = "ok"

    try:
        raw, latency_ms = await complete(prompt)
        explanation = raw.strip()

        # Guardrail: number-consistency check
        if not _check_number_consistency(explanation, req.recommendation):
            validation_outcome = "number_consistency_failed"
            logger.warning(
                "Explanation for SKU %s failed number-consistency check — using template fallback.",
                req.sku,
            )
            explanation = _template_fallback(req)
            used_fallback = True

    except LLMError as exc:
        latency_ms = (time.monotonic() - t0) * 1000
        validation_outcome = f"llm_error: {exc}"
        logger.warning("LLM error during explain_recommendation for %s: %s", req.sku, exc)
        explanation = _template_fallback(req)
        used_fallback = True

    # Audit record (not returned in response body; B can store via side-channel)
    _audit = AIAuditRecord(
        task="explain_recommendation",
        model=cfg.model,
        prompt_version=PROMPT_VERSION,
        latency_ms=latency_ms if "latency_ms" in dir() else 0.0,
        validation_outcome=validation_outcome,
    )

    return ExplainResult(explanation=explanation, used_fallback=used_fallback)
