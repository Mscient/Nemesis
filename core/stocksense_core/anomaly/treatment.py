"""Stub — apply anomaly treatments to produce a cleaned series."""
from __future__ import annotations
from stocksense_core.types import SalesRecord, AnomalyFlag, CleanedSeries


def clean_series(
    records: list[SalesRecord],
    flags: list[AnomalyFlag],
    user_decisions: dict | None = None,
) -> CleanedSeries:
    """Apply default or user-overridden treatments. Stub returns records unchanged."""
    return CleanedSeries(records=tuple(records))
