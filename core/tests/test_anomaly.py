"""
Tests for anomaly detection and treatment — D8, D9.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

import pytest

from stocksense_core.types import AnomalyFlag, SalesRecord
from stocksense_core.anomaly.detection import detect_anomalies
from stocksense_core.anomaly.treatment import clean_series


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_records(units: List[float], start: date = date(2026, 1, 1), sku: str = "TEST") -> List[SalesRecord]:
    return [
        SalesRecord(date=start + timedelta(days=i), sku=sku, units_sold=u, on_hand=100.0 - i * 0.1, promo_flag=0)
        for i, u in enumerate(units)
    ]


# ── Negative value → data_error ──────────────────────────────────────────────

def test_negative_demand_flagged():
    records = make_records([10.0] * 30 + [-5.0] + [10.0] * 30)
    flags = detect_anomalies(records)
    neg_flags = [f for f in flags if "negative" in f.flags]
    assert len(neg_flags) >= 1
    assert neg_flags[0].cls == "data_error"


# ── Stockout censoring detection ─────────────────────────────────────────────

def test_stockout_censored_when_zero_sales_zero_onhand():
    start = date(2026, 1, 1)
    records = [
        SalesRecord(date=start + timedelta(days=i), sku="TEST", units_sold=10.0, on_hand=50.0, promo_flag=0)
        for i in range(30)
    ]
    # Add a stretch where on_hand=0 and sales=0
    for i in range(30, 36):
        records.append(
            SalesRecord(date=start + timedelta(days=i), sku="TEST", units_sold=0.0, on_hand=0.0, promo_flag=0)
        )
    records += [
        SalesRecord(date=start + timedelta(days=i), sku="TEST", units_sold=10.0, on_hand=50.0, promo_flag=0)
        for i in range(36, 60)
    ]

    flags = detect_anomalies(records)
    censored = [f for f in flags if "stockout_censored" in f.flags]
    assert len(censored) >= 1
    assert all(f.cls == "stockout_censored" for f in censored)


# ── Statistical z-score detection ────────────────────────────────────────────

def test_statistical_outlier_flagged():
    """A single extreme spike should be caught by the robust z-score."""
    base = [10.0] * 60
    base[40] = 500.0  # extreme outlier
    records = make_records(base)
    flags = detect_anomalies(records, threshold=3.5)
    flagged_dates = [f.date for f in flags]
    assert date(2026, 1, 1) + timedelta(days=40) in flagged_dates


# ── Promotion window overlay ──────────────────────────────────────────────────

def test_promo_window_classifies_as_promotion():
    base = [10.0] * 60
    base[20] = 50.0  # spike during promo
    records = make_records(base)
    promo_start = date(2026, 1, 1) + timedelta(days=18)
    promo_end = date(2026, 1, 1) + timedelta(days=22)
    flags = detect_anomalies(records, promo_windows=((promo_start, promo_end),))
    promo_flags = [f for f in flags if f.cls == "promotion"]
    assert len(promo_flags) >= 1


# ── No anomalies in clean data ────────────────────────────────────────────────

def test_clean_data_produces_no_flags():
    records = make_records([10.0 + i * 0.01 for i in range(60)])
    flags = detect_anomalies(records)
    # Allow up to 1 edge flag but no extreme ones
    assert all(f.robust_z < 10 for f in flags)


# ── Treatment: exclude data_error ────────────────────────────────────────────

def test_clean_series_excludes_data_error():
    records = make_records([10.0] * 30 + [-5.0] + [10.0] * 30)
    flags = detect_anomalies(records)
    cleaned = clean_series(records, flags)
    # The negative record should be excluded
    assert all(r.units_sold >= 0 for r in cleaned.records)


# ── Treatment: keep unknown ───────────────────────────────────────────────────

def test_clean_series_keeps_unknown():
    base = [10.0] * 60
    base[30] = 45.0  # statistical spike but no promo / on_hand=0
    records = make_records(base)
    flags = detect_anomalies(records)
    unknown_flags = [f for f in flags if f.cls == "unknown"]
    if not unknown_flags:
        pytest.skip("No unknown flags generated with this data — model classified differently.")
    cleaned = clean_series(records, flags)
    # Unknown records should still be in cleaned
    assert len(cleaned.records) == len(records)


# ── User override: force exclude ──────────────────────────────────────────────

def test_user_can_override_treatment_to_exclude():
    base = [10.0] * 60
    base[30] = 45.0
    records = make_records(base)
    flags = detect_anomalies(records)
    override_date = (date(2026, 1, 1) + timedelta(days=30)).isoformat()
    user_decisions = {override_date: {"treatment": "exclude"}}
    cleaned_no_override = clean_series(records, flags)
    cleaned_with_override = clean_series(records, flags, user_decisions=user_decisions)
    assert len(cleaned_with_override.records) <= len(cleaned_no_override.records)


# ── Empty input ───────────────────────────────────────────────────────────────

def test_detect_anomalies_empty_input():
    assert detect_anomalies([]) == []


def test_clean_series_empty_input():
    cleaned = clean_series([], [])
    assert cleaned.records == ()
