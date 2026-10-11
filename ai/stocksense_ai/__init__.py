"""
stocksense_ai — LLM / AI layer.
All functions are async, never raise to the caller, and log every call.
The system works fully with AI disabled (AI_ENABLED=false).
"""
from stocksense_ai.schemas import (
    AnomalyContext, AnomalySuggestionBatch,
    ExplainRequest, ExplainResult,
    AdjustmentRequest, AdjustmentProposalBatch,
    AIStatus,
)
from stocksense_ai.client import is_enabled, status
from stocksense_ai.suggester import suggest_anomaly_labels
from stocksense_ai.explainer import explain_recommendation
from stocksense_ai.proposer import propose_forecast_adjustments

__all__ = [
    "is_enabled", "status",
    "suggest_anomaly_labels", "explain_recommendation", "propose_forecast_adjustments",
    "AnomalyContext", "AnomalySuggestionBatch",
    "ExplainRequest", "ExplainResult",
    "AdjustmentRequest", "AdjustmentProposalBatch",
    "AIStatus",
]
