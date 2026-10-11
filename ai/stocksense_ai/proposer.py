"""
Forecast adjustment proposer (C7).

Given user-supplied event notes and a forecast summary, proposes bounded
forecast multiplier adjustments for specific date ranges.

Guardrails:
- multiplier is hard-clamped to [0.5, 2.0].
- start_date <= end_date is enforced.
- status is always 'proposed' (never changed by AI).
- source is always 'ai'.
- Empty proposals list is valid (no adjustment warranted).
- Prompt injection: event_notes treated as pure data (JSON-escaped).
- On any failure, returns empty proposals list — never raises.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date

from stocksense_ai.ai_status import is_enabled
from stocksense_ai.client import complete, LLMError
from stocksense_ai.config import get_config
from stocksense_ai.prompts.templates import ADJUSTMENT_PROPOSE_PROMPT, PROMPT_VERSION
from stocksense_ai.schemas import (
    AIAuditRecord,
    AdjustmentProposal,
    AdjustmentProposalBatch,
    AdjustmentRequest,
)

logger = logging.getLogger(__name__)


def _clamp_multiplier(value: object) -> float:
    try:
        return max(0.5, min(2.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1.0


def _parse_proposals(raw: str) -> list[AdjustmentProposal]:
    """Parse LLM JSON, apply guardrails, return validated proposals."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(l for l in lines if not l.startswith("```")).strip()

    try:
        data = json.loads(text)
        raw_proposals = data.get("proposals", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("LLM returned invalid JSON for adjustment proposals: %s", exc)
        return []

    proposals: list[AdjustmentProposal] = []
    for rp in raw_proposals:
        try:
            start = date.fromisoformat(str(rp.get("start_date", "")))
            end = date.fromisoformat(str(rp.get("end_date", "")))
        except ValueError:
            logger.warning("Skipping proposal with invalid dates: %s", rp)
            continue

        if end < start:
            logger.warning("Skipping proposal where end_date < start_date: %s", rp)
            continue

        multiplier = _clamp_multiplier(rp.get("multiplier", 1.0))
        confidence = max(0.0, min(1.0, float(rp.get("confidence", 0.5))))
        rationale = str(rp.get("rationale", ""))[:200]

        proposals.append(
            AdjustmentProposal(
                start_date=start,
                end_date=end,
                multiplier=multiplier,
                rationale=rationale,
                confidence=confidence,
                status="proposed",
                source="ai",
            )
        )

    return proposals


async def propose_forecast_adjustments(req: AdjustmentRequest) -> AdjustmentProposalBatch:
    """
    Propose forecast adjustments based on event notes and a forecast summary.

    Returns empty proposals when AI is disabled or on any error.
    Never raises.
    """
    if not is_enabled():
        return AdjustmentProposalBatch(proposals=[])

    cfg = get_config()

    # Sanitise event_notes: JSON-encode to prevent injection
    safe_notes = json.dumps(req.event_notes)   # produces a quoted string
    # Remove outer quotes for cleaner prompt display
    safe_notes = safe_notes[1:-1]  # strip leading/trailing "

    prompt = ADJUSTMENT_PROPOSE_PROMPT.format(
        forecast_summary_json=json.dumps(req.forecast_summary, default=str, indent=2),
        event_notes=safe_notes,
    )

    t0 = time.monotonic()
    validation_outcome = "ok"

    try:
        raw, latency_ms = await complete(prompt)
        proposals = _parse_proposals(raw)
        if not proposals and raw.strip():
            validation_outcome = "empty_or_invalid"
    except LLMError as exc:
        latency_ms = (time.monotonic() - t0) * 1000
        validation_outcome = f"llm_error: {exc}"
        logger.warning("LLM error during propose_forecast_adjustments for %s: %s", req.sku, exc)
        proposals = []

    _audit = AIAuditRecord(
        task="propose_forecast_adjustments",
        model=cfg.model,
        prompt_version=PROMPT_VERSION,
        latency_ms=latency_ms if "latency_ms" in dir() else 0.0,
        validation_outcome=validation_outcome,
    )

    return AdjustmentProposalBatch(proposals=proposals)
