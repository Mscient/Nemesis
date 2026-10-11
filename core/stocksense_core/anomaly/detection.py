"""Stub — anomaly detection (rolling median + MAD robust z-score)."""
from __future__ import annotations
from stocksense_core.types import SalesRecord, AnomalyFlag


def detect_anomalies(
    records: list[SalesRecord],
    promo_windows: tuple = (),
    threshold: float = 3.5,
) -> list[AnomalyFlag]:
    """Detect statistical and rule-based anomalies. Returns empty list (stub)."""
    return []
