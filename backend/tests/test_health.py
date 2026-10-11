"""Tests for the health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_version_format(client: TestClient) -> None:
    response = client.get("/api/health")
    version = response.json()["version"]
    parts = version.split(".")
    assert len(parts) == 3, f"Expected semver, got: {version}"
