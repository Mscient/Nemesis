"""Stub — anomaly label suggester."""
from stocksense_ai.schemas import AnomalyContext, AnomalySuggestionBatch, AnomalySuggestion
from stocksense_ai.client import is_enabled


async def suggest_anomaly_labels(items: list[AnomalyContext]) -> AnomalySuggestionBatch:
    """Return unknown for all items (stub / AI-disabled fallback)."""
    suggestions = [
        AnomalySuggestion(
            anomaly_id=item.anomaly_id,
            cls="unknown",
            confidence=0.0,
            rationale="AI disabled — defaulting to unknown.",
        )
        for item in items
    ]
    return AnomalySuggestionBatch(suggestions=suggestions)
