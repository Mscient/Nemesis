"""
Anomaly detection — D8.

Implements:
  1. Rolling-median + MAD robust z-score (configurable threshold, default 3.5).
  2. Rule-based flags:
       - Negative values         → data_error
       - Duplicate dates         → data_error
       - Impossible magnitude    → data_error   (> 10× rolling median and > 100 units)
       - Zero sales while on_hand == 0  → stockout_censored
  3. Promotion overlay (promo_flag column or explicit promo_windows list).

Returns a list[AnomalyFlag] — one entry per flagged point.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Sequence, Tuple

import numpy as np
import pandas as pd

from stocksense_core.series import build_daily_series
from stocksense_core.types import AnomalyFlag, SalesRecord

# Minimum window size for rolling statistics (if fewer points are available,
# fallback to global MAD so we still flag obvious errors).
_MIN_WINDOW = 7
_ROLLING_WINDOW = 14


def _rolling_robust_z(series: pd.Series, window: int = _ROLLING_WINDOW) -> pd.Series:
    """Return the robust z-score for each point relative to its rolling window.

    robust_z = |x - median| / (1.4826 × MAD)
    1.4826 is the consistency factor that makes MAD consistent with std for Normal data.
    """
    rolling_med = series.rolling(window, min_periods=_MIN_WINDOW, center=True).median()
    rolling_mad = (
        series.subtract(rolling_med).abs()
        .rolling(window, min_periods=_MIN_WINDOW, center=True).median()
    )
    # Avoid division by zero; fall back to global MAD
    global_mad = (series - series.median()).abs().median()
    rolling_mad = rolling_mad.where(rolling_mad > 0, other=max(global_mad, 1e-9))
    robust_z = (series - rolling_med).abs() / (1.4826 * rolling_mad)
    return robust_z, rolling_med


def _classify(
    units_sold: float,
    on_hand: float | None,
    promo_flag: int,
    is_duplicate: bool,
    flags: list[str],
) -> str:
    """Apply rule-based classification in priority order."""
    if "negative" in flags or "impossible_magnitude" in flags or is_duplicate:
        return "data_error"
    if "stockout_censored" in flags:
        return "stockout_censored"
    if promo_flag == 1 or "promotion" in flags:
        return "promotion"
    return "unknown"


def _default_treatment(cls: str) -> str:
    treatments = {
        "data_error": "exclude",
        "stockout_censored": "exclude_or_impute",
        "promotion": "keep_with_promo_flag",
        "unknown": "keep_surface_to_user",
    }
    return treatments.get(cls, "keep_surface_to_user")


def detect_anomalies(
    records: Sequence[SalesRecord],
    promo_windows: tuple[tuple[date_type, date_type], ...] = (),
    threshold: float = 3.5,
) -> list[AnomalyFlag]:
    """
    Detect statistical and rule-based anomalies in the sales records.

    Parameters
    ----------
    records       : sales history (any order; duplicates handled internally)
    promo_windows : optional list of (start_date, end_date) promotion periods
    threshold     : robust z-score threshold for statistical flagging (default 3.5)

    Returns
    -------
    list[AnomalyFlag] — one entry per anomalous data point
    """
    if not records:
        return []

    # Determine the SKU from the first record (all records should share one SKU)
    sku = records[0].sku

    df = build_daily_series(records)

    # ── Statistical detection ─────────────────────────────────────────────────
    robust_z, rolling_med = _rolling_robust_z(df["units_sold"])
    df["robust_z"] = robust_z.fillna(0.0)
    df["rolling_med"] = rolling_med.fillna(df["units_sold"].median())

    # ── Build a set of promo dates from windows ───────────────────────────────
    promo_dates: set[pd.Timestamp] = set()
    for (s, e) in promo_windows:
        promo_dates.update(pd.date_range(pd.Timestamp(s), pd.Timestamp(e), freq="D"))

    anomalies: list[AnomalyFlag] = []

    for row in df.itertuples(index=False):
        flags: list[str] = []
        ts: pd.Timestamp = row.date
        units: float = float(row.units_sold)
        on_hand_val = float(row.on_hand) if pd.notna(row.on_hand) else None
        promo: int = int(row.promo_flag)
        is_dup: bool = bool(row.duplicate)
        rz: float = float(row.robust_z)
        expected: float = float(row.rolling_med)

        # Rule 1 — negative demand
        if units < 0:
            flags.append("negative")

        # Rule 2 — duplicate date (already deduplicated; flag the dropped ones via detection)
        if is_dup:
            flags.append("duplicate_date")

        # Rule 3 — impossible magnitude (> 10× rolling median and > 100 units above median)
        if units > 0 and expected > 0 and units > 10 * expected and units - expected > 100:
            flags.append("impossible_magnitude")

        # Rule 4 — stockout censoring: zero sales while on_hand was also zero
        if units == 0.0 and on_hand_val is not None and on_hand_val == 0.0:
            flags.append("stockout_censored")

        # Rule 5 — promotion window overlay
        if ts in promo_dates:
            flags.append("promotion")

        # Statistical flag (robust z > threshold)
        if rz > threshold:
            flags.append(f"robust_z>{threshold:.1f}")

        if not flags:
            continue  # Not an anomaly

        cls = _classify(units, on_hand_val, promo, is_dup, flags)
        treatment = _default_treatment(cls)

        promo_note = " (promotion window)" if ts in promo_dates else ""
        rationale = (
            f"Flags: {', '.join(flags)}. "
            f"Value={units:.2f}, Expected≈{expected:.2f}, robust_z={rz:.2f}.{promo_note}"
        )

        anomalies.append(
            AnomalyFlag(
                date=ts.date(),
                value=units,
                expected_value=round(expected, 4),
                robust_z=round(rz, 4),
                flags=tuple(flags),
                cls=cls,
                default_treatment=treatment,
                rationale=rationale,
            )
        )

    return anomalies
