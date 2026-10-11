"""
stocksense_core — Analytics core package.

Public API (all importable from `stocksense_core` directly):
  service_level_to_z, detect_anomalies, clean_series,
  run_forecast, compute_recommendation, simulate, run_scenario
"""
from stocksense_core.types import (
    SalesRecord, SkuParams, AnomalyFlag, Adjustment,
    ForecastResult, RecommendationResult, SimulationResult,
    ScenarioSpec, ScenarioComparison, CleanedSeries,
)
from stocksense_core.engine.z_factor import service_level_to_z
from stocksense_core.anomaly.detection import detect_anomalies
from stocksense_core.anomaly.treatment import clean_series
from stocksense_core.forecast.runner import run_forecast
from stocksense_core.engine.recommendation import compute_recommendation
from stocksense_core.simulation.monte_carlo import simulate
from stocksense_core.simulation.scenarios import run_scenario

__all__ = [
    "SalesRecord", "SkuParams", "AnomalyFlag", "Adjustment",
    "ForecastResult", "RecommendationResult", "SimulationResult",
    "ScenarioSpec", "ScenarioComparison", "CleanedSeries",
    "service_level_to_z", "detect_anomalies", "clean_series",
    "run_forecast", "compute_recommendation", "simulate", "run_scenario",
]
