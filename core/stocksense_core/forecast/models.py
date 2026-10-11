"""
Forecasting models — D10.

Implements:
  Baselines:
    - naive           : last known value carried forward
    - seasonal_naive  : same weekday from the previous week
    - moving_average  : 14-day trailing mean

  Proposed:
    - holt_winters    : ExponentialSmoothing with additive weekly seasonality
                        (falls back to simple exponential smoothing if < 2 seasons)
    - regression      : OLS with weekday dummies + linear trend + promo flag

Each model returns a ForecastFrame namedtuple with:
    predictions  (np.ndarray)
    mu_d         float  — average predicted daily demand
    sigma_d      float  — std-dev of residuals on the training set
    model_name   str
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np
import pandas as pd

_MIN_HW_POINTS = 28   # minimum points for Holt-Winters with weekly seasonality
_SEASON_PERIOD = 7    # weekly


class ForecastFrame(NamedTuple):
    predictions: np.ndarray
    mu_d: float
    sigma_d: float
    model_name: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _residual_sigma(actuals: np.ndarray, preds: np.ndarray) -> float:
    """Standard deviation of residuals (in-sample)."""
    if len(preds) == 0:
        return 0.0
    resid = actuals[: len(preds)] - preds
    return float(np.std(resid, ddof=1)) if len(resid) > 1 else 0.0


# ── Baseline models ──────────────────────────────────────────────────────────

def naive_forecast(train: np.ndarray, horizon: int) -> ForecastFrame:
    """Last-value naive forecast."""
    last = float(train[-1]) if len(train) else 0.0
    preds = np.full(horizon, last)
    return ForecastFrame(
        predictions=preds,
        mu_d=float(np.mean(train)),
        sigma_d=float(np.std(train, ddof=1)) if len(train) > 1 else 0.0,
        model_name="naive",
    )


def seasonal_naive_forecast(train: np.ndarray, horizon: int) -> ForecastFrame:
    """Same-weekday-last-week seasonal naive."""
    n = len(train)
    preds = np.array(
        [train[max(0, n - _SEASON_PERIOD + (i % _SEASON_PERIOD))] for i in range(horizon)],
        dtype=float,
    )
    return ForecastFrame(
        predictions=preds,
        mu_d=float(np.mean(train)),
        sigma_d=float(np.std(train, ddof=1)) if len(train) > 1 else 0.0,
        model_name="seasonal_naive",
    )


def moving_average_forecast(train: np.ndarray, horizon: int, window: int = 14) -> ForecastFrame:
    """14-day trailing moving average."""
    ma_val = float(np.mean(train[-window:])) if len(train) >= window else float(np.mean(train))
    preds = np.full(horizon, ma_val)
    return ForecastFrame(
        predictions=preds,
        mu_d=float(np.mean(train)),
        sigma_d=float(np.std(train, ddof=1)) if len(train) > 1 else 0.0,
        model_name="moving_average_14d",
    )


# ── Proposed models ──────────────────────────────────────────────────────────

def holt_winters_forecast(
    train: np.ndarray,
    horizon: int,
    promo_flags: np.ndarray | None = None,
) -> ForecastFrame:
    """
    Additive Holt-Winters with weekly seasonality.
    Falls back to simple exponential smoothing if fewer than 2 full seasons exist.
    """
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    mu_d = float(np.mean(train))
    sigma_d = float(np.std(train, ddof=1)) if len(train) > 1 else 0.0

    n = len(train)
    try:
        if n >= _MIN_HW_POINTS:
            model = ExponentialSmoothing(
                train.astype(float),
                trend="add",
                seasonal="add",
                seasonal_periods=_SEASON_PERIOD,
                initialization_method="estimated",
            ).fit(optimized=True, disp=False)
            preds = np.clip(model.forecast(horizon), 0, None)
            model_name = "holt_winters"
        else:
            # Too short for seasonal model — use simple exponential smoothing
            model = ExponentialSmoothing(
                train.astype(float),
                trend=None,
                seasonal=None,
                initialization_method="estimated",
            ).fit(optimized=True, disp=False)
            preds = np.clip(model.forecast(horizon), 0, None)
            model_name = "exp_smoothing"
    except Exception:
        # Absolute fallback: moving average
        preds = np.full(horizon, max(mu_d, 0.0))
        model_name = "moving_average_fallback"

    return ForecastFrame(
        predictions=preds,
        mu_d=float(np.mean(preds)),
        sigma_d=sigma_d,
        model_name=model_name,
    )


def regression_forecast(
    train: np.ndarray,
    horizon: int,
    train_dates: pd.DatetimeIndex,
    promo_flags: np.ndarray | None = None,
) -> ForecastFrame:
    """
    OLS regression with:
      - Linear trend (day index)
      - Weekday dummies (6 of 7)
      - Promo flag (if available)
    """
    import warnings
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant

    n = len(train)
    trend = np.arange(n, dtype=float)

    # Weekday dummies (Mon=0 … Sun=6; drop Sunday to avoid multicollinearity)
    weekdays = train_dates.dayofweek.values
    wd_dummies = np.zeros((n, 6), dtype=float)
    for w in range(6):
        wd_dummies[:, w] = (weekdays == w).astype(float)

    features = np.column_stack([trend, wd_dummies])
    if promo_flags is not None and len(promo_flags) == n:
        features = np.column_stack([features, promo_flags])

    features = add_constant(features)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = OLS(train.astype(float), features).fit()

        # Build future feature matrix
        future_trend = np.arange(n, n + horizon, dtype=float)
        future_dates = pd.date_range(train_dates[-1] + pd.Timedelta("1D"), periods=horizon, freq="D")
        future_weekdays = future_dates.dayofweek.values
        future_wd = np.zeros((horizon, 6), dtype=float)
        for w in range(6):
            future_wd[:, w] = (future_weekdays == w).astype(float)
        future_features = np.column_stack([future_trend, future_wd])
        if promo_flags is not None:
            future_features = np.column_stack([future_features, np.zeros(horizon)])
        future_features = add_constant(future_features, has_constant="add")

        preds = np.clip(fit.predict(future_features), 0, None)
        mu_d = float(np.mean(preds))
        sigma_d = float(np.std(train, ddof=1)) if n > 1 else 0.0
        return ForecastFrame(predictions=preds, mu_d=mu_d, sigma_d=sigma_d, model_name="regression")

    except Exception:
        # Fallback
        return moving_average_forecast(train, horizon)
