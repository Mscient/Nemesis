"""
stocksense_ai — LLM / AI layer for StockSense.

Public API (what backend/B imports):
    is_enabled()                    -> bool
    status()                        -> AIStatus
    suggest_anomaly_labels(items)   -> AnomalySuggestionBatch        (async)
    explain_recommendation(req)     -> ExplainResult                 (async)
    propose_forecast_adjustments(req) -> AdjustmentProposalBatch     (async)

Design contracts:
- All async functions NEVER raise — they return graceful fallbacks on error.
- The system is fully usable with AI_ENABLED=false.
- No secrets, no data beyond what is necessary, leave the system.
- 'core/' and 'backend/' are never imported here.
"""
from stocksense_ai.schemas import (
    AnomalyContext,
    AnomalySuggestion,
    AnomalySuggestionBatch,
    ExplainRequest,
    ExplainResult,
    AdjustmentRequest,
    AdjustmentProposal,
    AdjustmentProposalBatch,
    AIStatus,
    AIAuditRecord,
)
from stocksense_ai.ai_status import is_enabled, status
from stocksense_ai.suggester import suggest_anomaly_labels
from stocksense_ai.explainer import explain_recommendation
from stocksense_ai.proposer import propose_forecast_adjustments

__all__ = [
    # Status
    "is_enabled",
    "status",
    # Core async functions
    "suggest_anomaly_labels",
    "explain_recommendation",
    "propose_forecast_adjustments",
    # Schemas
    "AnomalyContext",
    "AnomalySuggestion",
    "AnomalySuggestionBatch",
    "ExplainRequest",
    "ExplainResult",
    "AdjustmentRequest",
    "AdjustmentProposal",
    "AdjustmentProposalBatch",
    "AIStatus",
    "AIAuditRecord",
]
