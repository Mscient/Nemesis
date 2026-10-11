"""
Anomaly treatment — D9.

`clean_series` applies default or user-overridden treatments to produce a
CleanedSeries that is suitable for forecasting.

Treatment mapping:
  data_error            → exclude the point
  stockout_censored     → exclude the point (don't treat as low demand)
  promotion             → keep but mark with promo_flag=1 (already set)
  unknown               → keep (surface to user for review)

User decisions override the default.  `user_decisions` is a dict keyed by
ISO date string → {"treatment": "exclude" | "keep", "cls": <optional override>}.
"""
from __future__ import annotations

from typing import Sequence

from stocksense_core.types import AnomalyFlag, CleanedSeries, SalesRecord

_EXCLUDE_TREATMENTS = {"exclude", "exclude_or_impute"}


def clean_series(
    records: Sequence[SalesRecord],
    flags: Sequence[AnomalyFlag],
    user_decisions: dict | None = None,
) -> CleanedSeries:
    """
    Apply anomaly treatments and return a cleaned series.

    Parameters
    ----------
    records        : original sales records (any order)
    flags          : anomaly flags from detect_anomalies
    user_decisions : optional mapping of ISO-date → {treatment, cls}
                     (overrides default treatment for that date)

    Returns
    -------
    CleanedSeries containing only the records that should feed into forecasting.
    """
    user_decisions = user_decisions or {}

    # Build a lookup: date → AnomalyFlag (first flag per date wins)
    flag_by_date: dict = {}
    for af in flags:
        date_key = af.date.isoformat()
        if date_key not in flag_by_date:
            flag_by_date[date_key] = af

    cleaned: list[SalesRecord] = []

    for record in records:
        date_key = record.date.isoformat()
        af = flag_by_date.get(date_key)

        if af is None:
            # No anomaly — always keep
            cleaned.append(record)
            continue

        # Determine the effective treatment
        if date_key in user_decisions:
            ud = user_decisions[date_key]
            treatment = ud.get("treatment", af.default_treatment)
        else:
            treatment = af.default_treatment

        if treatment in _EXCLUDE_TREATMENTS:
            # Skip this record
            continue

        # Keep (with optional classification override for promo already baked in flag)
        cleaned.append(record)

    # Return sorted by date (forecasting code expects chronological order)
    cleaned.sort(key=lambda r: r.date)
    return CleanedSeries(records=tuple(cleaned))
