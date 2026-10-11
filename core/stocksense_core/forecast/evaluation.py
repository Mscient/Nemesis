"""
Forecast evaluation — D11.

Protocol (from spec §7.2):
  1. Sort history by date.
  2. Holdout = last 20% (minimum 14 days).
  3. Fit on training slice, forecast the holdout window.
  4. Compute MAE, RMSE, WAPE, Bias.
  5. Best baseline wins rule: if proposed model does not beat the best baseline,
     return the baseline ForecastFrame as the chosen model.

The chosen-model rule uses WAPE as the primary metric (robust to scale).
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd

from stocksense_core.types import EvaluationMetrics
from stocksense_core.forecast.models import (
    ForecastFrame,
    naive_forecast,
    seasonal_naive_forecast,
    moving_average_forecast,
    holt_winters_forecast,
    regression_forecast,
)

_MIN_HOLDOUT_DAYS = 14


def _mae(actuals: np.ndarray, preds: np.ndarray) -> float:
    return float(np.mean(np.abs(actuals - preds)))


def _rmse(actuals: np.ndarray, preds: np.ndarray) -> float:
    return float(math.sqrt(np.mean((actuals - preds) ** 2)))


def _wape(actuals: np.ndarray, preds: np.ndarray) -> float:
    denom = float(np.sum(np.abs(actuals)))
    if denom == 0:
        return 0.0
    return float(np.sum(np.abs(actuals - preds))) / denom


def _bias(actuals: np.ndarray, preds: np.ndarray) -> float:
    return float(np.mean(preds - actuals))


def _metrics(actuals: np.ndarray, preds: np.ndarray, model_name: str) -> EvaluationMetrics:
    n = min(len(actuals), len(preds))
    a, p = actuals[:n], preds[:n]
    return EvaluationMetrics(
        mae=round(_mae(a, p), 4),
        rmse=round(_rmse(a, p), 4),
        wape=round(_wape(a, p), 4),
        bias=round(_bias(a, p), 4),
        model_name=model_name,
    )


def evaluate_models(
    values: np.ndarray,
    dates: pd.DatetimeIndex,
    promo_flags: np.ndarray | None,
    horizon_days: int,
    holdout_fraction: float = 0.2,
    adjustments: tuple = (),
) -> tuple[ForecastFrame, tuple[EvaluationMetrics, ...], list[str]]:
    """
    Split the series into train/holdout, fit baselines + proposed model,
    pick the winner, and return:
        (chosen_frame, evaluation_metrics_tuple, warnings)

    The chosen_frame is used to produce the final horizon forecast on the
    FULL series (train + holdout).
    """
    warnings_out: list[str] = []
    n = len(values)

    # ── 1. Compute holdout size ───────────────────────────────────────────────
    holdout_n = max(_MIN_HOLDOUT_DAYS, int(n * holdout_fraction))
    if holdout_n >= n:
        # Not enough data to hold out anything useful — use all data for fitting
        warnings_out.append(
            f"Only {n} days of history — cannot create a {holdout_n}-day holdout. "
            "Evaluation metrics are approximate."
        )
        holdout_n = max(1, n // 5)

    train_n = n - holdout_n
    if train_n < 1:
        train_n = 1
        holdout_n = n - 1

    train_vals = values[:train_n]
    holdout_vals = values[train_n:]
    train_dates = dates[:train_n]
    train_promo = promo_flags[:train_n] if promo_flags is not None else None

    # ── 2. Fit baselines on training slice ───────────────────────────────────
    h = len(holdout_vals)

    naive_frame = naive_forecast(train_vals, h)
    sn_frame = seasonal_naive_forecast(train_vals, h)
    ma_frame = moving_average_forecast(train_vals, h)

    baseline_frames = [naive_frame, sn_frame, ma_frame]

    # ── 3. Fit proposed model ────────────────────────────────────────────────
    # Try Holt-Winters first; regression as alternative
    hw_frame = holt_winters_forecast(train_vals, h, train_promo)
    proposed_frame = hw_frame

    # ── 4. Compute holdout metrics ───────────────────────────────────────────
    ho = holdout_vals.astype(float)
    naive_metrics = _metrics(ho, naive_frame.predictions[:h], "naive")
    sn_metrics = _metrics(ho, sn_frame.predictions[:h], "seasonal_naive")
    ma_metrics = _metrics(ho, ma_frame.predictions[:h], "moving_average_14d")
    proposed_metrics = _metrics(ho, proposed_frame.predictions[:h], proposed_frame.model_name)

    all_baseline_metrics = [naive_metrics, sn_metrics, ma_metrics]
    best_baseline_wape = min(m.wape for m in all_baseline_metrics)

    # ── 5. Chosen-model rule ─────────────────────────────────────────────────
    if proposed_metrics.wape <= best_baseline_wape:
        chosen_name = proposed_frame.model_name
        warnings_out_note = None
    else:
        # Proposed did NOT beat the baseline — use best baseline
        best_idx = min(range(len(all_baseline_metrics)), key=lambda i: all_baseline_metrics[i].wape)
        proposed_frame = baseline_frames[best_idx]
        chosen_name = all_baseline_metrics[best_idx].model_name
        warnings_out.append(
            f"Proposed model ({hw_frame.model_name}) did not beat the best baseline "
            f"({chosen_name}) on holdout (WAPE {proposed_metrics.wape:.3f} vs "
            f"{best_baseline_wape:.3f}). Using baseline."
        )

    # ── 6. Re-fit chosen model on FULL series for final forecast ─────────────
    full_frame = _refit_full(chosen_name, values, dates, promo_flags, horizon_days, adjustments)

    # Update proposed_metrics model_name to match chosen
    final_proposed_metrics = EvaluationMetrics(
        mae=proposed_metrics.mae,
        rmse=proposed_metrics.rmse,
        wape=proposed_metrics.wape,
        bias=proposed_metrics.bias,
        model_name=chosen_name,
    )

    all_metrics = (naive_metrics, sn_metrics, ma_metrics, final_proposed_metrics)
    return full_frame, all_metrics, warnings_out


def _refit_full(
    model_name: str,
    values: np.ndarray,
    dates: pd.DatetimeIndex,
    promo_flags: np.ndarray | None,
    horizon: int,
    adjustments: tuple,
) -> ForecastFrame:
    """Refit the chosen model on the full series and return a ForecastFrame."""
    if model_name == "naive":
        frame = naive_forecast(values, horizon)
    elif model_name == "seasonal_naive":
        frame = seasonal_naive_forecast(values, horizon)
    elif model_name in ("moving_average_14d", "moving_average_fallback"):
        frame = moving_average_forecast(values, horizon)
    elif model_name == "regression":
        frame = regression_forecast(values, horizon, dates, promo_flags)
    else:
        # holt_winters or exp_smoothing
        frame = holt_winters_forecast(values, horizon, promo_flags)

    # Apply user-approved adjustments
    preds = frame.predictions.copy()
    for adj in adjustments:
        # adj is an Adjustment dataclass; convert date range to index offsets
        # We apply the multiplier to predictions whose future date falls in [start, end]
        future_dates = pd.date_range(dates[-1] + pd.Timedelta("1D"), periods=len(preds), freq="D")
        mask = (future_dates.date >= adj.start_date) & (future_dates.date <= adj.end_date)
        preds[mask] *= adj.multiplier

    preds = np.clip(preds, 0, None)
    return ForecastFrame(
        predictions=preds,
        mu_d=float(np.mean(preds)),
        sigma_d=frame.sigma_d,
        model_name=frame.model_name,
    )
