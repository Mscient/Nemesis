"""
Error envelope conformance tests.
Every 4xx / 5xx must return:
  { "error": { "code": "...", "message": "...", "field": null | "field_name" } }
"""
from __future__ import annotations
import asyncio
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import create_tables

client = TestClient(app, raise_server_exceptions=False)


def setup_module(module):
    asyncio.run(create_tables())


def _assert_envelope(r, expected_status: int):
    assert r.status_code == expected_status, f"Got {r.status_code}: {r.text}"
    data = r.json()
    assert "error" in data, f"No 'error' key in response: {data}"
    err = data["error"]
    assert "code" in err,    f"'code' missing: {err}"
    assert "message" in err, f"'message' missing: {err}"
    assert "field" in err,   f"'field' missing: {err}"


# ── 404 — SKU not found ───────────────────────────────────────────────────────

def test_404_sku_not_found():
    r = client.get("/api/skus/DOES-NOT-EXIST-XYZ")
    _assert_envelope(r, 404)


def test_404_anomaly_patch():
    r = client.patch("/api/anomalies/99999999", json={"cls": "promotion", "status": "confirmed"})
    _assert_envelope(r, 404)


def test_404_recommendation_no_sku():
    r = client.post("/api/skus/NO-SUCH-SKU-ABC/recommendation")
    _assert_envelope(r, 404)


def test_404_scenario_no_sku():
    r = client.post("/api/skus/NO-SUCH-SKU-ABC/scenarios", json={
        "scenario_type": "demand_surge",
        "demand_surge_pct": 20.0,
        "demand_surge_days": 7,
        "supplier_delay_days": 0,
        "supplier_delay_sigma": 0.0,
    })
    _assert_envelope(r, 404)


# ── 422 — Validation errors ───────────────────────────────────────────────────

def test_422_negative_lead_time():
    payload = {
        "lead_time_days": -1,
        "unit_cost": 5.0,
        "order_cost": 40.0,
        "holding_cost_per_unit_per_year": 1.5,
        "stockout_penalty_per_unit": 4.0,
    }
    r = client.put("/api/skus/ANY-SKU/params", json=payload)
    _assert_envelope(r, 422)
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_422_forecast_horizon_zero():
    r = client.get("/api/skus/ANY-SKU/forecast?horizon=0")
    assert r.status_code == 422


def test_422_forecast_horizon_too_large():
    r = client.get("/api/skus/ANY-SKU/forecast?horizon=999")
    assert r.status_code == 422


def test_422_invalid_scenario_type():
    r = client.post("/api/skus/ANY-SKU/scenarios", json={
        "scenario_type": "INVALID_TYPE",
        "demand_surge_pct": 10.0,
        "demand_surge_days": 7,
        "supplier_delay_days": 0,
        "supplier_delay_sigma": 0.0,
    })
    # 422 from pydantic or 404 (SKU not found) — either is acceptable; never 500
    assert r.status_code in (404, 422)
    assert r.status_code != 500
