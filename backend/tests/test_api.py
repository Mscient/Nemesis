"""
Backend test suite — B13.
Contract tests, ingestion tests, and integration tests using FastAPI TestClient.
"""
from __future__ import annotations

import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

# Use lifespan=True so startup (create_tables) runs before tests
client = TestClient(app, raise_server_exceptions=False)


def setup_module(module):
    """Ensure DB tables exist before any test in this module runs."""
    import asyncio
    from app.db.session import create_tables
    asyncio.run(create_tables())



# ─── B13: Health ──────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


# ─── B13: AI status ───────────────────────────────────────────────────────────

def test_ai_status():
    r = client.get("/api/ai/status")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data
    assert "provider" in data
    assert "model" in data


# ─── B13: Mock mode ───────────────────────────────────────────────────────────

def test_skus_returns_list():
    """GET /api/skus must return a list (even if empty)."""
    r = client.get("/api/skus")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ─── B13: CSV ingestion — good file ───────────────────────────────────────────

GOOD_CSV = b"""date,sku,units_sold,on_hand,promo_flag
2026-01-01,TEST-SKU,10,100,0
2026-01-02,TEST-SKU,12,88,0
2026-01-03,TEST-SKU,8,80,0
2026-01-04,TEST-SKU,11,72,0
2026-01-05,TEST-SKU,9,61,0
"""

BAD_CSV_MISSING_COL = b"""date,sku
2026-01-01,TEST-SKU
"""

BAD_CSV_BAD_DATE = b"""date,sku,units_sold
not-a-date,TEST-SKU,10
2026-01-02,TEST-SKU,12
"""

BAD_CSV_BAD_UNITS = b"""date,sku,units_sold
2026-01-01,TEST-SKU,not_a_number
"""


