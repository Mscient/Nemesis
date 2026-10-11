"""
Tests for forecasting and evaluation — D10, D11.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from stocksense_core.types import CleanedSeries, SalesRecord
from stocksense_core.forecast.runner import run_forecast
from stocksense_core.forecast.models import (
    naive_forecast,
    seasonal_naive_forecast,
    moving_average_forecast,
    holt_winters_forecast,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_cleaned(units, start=date(2026, 1, 1), sku="TEST"):
    records = tuple(
        SalesRecord(
            date=start + timedelta(days=i),
            sku=sku,
            units_sold=float(u),
            on_hand=100.0,
            promo_flag=0,
        )
        for i, u in enumerate(units)
    )
    return CleanedSeries(records=records)


# ── run_forecast basic sanity ────────────────────────────────────────────────

def test_run_forecast_returns_correct_horizon():
    cleaned = make_cleaned([10.0] * 60)
    result = run_forecast(cleaned, horizon_days=14)
    assert len(result.predictions) == 14


def test_run_forecast_non_negative_predictions():
    cleaned = make_cleaned([5.0 + i * 0.1 for i in range(90)])
    result = run_forecast(cleaned, horizon_days=14)
    assert all(p >= 0 for p in result.predictions)


def test_run_forecast_confidence_low_for_short_history():
    cleaned = make_cleaned([10.0] * 10)
    result = run_forecast(cleaned, horizon_days=7)
    assert result.confidence == "low"
    assert any("low-confidence" in w.lower() for w in result.warnings)


def test_run_forecast_produces_evaluation_metrics():
    cleaned = make_cleaned([10.0 + np.sin(i * 2 * np.pi / 7) for i in range(90)])
    result = run_forecast(cleaned, horizon_days=14)
    assert len(result.evaluation) >= 2  # at least one baseline + proposed
    for m in result.evaluation:
        assert m.mae >= 0
        assert m.rmse >= 0
        assert 0 <= m.wape <= 2.0


# ── Chosen-model rule ────────────────────────────────────────────────────────

def test_run_forecast_model_used_is_in_evaluation():
    cleaned = make_cleaned([10.0 + np.sin(i * 2 * np.pi / 7) for i in range(90)])
    result = run_forecast(cleaned, horizon_days=14)
    model_names = {m.model_name for m in result.evaluation}
    assert result.model_used in model_names


# ── Baseline model shapes ────────────────────────────────────────────────────

def test_naive_forecast_shape():
    train = np.array([5.0] * 30)
    frame = naive_forecast(train, horizon=14)
    assert len(frame.predictions) == 14
    assert frame.model_name == "naive"


def test_seasonal_naive_shape():
    train = np.array([float(i % 7) + 1 for i in range(30)])
    frame = seasonal_naive_forecast(train, horizon=14)
    assert len(frame.predictions) == 14
    assert frame.model_name == "seasonal_naive"


def test_moving_average_shape():
    train = np.array([10.0] * 30)
    frame = moving_average_forecast(train, horizon=14)
    assert len(frame.predictions) == 14
    assert abs(frame.predictions[0] - 10.0) < 1e-6


# ── Holt-Winters falls back gracefully for short series ──────────────────────

def test_holt_winters_short_series_fallback():
    train = np.array([10.0] * 10)
    frame = holt_winters_forecast(train, horizon=7)
    assert len(frame.predictions) == 7
    assert all(p >= 0 for p in frame.predictions)


# ── Adjustments applied to predictions ───────────────────────────────────────

def test_run_forecast_with_adjustment():
    from stocksense_core.types import Adjustment
    cleaned = make_cleaned([10.0] * 90)
    start_date = date(2026, 1, 1) + timedelta(days=90)
    end_date = start_date + timedelta(days=6)
    adj = Adjustment(start_date=start_date, end_date=end_date, multiplier=2.0, source="user")
    result_no_adj = run_forecast(cleaned, horizon_days=14, adjustments=())
    result_with_adj = run_forecast(cleaned, horizon_days=14, adjustments=(adj,))
    # First 7 days should be boosted, last 7 unchanged
    assert result_with_adj.predictions[0] > result_no_adj.predictions[0]


# ── Empty cleaned series ──────────────────────────────────────────────────────

def test_run_forecast_empty_series():
    cleaned = CleanedSeries(records=())
    result = run_forecast(cleaned, horizon_days=14)
    assert result.confidence == "low"
    assert all(p == 0.0 for p in result.predictions)
    assert len(result.predictions) == 14


# ── mu_d and sigma_d are non-negative ────────────────────────────────────────

def test_run_forecast_mu_sigma_non_negative():
    cleaned = make_cleaned([max(0, 10 + np.random.randn() * 3) for _ in range(90)])
    result = run_forecast(cleaned, horizon_days=14)
    assert result.mu_d >= 0
    assert result.sigma_d >= 0
