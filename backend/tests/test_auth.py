"""
Auth endpoint tests — register, login, bad creds, /me.
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

REGISTER_PAYLOAD = {
    "email": "testuser@stocksense.io",
    "password": "SecurePass123!",
    "full_name": "Test User",
}


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_new_user():
    r = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    # 201 on first call, 400 on re-run (already exists — both are correct)
    assert r.status_code in (201, 400)
    if r.status_code == 201:
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == REGISTER_PAYLOAD["email"].lower()


def test_register_duplicate_email():
    # Ensure user exists first
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 400


def test_register_missing_email():
    r = client.post("/api/auth/register", json={"password": "abc", "full_name": "X"})
    assert r.status_code == 422


def test_register_missing_password():
    r = client.post("/api/auth/register", json={"email": "x@x.com", "full_name": "X"})
    assert r.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_valid_credentials():
    # Ensure user exists
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": "WrongPassword!",
    })
    assert r.status_code == 401


def test_login_nonexistent_email():
    r = client.post("/api/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "whatever",
    })
    assert r.status_code == 401


def test_login_email_case_insensitive():
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/auth/login", json={
        "email": REGISTER_PAYLOAD["email"].upper(),
        "password": REGISTER_PAYLOAD["password"],
    })
    assert r.status_code == 200


# ── /me (authenticated) ───────────────────────────────────────────────────────

def _get_token() -> str:
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/api/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    return r.json()["access_token"]


def test_me_with_valid_token():
    token = _get_token()
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == REGISTER_PAYLOAD["email"].lower()


def test_me_without_token():
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token():
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer totally.invalid.token"})
    assert r.status_code == 401
