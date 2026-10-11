"""Stub — forecast adjustment proposer."""
from stocksense_ai.schemas import AdjustmentRequest, AdjustmentProposalBatch


async def propose_forecast_adjustments(req: AdjustmentRequest) -> AdjustmentProposalBatch:
    """Returns empty proposals (AI disabled stub)."""
    return AdjustmentProposalBatch(proposals=[])