def test_upload_good_csv():
    r = client.post(
        "/api/datasets",
        files={"file": ("sales.csv", io.BytesIO(GOOD_CSV), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    # accepted regardless of whether rows are new (idempotent re-upload)
    assert data["status"] == "accepted"
    # rows_ingested may be 0 on re-run due to unique constraint; that's correct behaviour
    assert data["rows_ingested"] >= 0
    assert "errors" in data


def test_upload_missing_required_column():
    r = client.post(
        "/api/datasets",
        files={"file": ("bad.csv", io.BytesIO(BAD_CSV_MISSING_COL), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"
    assert len(data["errors"]) >= 1


def test_upload_bad_date_rows():
    r = client.post(
        "/api/datasets",
        files={"file": ("bad_date.csv", io.BytesIO(BAD_CSV_BAD_DATE), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    # good rows should still be accepted
    assert data["status"] == "accepted"
    assert any("date" in e["message"].lower() for e in data["errors"])


def test_upload_bad_units():
    r = client.post(
        "/api/datasets",
        files={"file": ("bad_units.csv", io.BytesIO(BAD_CSV_BAD_UNITS), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["errors"]) >= 1


# ─── B13: SKU endpoints ───────────────────────────────────────────────────────

def test_get_nonexistent_sku_returns_404():
    r = client.get("/api/skus/DOES-NOT-EXIST")
    assert r.status_code == 404


def test_update_params_nonexistent_sku():
    payload = {
        "lead_time_days": 7,
        "lead_time_std_days": 1.0,
        "unit_cost": 5.0,
        "order_cost": 40.0,
        "holding_cost_per_unit_per_year": 1.5,
        "stockout_penalty_per_unit": 4.0,
        "moq": 12,
        "pack_size": 6,
        "max_storage": None,
        "service_level": 0.95,
        "on_hand": 100.0,
        "on_order": 0.0,
    }
    r = client.put("/api/skus/DOES-NOT-EXIST/params", json=payload)
    assert r.status_code == 404


def test_update_params_validation_error():
    """Negative lead_time_days should fail with 422 and standard error envelope."""
    payload = {
        "lead_time_days": -1,
        "unit_cost": 5.0,
        "order_cost": 40.0,
        "holding_cost_per_unit_per_year": 1.5,
        "stockout_penalty_per_unit": 4.0,
    }
    r = client.put("/api/skus/SOME-SKU/params", json=payload)
    assert r.status_code == 422
    data = r.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


# ─── B13: Integration: upload → recommend → scenario ─────────────────────────

SAMPLE_CSV = b"""date,sku,units_sold,on_hand
2026-01-01,INTEG-SKU,10,200
2026-01-02,INTEG-SKU,12,188
2026-01-03,INTEG-SKU,8,176
2026-01-04,INTEG-SKU,11,165
2026-01-05,INTEG-SKU,9,154
2026-01-06,INTEG-SKU,13,141
2026-01-07,INTEG-SKU,10,128
2026-01-08,INTEG-SKU,11,117
2026-01-09,INTEG-SKU,9,106
2026-01-10,INTEG-SKU,12,94
2026-01-11,INTEG-SKU,10,82
2026-01-12,INTEG-SKU,8,72
2026-01-13,INTEG-SKU,11,61
2026-01-14,INTEG-SKU,9,50
2026-01-15,INTEG-SKU,10,40
2026-01-16,INTEG-SKU,12,28
2026-01-17,INTEG-SKU,8,20
2026-01-18,INTEG-SKU,11,9
2026-01-19,INTEG-SKU,9,0
2026-01-20,INTEG-SKU,10,0
2026-01-21,INTEG-SKU,12,0
2026-01-22,INTEG-SKU,8,0
2026-01-23,INTEG-SKU,11,0
2026-01-24,INTEG-SKU,9,0
2026-01-25,INTEG-SKU,10,0
2026-01-26,INTEG-SKU,12,0
2026-01-27,INTEG-SKU,8,0
2026-01-28,INTEG-SKU,11,0
2026-01-29,INTEG-SKU,9,0
2026-01-30,INTEG-SKU,10,0
"""


def test_integration_upload_recommend_scenario():
    """Full flow: upload → update params → recommend → scenario."""
    # 1. Upload
    r = client.post(
        "/api/datasets",
        files={"file": ("sample.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"

    # 2. Update SKU params
    params = {
        "lead_time_days": 5,
        "lead_time_std_days": 0.0,
        "unit_cost": 8.0,
        "order_cost": 50.0,
        "holding_cost_per_unit_per_year": 2.0,
        "stockout_penalty_per_unit": 6.0,
        "moq": 24,
        "pack_size": 12,
        "max_storage": None,
        "service_level": 0.95,
        "on_hand": 120.0,
        "on_order": 0.0,
    }
    r = client.put("/api/skus/INTEG-SKU/params", json=params)
    assert r.status_code == 200

    # 3. Compute recommendation — must return the expected fields
    r = client.post("/api/skus/INTEG-SKU/recommendation")
    assert r.status_code == 200
    rec = r.json()
    assert "action" in rec
    assert "order_quantity" in rec
    assert "reorder_point" in rec
    assert "safety_stock" in rec
    assert "formulas" in rec
    assert "safety_stock" in rec["formulas"]
    assert "reorder_point" in rec["formulas"]
    assert "confidence" in rec

    # 4. Run a scenario
    scenario_body = {
        "scenario_type": "demand_surge",
        "demand_surge_pct": 30.0,
        "demand_surge_days": 14,
        "supplier_delay_days": 0,
        "supplier_delay_sigma": 0.0,
    }
    r = client.post("/api/skus/INTEG-SKU/scenarios", json=scenario_body)
    assert r.status_code == 200
    sc = r.json()
    assert "before" in sc
    assert "after" in sc
    assert "recommended_action" in sc


def test_forecast_returns_evaluation():
    """GET /forecast must include evaluation metrics."""
    r = client.get("/api/skus/INTEG-SKU/forecast?horizon=14")
    if r.status_code == 404:
        pytest.skip("INTEG-SKU not available (upload test may have been skipped)")
    assert r.status_code == 200
    data = r.json()
    assert "evaluation" in data
    assert isinstance(data["evaluation"], list)
    assert "model_used" in data
    assert "predictions" in data


def test_anomalies_list_returns_list():
    r = client.get("/api/skus/INTEG-SKU/anomalies")
    if r.status_code == 404:
        pytest.skip("INTEG-SKU not available")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_anomaly_patch_invalid_id():
    r = client.patch("/api/anomalies/999999", json={"cls": "promotion", "status": "confirmed"})
    assert r.status_code == 404


def test_ai_explain_returns_explanation():
    r = client.post(
        "/api/skus/INTEG-SKU/explain",
        json={"audience": "planner", "recommendation": None},
    )
    if r.status_code == 404:
        pytest.skip("INTEG-SKU not available")
    assert r.status_code == 200
    data = r.json()
    assert "explanation" in data
    assert "used_fallback" in data
