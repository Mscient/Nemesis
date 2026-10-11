"""
Orchestration service — B5, B6, B7, B8, B9, B10.
This is the ONLY place where core and ai meet.
All mapping between core results and api schemas lives here.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repositories as repo
from app.db.models import SkuModel, AnomalyModel, AdjustmentModel
from app.schemas import (
    AnomalyRecord, EvaluationMetrics, EvaluationResponse,
    ForecastResponse, ForecastSummary,
    RecommendationInputs, RecommendationResponse,
    ScenarioResponse, SimulationSummary,
    SkuDetail, SkuParams, SkuSummary, SalesPoint,
    SkuHistoryResponse, AdjustmentRecord,
)

log = logging.getLogger(__name__)


# ─── Helpers: model → schema ──────────────────────────────────────────────────

def _sku_params_from_model(m: SkuModel) -> SkuParams:
    return SkuParams(
        lead_time_days=m.lead_time_days,
        lead_time_std_days=m.lead_time_std_days,
        unit_cost=m.unit_cost,
        order_cost=m.order_cost,
        holding_cost_per_unit_per_year=m.holding_cost_per_unit_per_year,
        stockout_penalty_per_unit=m.stockout_penalty_per_unit,
        moq=m.moq,
        pack_size=m.pack_size,
        max_storage=m.max_storage,
        service_level=m.service_level,
        on_hand=m.on_hand,
        on_order=m.on_order,
    )


def _anomaly_from_model(a: AnomalyModel) -> AnomalyRecord:
    return AnomalyRecord(
        id=a.id,
        sku=a.sku,
        date=a.date,
        value=a.value,
        expected_value=a.expected_value,
        robust_z=a.robust_z,
        flags=a.flags,
        cls=a.cls,
        treatment=a.treatment,
        source=a.source,
        status=a.status,
        rationale=a.rationale,
    )


def _adjustment_from_model(a: AdjustmentModel) -> AdjustmentRecord:
    return AdjustmentRecord(
        id=a.id,
        sku=a.sku,
        start_date=a.start_date,
        end_date=a.end_date,
        multiplier=a.multiplier,
        rationale=a.rationale,
        confidence=a.confidence,
        source=a.source,
        status=a.status,
    )


# ─── B5: SKU services ─────────────────────────────────────────────────────────

async def list_skus_with_status(db: AsyncSession) -> list[SkuSummary]:
    """Return all SKUs with derived OK/REORDER/AT_RISK status."""
    skus = await repo.get_all_skus(db)
    results = []
    for m in skus:
        inv_pos = m.on_hand + m.on_order
        # try to compute ROP from latest forecast — best effort
        rop = None
        try:
            from stocksense_core import run_forecast, compute_recommendation, SalesRecord, SkuParams as CoreParams, CleanedSeries
            records_db = await repo.get_sales_records(db, m.sku)
            if records_db:
                core_records = [
                    SalesRecord(date=r.date, sku=r.sku, units_sold=r.units_sold,
                                on_hand=r.on_hand, promo_flag=r.promo_flag)
                    for r in records_db
                ]
                cleaned = CleanedSeries(records=tuple(core_records))
                forecast = run_forecast(cleaned)
                core_params = CoreParams(
                    sku=m.sku,
                    lead_time_days=m.lead_time_days,
                    lead_time_std_days=m.lead_time_std_days,
                    unit_cost=m.unit_cost,
                    order_cost=m.order_cost,
                    holding_cost_per_unit_per_year=m.holding_cost_per_unit_per_year,
                    stockout_penalty_per_unit=m.stockout_penalty_per_unit,
                    moq=m.moq,
                    pack_size=m.pack_size,
                    max_storage=m.max_storage,
                    service_level=m.service_level,
                    on_hand=m.on_hand,
                    on_order=m.on_order,
                )
                rec = compute_recommendation(core_params, forecast)
                rop = rec.reorder_point
        except Exception as exc:
            log.debug("Could not compute ROP for SKU %s: %s", m.sku, exc)

        if rop is None:
            status = "OK"
        elif inv_pos <= rop * 0.5:
            status = "AT_RISK"
        elif inv_pos <= rop:
            status = "REORDER"
        else:
            status = "OK"

        results.append(SkuSummary(
            sku=m.sku,
            name=m.name,
            status=status,
            inventory_position=inv_pos,
            reorder_point=rop,
            on_hand=m.on_hand,
            on_order=m.on_order,
            is_synthetic=m.is_synthetic,
        ))
    return results


async def get_sku_detail(db: AsyncSession, sku: str) -> Optional[SkuDetail]:
    m = await repo.get_sku(db, sku)
    if m is None:
        return None
    inv_pos = m.on_hand + m.on_order
    rop = None
    status = "OK"
    try:
        from stocksense_core import run_forecast, compute_recommendation, SalesRecord, SkuParams as CoreParams, CleanedSeries
        records_db = await repo.get_sales_records(db, sku)
        if records_db:
            core_records = [SalesRecord(date=r.date, sku=r.sku, units_sold=r.units_sold, on_hand=r.on_hand, promo_flag=r.promo_flag) for r in records_db]
            cleaned = CleanedSeries(records=tuple(core_records))
            forecast = run_forecast(cleaned)
            core_params = CoreParams(sku=m.sku, lead_time_days=m.lead_time_days, lead_time_std_days=m.lead_time_std_days,
                unit_cost=m.unit_cost, order_cost=m.order_cost, holding_cost_per_unit_per_year=m.holding_cost_per_unit_per_year,
                stockout_penalty_per_unit=m.stockout_penalty_per_unit, moq=m.moq, pack_size=m.pack_size, max_storage=m.max_storage,
                service_level=m.service_level, on_hand=m.on_hand, on_order=m.on_order)
            rec = compute_recommendation(core_params, forecast)
            rop = rec.reorder_point
    except Exception as exc:
        log.debug("Could not compute ROP for sku %s: %s", sku, exc)

    if rop is None:
        status = "OK"
    elif inv_pos <= rop * 0.5:
        status = "AT_RISK"
    elif inv_pos <= rop:
        status = "REORDER"
    else:
        status = "OK"

    return SkuDetail(
        sku=m.sku,
        name=m.name,
        status=status,
        params=_sku_params_from_model(m),
        is_synthetic=m.is_synthetic,
        created_at=m.created_at,
    )


async def update_sku_params_service(
    db: AsyncSession, sku: str, params: SkuParams
) -> Optional[SkuDetail]:
    await repo.update_sku_params(db, sku, **params.model_dump())
    return await get_sku_detail(db, sku)


# ─── B5: History ──────────────────────────────────────────────────────────────

async def get_sku_history(db: AsyncSession, sku: str) -> SkuHistoryResponse:
    records_db = await repo.get_sales_records(db, sku)
    anomalies_db = await repo.get_anomalies(db, sku)
    anomaly_dates = {a.date for a in anomalies_db if a.status != "dismissed"}
    dismissed_dates = {a.date for a in anomalies_db if a.status == "dismissed"}

    raw = [
        SalesPoint(
            date=r.date,
            units_sold=r.units_sold,
            on_hand=r.on_hand,
            promo_flag=r.promo_flag,
            is_anomaly=r.date in anomaly_dates,
            is_cleaned=False,
        )
        for r in records_db
    ]
    # "cleaned" = exclude dismissed anomalies from raw for chart purposes
    cleaned = [p for p in raw if p.date not in dismissed_dates]

    return SkuHistoryResponse(sku=sku, raw=raw, cleaned=cleaned)


# ─── B7: Anomalies ────────────────────────────────────────────────────────────

async def list_anomalies(db: AsyncSession, sku: str) -> list[AnomalyRecord]:
    rows = await repo.get_anomalies(db, sku)
    return [_anomaly_from_model(r) for r in rows]


async def reclassify_anomaly(
    db: AsyncSession, anomaly_id: int, cls: str, status: str, rationale: Optional[str]
) -> Optional[AnomalyRecord]:
    obj = await repo.update_anomaly(db, anomaly_id, cls=cls, status=status, source="user", rationale=rationale)
    if obj is None:
        return None
    return _anomaly_from_model(obj)


# ─── B6: Forecast & Evaluation ────────────────────────────────────────────────

async def _build_forecast(db: AsyncSession, sku: str, horizon_days: int = 14) -> Optional[ForecastResponse]:
    """Internal helper: load records, clean, forecast, persist run."""
    try:
        from stocksense_core import (
            SalesRecord, CleanedSeries, AnomalyFlag, Adjustment,
            detect_anomalies, clean_series, run_forecast,
        )
    except ImportError as e:
        log.error("stocksense_core not available: %s", e)
        return None

    records_db = await repo.get_sales_records(db, sku)
    if not records_db:
        return None

    anomalies_db = await repo.get_anomalies(db, sku)
    core_records = [
        SalesRecord(date=r.date, sku=r.sku, units_sold=r.units_sold, on_hand=r.on_hand, promo_flag=r.promo_flag)
        for r in records_db
    ]

    # user decisions for anomaly treatment
    user_decisions: dict = {}
    for a in anomalies_db:
        if a.source == "user" and a.status == "confirmed":
            user_decisions[a.date] = a.cls

    flags = detect_anomalies(core_records)
    cleaned = clean_series(core_records, flags, user_decisions=user_decisions)

    # accepted adjustments
    adj_db = await repo.get_accepted_adjustments(db, sku)
    core_adjustments = tuple(
        Adjustment(start_date=a.start_date, end_date=a.end_date, multiplier=a.multiplier, source=a.source)
        for a in adj_db
    )

    result = run_forecast(cleaned, horizon_days=horizon_days, adjustments=core_adjustments)

    metrics = [
        EvaluationMetrics(model_name=e.model_name, mae=e.mae, rmse=e.rmse, wape=e.wape, bias=e.bias)
        for e in result.evaluation
    ]

    # persist
    await repo.save_forecast_run(db, sku, {
        "model_used": result.model_used,
        "horizon_days": horizon_days,
        "mu_d": result.mu_d,
        "sigma_d": result.sigma_d,
        "confidence": result.confidence,
        "predictions": list(result.predictions),
        "metrics": [m.model_dump() for m in metrics],
        "warnings": list(result.warnings),
    })

    return ForecastResponse(
        sku=sku,
        horizon_days=horizon_days,
        model_used=result.model_used,
        avg_daily_demand=result.mu_d,
        sigma_daily=result.sigma_d,
        predictions=list(result.predictions),
        confidence=result.confidence,
        warnings=list(result.warnings),
        evaluation=metrics,
    ), result


async def get_forecast(db: AsyncSession, sku: str, horizon_days: int) -> Optional[ForecastResponse]:
    out = await _build_forecast(db, sku, horizon_days)
    if out is None:
        return None
    response, _ = out
    return response


async def get_evaluation(db: AsyncSession, sku: str) -> Optional[EvaluationResponse]:
    out = await _build_forecast(db, sku)
    if out is None:
        return None
    _, result = out
    metrics = [
        EvaluationMetrics(model_name=e.model_name, mae=e.mae, rmse=e.rmse, wape=e.wape, bias=e.bias)
        for e in result.evaluation
    ]
    # baseline_wins if the proposed model is worse or equal on MAE vs the best baseline
    baseline_wins = False
    names = [m.model_name for m in metrics]
    if "stub" not in result.model_used and len(metrics) >= 2:
        proposed = next((m for m in metrics if m.model_name not in ("naive", "seasonal_naive", "moving_average")), None)
        baselines = [m for m in metrics if m != proposed]
        if proposed and baselines:
            best_baseline_mae = min(b.mae for b in baselines)
            baseline_wins = proposed.mae >= best_baseline_mae

    return EvaluationResponse(
        sku=sku,
        baseline_wins=baseline_wins,
        metrics=metrics,
    )


# ─── B8: Recommendation ───────────────────────────────────────────────────────

async def compute_recommendation_service(db: AsyncSession, sku: str) -> Optional[RecommendationResponse]:
    m = await repo.get_sku(db, sku)
    if m is None:
        return None

    try:
        from stocksense_core import (
            SalesRecord, CleanedSeries, Adjustment,
            detect_anomalies, clean_series, run_forecast,
            compute_recommendation, SkuParams as CoreParams,
        )
    except ImportError as e:
        log.error("stocksense_core not available: %s", e)
        return None

    records_db = await repo.get_sales_records(db, sku)
    if not records_db:
        return None

    core_records = [
        SalesRecord(date=r.date, sku=r.sku, units_sold=r.units_sold, on_hand=r.on_hand, promo_flag=r.promo_flag)
        for r in records_db
    ]

    anomalies_db = await repo.get_anomalies(db, sku)
    user_decisions = {a.date: a.cls for a in anomalies_db if a.source == "user" and a.status == "confirmed"}

    flags = detect_anomalies(core_records)
    cleaned = clean_series(core_records, flags, user_decisions=user_decisions)

    adj_db = await repo.get_accepted_adjustments(db, sku)
    core_adjustments = tuple(
        Adjustment(start_date=a.start_date, end_date=a.end_date, multiplier=a.multiplier, source=a.source)
        for a in adj_db
    )

    forecast = run_forecast(cleaned, adjustments=core_adjustments)
    core_params = CoreParams(
        sku=m.sku, lead_time_days=m.lead_time_days, lead_time_std_days=m.lead_time_std_days,
        unit_cost=m.unit_cost, order_cost=m.order_cost,
        holding_cost_per_unit_per_year=m.holding_cost_per_unit_per_year,
        stockout_penalty_per_unit=m.stockout_penalty_per_unit, moq=m.moq,
        pack_size=m.pack_size, max_storage=m.max_storage, service_level=m.service_level,
        on_hand=m.on_hand, on_order=m.on_order,
    )

    rec = compute_recommendation(core_params, forecast)

    return RecommendationResponse(
        sku=rec.sku,
        as_of=rec.as_of,
        action=rec.action,
        order_quantity=rec.order_quantity,
        inventory_position=rec.inventory_position,
        reorder_point=rec.reorder_point,
        safety_stock=rec.safety_stock,
        forecast=ForecastSummary(model=forecast.model_used, avg_daily_demand=forecast.mu_d, sigma_daily=forecast.sigma_d),
        inputs=RecommendationInputs(
            service_level=core_params.service_level,
            z_factor=rec.z_factor,
            lead_time_days=m.lead_time_days,
            lead_time_std_days=m.lead_time_std_days,
        ),
        formulas=dict(rec.formulas),
        assumptions=list(rec.assumptions),
        ai_adjustments=list(rec.ai_adjustments),
        warnings=list(rec.warnings),
        confidence=rec.confidence,
    )


# ─── B9: Scenarios ────────────────────────────────────────────────────────────

async def run_scenario_service(
    db: AsyncSession, sku: str, scenario_type: str,
    demand_surge_pct: float = 0.0, demand_surge_days: int = 0,
    supplier_delay_days: int = 0, supplier_delay_sigma: float = 0.0,
) -> Optional[ScenarioResponse]:
    m = await repo.get_sku(db, sku)
    if m is None:
        return None

    try:
        from stocksense_core import (
            SalesRecord, CleanedSeries, Adjustment, ScenarioSpec,
            detect_anomalies, clean_series, run_forecast,
            run_scenario, SkuParams as CoreParams,
        )
    except ImportError as e:
        log.error("stocksense_core not available: %s", e)
        return None

    records_db = await repo.get_sales_records(db, sku)
    core_records = [
        SalesRecord(date=r.date, sku=r.sku, units_sold=r.units_sold, on_hand=r.on_hand, promo_flag=r.promo_flag)
        for r in records_db
    ]
    flags = detect_anomalies(core_records)
    cleaned = clean_series(core_records, flags)
    forecast = run_forecast(cleaned)

    core_params = CoreParams(
        sku=m.sku, lead_time_days=m.lead_time_days, lead_time_std_days=m.lead_time_std_days,
        unit_cost=m.unit_cost, order_cost=m.order_cost,
        holding_cost_per_unit_per_year=m.holding_cost_per_unit_per_year,
        stockout_penalty_per_unit=m.stockout_penalty_per_unit, moq=m.moq,
        pack_size=m.pack_size, max_storage=m.max_storage, service_level=m.service_level,
        on_hand=m.on_hand, on_order=m.on_order,
    )

    spec = ScenarioSpec(
        scenario_type=scenario_type,
        demand_surge_pct=demand_surge_pct,
        demand_surge_days=demand_surge_days,
        supplier_delay_days=supplier_delay_days,
        supplier_delay_sigma=supplier_delay_sigma,
    )

    comparison = run_scenario(core_params, forecast, spec)

    def _sim(s) -> SimulationSummary:
        return SimulationSummary(
            stockout_probability=s.stockout_probability,
            expected_unmet_units=s.expected_unmet_units,
            average_inventory=s.average_inventory,
            total_cost_p10=s.total_cost_p10,
            total_cost_p50=s.total_cost_p50,
            total_cost_p90=s.total_cost_p90,
        )

    response = ScenarioResponse(
        sku=sku,
        scenario_type=scenario_type,
        before=_sim(comparison.before),
        after=_sim(comparison.after),
        delta_rop=comparison.delta_rop,
        delta_safety_stock=comparison.delta_safety_stock,
        recommended_action=comparison.recommended_action,
    )

    # persist
    await repo.save_scenario(db, sku,
        params={"scenario_type": scenario_type, "demand_surge_pct": demand_surge_pct,
                "demand_surge_days": demand_surge_days, "supplier_delay_days": supplier_delay_days},
        results=response.model_dump(mode="json"),
    )

    return response


# ─── B10: AI glue ─────────────────────────────────────────────────────────────

async def suggest_anomaly_labels_service(
    db: AsyncSession, sku: str, anomaly_ids: Optional[list[int]] = None
) -> list[AnomalyRecord]:
    """Call ai.suggest_anomaly_labels, persist ai source, return updated anomalies."""
    rows = await repo.get_open_anomalies(db, sku)
    if anomaly_ids is not None:
        rows = [r for r in rows if r.id in anomaly_ids]
    if not rows:
        return []

    try:
        from stocksense_ai import suggest_anomaly_labels, AnomalyContext
        from stocksense_ai.schemas import AIAuditRecord
        items = [
            AnomalyContext(
                anomaly_id=a.id, sku=a.sku, date=a.date, value=a.value,
                expected_value=a.expected_value, robust_z=a.robust_z, flags=a.flags,
            )
            for a in rows
        ]
        t0 = time.monotonic()
        batch = await suggest_anomaly_labels(items)
        latency = (time.monotonic() - t0) * 1000

        # persist audit
        await repo.log_ai_call(db, {
            "task": "suggest_anomaly_labels",
            "model": "mock",
            "prompt_version": "v1",
            "latency_ms": latency,
            "validation_outcome": "ok",
        })

        # update anomaly rows with AI suggestion (source="ai", status stays "open")
        for sug in batch.suggestions:
            obj = await repo.get_anomaly_by_id(db, sug.anomaly_id)
            if obj:
                obj.cls = sug.cls
                obj.source = "ai"
                obj.rationale = sug.rationale
                await db.flush()

    except Exception as exc:
        log.warning("AI suggestion failed: %s", exc)

    updated = await repo.get_anomalies(db, sku)
    return [_anomaly_from_model(r) for r in updated]


async def explain_recommendation_service(
    db: AsyncSession, sku: str, audience: str, recommendation: Optional[dict]
) -> dict:
    """Call ai.explain_recommendation and return {explanation, used_fallback}."""
    if recommendation is None:
        rec_response = await compute_recommendation_service(db, sku)
        if rec_response is None:
            recommendation = {}
        else:
            recommendation = rec_response.model_dump(mode="json")

    try:
        from stocksense_ai import explain_recommendation, ExplainRequest
        req = ExplainRequest(sku=sku, audience=audience, recommendation=recommendation)
        t0 = time.monotonic()
        result = await explain_recommendation(req)
        latency = (time.monotonic() - t0) * 1000

        await repo.log_ai_call(db, {
            "task": "explain_recommendation",
            "model": "mock",
            "prompt_version": "v1",
            "latency_ms": latency,
            "validation_outcome": "ok",
        })

        return {"explanation": result.explanation, "used_fallback": result.used_fallback}
    except Exception as exc:
        log.warning("AI explain failed: %s", exc)
        return {"explanation": "Explanation unavailable.", "used_fallback": True}


async def propose_adjustments_service(
    db: AsyncSession, sku: str, event_notes: str, forecast_summary: Optional[dict]
) -> list[AdjustmentRecord]:
    """Call ai.propose_forecast_adjustments, persist proposals, return list."""
    if forecast_summary is None:
        fc = await get_forecast(db, sku, 14)
        forecast_summary = fc.model_dump(mode="json") if fc else {}

    try:
        from stocksense_ai import propose_forecast_adjustments, AdjustmentRequest
        req = AdjustmentRequest(sku=sku, event_notes=event_notes, forecast_summary=forecast_summary)
        t0 = time.monotonic()
        batch = await propose_forecast_adjustments(req)
        latency = (time.monotonic() - t0) * 1000

        await repo.log_ai_call(db, {
            "task": "propose_forecast_adjustments",
            "model": "mock",
            "prompt_version": "v1",
            "latency_ms": latency,
            "validation_outcome": "ok",
        })

        for p in batch.proposals:
            await repo.save_adjustment(db, {
                "sku": sku,
                "start_date": p.start_date,
                "end_date": p.end_date,
                "multiplier": p.multiplier,
                "rationale": p.rationale,
                "confidence": p.confidence,
                "source": "ai",
                "status": "proposed",
            })

    except Exception as exc:
        log.warning("AI propose_adjustments failed: %s", exc)

    rows = await repo.get_adjustments(db, sku)
    return [_adjustment_from_model(r) for r in rows]


async def list_adjustments_service(db: AsyncSession, sku: str) -> list[AdjustmentRecord]:
    rows = await repo.get_adjustments(db, sku)
    return [_adjustment_from_model(r) for r in rows]


async def update_adjustment_service(db: AsyncSession, adj_id: int, status: str) -> Optional[AdjustmentRecord]:
    obj = await repo.update_adjustment_status(db, adj_id, status)
    if obj is None:
        return None
    return _adjustment_from_model(obj)
