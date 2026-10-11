"""
Forecast evaluation metric tests — MAE, RMSE, WAPE, Bias,
holdout split protocol, and baseline-wins rule.
"""
from __future__ import annotations
import math
import numpy as np
import pytest
from stocksense_core.forecast.evaluation import _mae, _rmse, _wape, _bias


# ── Unit tests for each metric function ──────────────────────────────────────

def test_mae_hand_calculated():
    actuals = np.array([10.0, 12.0, 8.0, 11.0])
    preds   = np.array([ 9.0, 13.0, 9.0, 10.0])
    # |1| + |1| + |1| + |1| / 4 = 1.0
    assert abs(_mae(actuals, preds) - 1.0) < 1e-9


def test_rmse_hand_calculated():
    actuals = np.array([10.0, 12.0])
    preds   = np.array([ 8.0, 14.0])
    # sqrt((4 + 4) / 2) = sqrt(4) = 2.0
    assert abs(_rmse(actuals, preds) - 2.0) < 1e-9


def test_wape_hand_calculated():
    actuals = np.array([10.0, 10.0])
    preds   = np.array([ 8.0, 12.0])
    # Σ|err| = 2+2=4 ; Σactual = 20 → 4/20 = 0.2
    assert abs(_wape(actuals, preds) - 0.2) < 1e-9


def test_wape_zero_actuals_returns_zero():
    """WAPE denominator = 0 → return 0.0 (no division by zero)."""
    actuals = np.array([0.0, 0.0])
    preds   = np.array([1.0, 2.0])
    assert _wape(actuals, preds) == 0.0


def test_bias_positive_overforecast():
    actuals = np.array([10.0, 10.0])
    preds   = np.array([12.0, 12.0])
    # mean(pred - actual) = 2.0
    assert abs(_bias(actuals, preds) - 2.0) < 1e-9


def test_bias_negative_underforecast():
    actuals = np.array([10.0, 10.0])
    preds   = np.array([ 8.0,  8.0])
    assert abs(_bias(actuals, preds) - (-2.0)) < 1e-9


def test_perfect_forecast_all_zeros():
    actuals = np.array([10.0, 12.0, 9.0])
    preds   = actuals.copy()
    assert _mae(actuals, preds) == 0.0
    assert _rmse(actuals, preds) == 0.0
    assert _bias(actuals, preds) == 0.0


# ── Forecast runner integration: verify holdout & evaluation structure ────────

def test_forecast_runner_returns_evaluation():
    """Smoke test: runner returns ForecastResult with evaluation metrics."""
    from datetime import date, timedelta
    from stocksense_core.types import SalesRecord, CleanedSeries
    from stocksense_core.forecast.runner import run_forecast

    start = date(2026, 1, 1)
    records = tuple(
        SalesRecord(date=start + timedelta(days=i), sku="EVAL-SKU",
                    units_sold=float(10 + (i % 3)), on_hand=200.0, promo_flag=0)
        for i in range(45)
    )
    cleaned = CleanedSeries(records=records)
    result = run_forecast(cleaned, horizon_days=7)
    assert result is not None
    assert len(result.predictions) == 7
    assert len(result.evaluation) >= 1
    assert result.mu_d > 0
    assert result.confidence in ("low", "medium", "high")


def test_forecast_runner_short_history_low_confidence():
    """< 28 days → confidence must be 'low'."""
    from datetime import date, timedelta
    from stocksense_core.types import SalesRecord, CleanedSeries
    from stocksense_core.forecast.runner import run_forecast

    start = date(2026, 1, 1)
    records = tuple(
        SalesRecord(date=start + timedelta(days=i), sku="SHORT-SKU",
                    units_sold=10.0, on_hand=100.0, promo_flag=0)
        for i in range(10)   # only 10 days
    )
    cleaned = CleanedSeries(records=records)
    result = run_forecast(cleaned, horizon_days=7)
    assert result.confidence == "low"


def test_forecast_runner_all_zero_demand():
    """All-zero training data: mu_d = 0, no exception."""
    from datetime import date, timedelta
    from stocksense_core.types import SalesRecord, CleanedSeries
    from stocksense_core.forecast.runner import run_forecast

    start = date(2026, 1, 1)
    records = tuple(
        SalesRecord(date=start + timedelta(days=i), sku="ZERO-SKU",
                    units_sold=0.0, on_hand=100.0, promo_flag=0)
        for i in range(30)
    )
    cleaned = CleanedSeries(records=records)
    result = run_forecast(cleaned, horizon_days=7)
    assert result.mu_d == pytest.approx(0.0, abs=0.01)
    assert all(p >= 0 for p in result.predictions)
