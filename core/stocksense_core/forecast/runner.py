"""Stub — demand forecasting (Holt-Winters vs naive baseline)."""
from __future__ import annotations
import statistics
from stocksense_core.types import CleanedSeries, ForecastResult, EvaluationMetrics


def run_forecast(
    cleaned: CleanedSeries,
    horizon_days: int = 14,
    holdout_fraction: float = 0.2,
    adjustments: tuple = (),
) -> ForecastResult:
    """Stub: returns mean demand from cleaned records, no real model yet."""
    units = [r.units_sold for r in cleaned.records]
    mu_d = statistics.mean(units) if units else 0.0
    sigma_d = statistics.stdev(units) if len(units) > 1 else 0.0
    n = len(units)
    warnings: list[str] = []
    if n < 28:
        warnings.append(f"Only {n} days of history — low-confidence forecast.")

    dummy_eval = EvaluationMetrics(mae=0, rmse=0, wape=0, bias=0, model_name="stub")

    return ForecastResult(
        sku="",
        predictions=tuple([mu_d] * horizon_days),
        mu_d=mu_d,
        sigma_d=sigma_d,
        model_used="stub",
        evaluation=(dummy_eval,),
        confidence="low" if n < 28 else "medium",
        warnings=tuple(warnings),
    )
