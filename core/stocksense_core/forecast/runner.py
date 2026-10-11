"""
Forecast runner — D10 + D11 (real implementation replacing the stub).

Entry point: run_forecast(cleaned, horizon_days, holdout_fraction, adjustments)
  1. Build a daily DataFrame from CleanedSeries.
  2. Delegate to evaluation.evaluate_models (which handles train/holdout split,
     model fitting, chosen-model rule, and refit on full series).
  3. Wrap the result in a ForecastResult.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stocksense_core.types import CleanedSeries, ForecastResult, EvaluationMetrics
from stocksense_core.series import build_daily_series
from stocksense_core.forecast.evaluation import evaluate_models

_LOW_CONFIDENCE_DAYS = 28


def run_forecast(
    cleaned: CleanedSeries,
    horizon_days: int = 14,
    holdout_fraction: float = 0.2,
    adjustments: tuple = (),
) -> ForecastResult:
    """
    Run the full forecasting pipeline on a CleanedSeries.

    Parameters
    ----------
    cleaned          : output of clean_series (chronologically sorted records)
    horizon_days     : number of future days to predict
    holdout_fraction : fraction of history to withhold for evaluation (default 0.2)
    adjustments      : tuple of approved Adjustment objects to apply post-fit

    Returns
    -------
    ForecastResult with predictions, mu_d, sigma_d, model_used, evaluation, confidence, warnings.
    """
    records = cleaned.records
    warnings_out: list[str] = []

    # ── Edge case: no data ────────────────────────────────────────────────────
    if not records:
        dummy = EvaluationMetrics(mae=0, rmse=0, wape=0, bias=0, model_name="no_data")
        return ForecastResult(
            sku="",
            predictions=tuple([0.0] * horizon_days),
            mu_d=0.0,
            sigma_d=0.0,
            model_used="no_data",
            evaluation=(dummy,),
            confidence="low",
            warnings=("No data available for forecasting.",),
        )

    sku = records[0].sku

    # ── Build daily DataFrame ────────────────────────────────────────────────
    df = build_daily_series(records)
    values = df["units_sold"].values.astype(float)
    dates = pd.DatetimeIndex(df["date"])
    promo_flags = df["promo_flag"].values.astype(float)

    n = len(values)

    # ── Low-history warning ──────────────────────────────────────────────────
    if n < _LOW_CONFIDENCE_DAYS:
        warnings_out.append(
            f"Only {n} days of history — low-confidence forecast. "
            "Minimum recommended: 28 days."
        )

    # ── Evaluate models and pick the winner ──────────────────────────────────
    chosen_frame, eval_metrics, eval_warnings = evaluate_models(
        values=values,
        dates=dates,
        promo_flags=promo_flags,
        horizon_days=horizon_days,
        holdout_fraction=holdout_fraction,
        adjustments=adjustments,
    )
    warnings_out.extend(eval_warnings)

    # ── Confidence level ─────────────────────────────────────────────────────
    if n < _LOW_CONFIDENCE_DAYS:
        confidence = "low"
    else:
        # Use holdout WAPE of the chosen model to gauge confidence
        chosen_metrics = next(
            (m for m in eval_metrics if m.model_name == chosen_frame.model_name),
            eval_metrics[-1],
        )
        wape = chosen_metrics.wape
        if wape < 0.15:
            confidence = "high"
        elif wape < 0.30:
            confidence = "medium"
        else:
            confidence = "low"
            warnings_out.append(
                f"High forecast error on holdout (WAPE={wape:.1%}). "
                "Recommend reviewing data quality."
            )

    return ForecastResult(
        sku=sku,
        predictions=tuple(float(v) for v in chosen_frame.predictions),
        mu_d=round(chosen_frame.mu_d, 4),
        sigma_d=round(chosen_frame.sigma_d, 4),
        model_used=chosen_frame.model_name,
        evaluation=tuple(eval_metrics),
        confidence=confidence,
        warnings=tuple(warnings_out),
    )
