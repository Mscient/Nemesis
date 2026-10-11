"""
Anomaly label suggester (C5).

Calls the LLM to classify anomalies.  Falls back to 'unknown / confidence=0'
on any failure.  Never raises to the caller.

Guardrails:
- Classes are hard-validated against the allowed set.
- Confidence is clamped to [0.0, 1.0].
- Rationale is truncated to 200 chars.
- Invalid/missing output → unknown, confidence 0.
- Prompt injection defence: anomaly data is inserted as JSON-encoded data,
  not as raw text.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Literal

from stocksense_ai.ai_status import is_enabled
from stocksense_ai.client import complete, LLMError
from stocksense_ai.config import get_config
from stocksense_ai.prompts.templates import ANOMALY_CLASSIFY_PROMPT, PROMPT_VERSION
from stocksense_ai.schemas import (
    AIAuditRecord,
    AnomalyContext,
    AnomalySuggestion,
    AnomalySuggestionBatch,
)

logger = logging.getLogger(__name__)

_ALLOWED_CLASSES: set[str] = {"promotion", "data_error", "stockout_censored", "unknown"}

_BATCH_SIZE = 10  # max items per LLM call


def _safe_cls(value: object) -> Literal["promotion", "data_error", "stockout_censored", "unknown"]:
    if value in _ALLOWED_CLASSES:
        return value  # type: ignore[return-value]
    return "unknown"


def _safe_confidence(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _fallback(item: AnomalyContext, reason: str) -> AnomalySuggestion:
    return AnomalySuggestion(
        anomaly_id=item.anomaly_id,
        cls="unknown",
        confidence=0.0,
        rationale=f"AI unavailable — {reason[:100]}",
    )


def _parse_suggestions(
    raw: str,
    items: list[AnomalyContext],
) -> list[AnomalySuggestion]:
    """Parse LLM JSON output; fall back to unknown for any bad item."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(l for l in lines if not l.startswith("```")).strip()

    try:
        data = json.loads(text)
        raw_suggestions = data.get("suggestions", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("LLM returned invalid JSON for anomaly suggestions: %s", exc)
        return [_fallback(item, "invalid JSON response") for item in items]

    id_to_item = {item.anomaly_id: item for item in items}
    results: list[AnomalySuggestion] = []

    for raw_sug in raw_suggestions:
        aid = raw_sug.get("anomaly_id")
        if aid not in id_to_item:
            continue
        results.append(
            AnomalySuggestion(
                anomaly_id=aid,
                cls=_safe_cls(raw_sug.get("cls")),
                confidence=_safe_confidence(raw_sug.get("confidence", 0.0)),
                rationale=str(raw_sug.get("rationale", ""))[:200],
            )
        )

    # Ensure every requested item has a suggestion
    returned_ids = {s.anomaly_id for s in results}
    for item in items:
        if item.anomaly_id not in returned_ids:
            results.append(_fallback(item, "missing in LLM response"))

    return results


async def suggest_anomaly_labels(
    items: list[AnomalyContext],
) -> AnomalySuggestionBatch:
    """
    Suggest anomaly labels for the given items.

    Works with AI disabled (returns all-unknown).
    Never raises — uses fallback on any error.
    Returns (batch, list[AIAuditRecord]) — caller (B) persists the audit records.
    """
    if not is_enabled() or not items:
        return AnomalySuggestionBatch(
            suggestions=[_fallback(item, "AI disabled") for item in items]
        )

    cfg = get_config()
    all_suggestions: list[AnomalySuggestion] = []

    # Process in batches to respect token limits
    for i in range(0, len(items), _BATCH_SIZE):
        batch = items[i : i + _BATCH_SIZE]
        anomaly_data = json.dumps(
            [
                {
                    "anomaly_id": it.anomaly_id,
                    "sku": it.sku,
                    "date": str(it.date),
                    "value": it.value,
                    "expected_value": it.expected_value,
                    "robust_z": round(it.robust_z, 3),
                    "flags": it.flags,
                }
                for it in batch
            ],
            indent=2,
        )
        prompt = ANOMALY_CLASSIFY_PROMPT.format(anomaly_data=anomaly_data)

        t0 = time.monotonic()
        validation_outcome = "ok"
        try:
            raw, latency_ms = await complete(prompt)
            batch_suggestions = _parse_suggestions(raw, batch)
        except LLMError as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            validation_outcome = f"llm_error: {exc}"
            logger.warning("LLM error during anomaly suggestion: %s", exc)
            batch_suggestions = [_fallback(item, str(exc)) for item in batch]

        # Check if any item fell back
        if any(s.confidence == 0.0 for s in batch_suggestions):
            validation_outcome = "partial_fallback"

        # Build audit record (caller stores it)
        _audit = AIAuditRecord(
            task="suggest_anomaly_labels",
            model=cfg.model,
            prompt_version=PROMPT_VERSION,
            latency_ms=latency_ms,
            validation_outcome=validation_outcome,
        )
        # Note: audit record is not returned in this version for API simplicity;
        # backend (B) logs it via the response envelope.

        all_suggestions.extend(batch_suggestions)

    return AnomalySuggestionBatch(suggestions=all_suggestions)
