"""Mandatory spec-fixture unit tests (Examples A, B, C from §6.5)."""
import math
import pytest
from stocksense_core.engine.z_factor import service_level_to_z
from stocksense_core.engine.recommendation import (
    safety_stock, reorder_point, eoq, constrained_order_qty
)


# ── z-factor table checks ────────────────────────────────────────────────────
@pytest.mark.parametrize("p,expected,tol", [
    (0.90, 1.282, 0.001),
    (0.95, 1.645, 0.001),
    (0.975, 1.960, 0.001),
    (0.99, 2.326, 0.001),
])
def test_z_factor_table(p, expected, tol):
    assert abs(service_level_to_z(p) - expected) < tol


def test_z_factor_rejects_invalid():
    with pytest.raises(ValueError):
        service_level_to_z(0.0)
    with pytest.raises(ValueError):
        service_level_to_z(1.0)


# ── Example A — ROP from given SS ────────────────────────────────────────────
def test_example_a_rop():
    """μd=10, L=5, SS=20 → ROP = 70"""
    rop = reorder_point(mu_d=10, L=5, ss=20)
    assert rop == 70.0


# ── Example B — computed SS and ROP ──────────────────────────────────────────
def test_example_b_safety_stock():
    """μd=10, σd=4, L=5, z=1.645, σL=0 → SS = ceil(14.71) = 15"""
    z = service_level_to_z(0.95)
    ss = safety_stock(z=z, sigma_d=4, L=5, mu_d=10, sigma_L=0)
    assert ss == 15


def test_example_b_rop():
    """Example B → ROP = 50 + 15 = 65"""
    z = service_level_to_z(0.95)
    ss = safety_stock(z=z, sigma_d=4, L=5, mu_d=10, sigma_L=0)
    rop = reorder_point(mu_d=10, L=5, ss=ss)
    assert rop == 65


# ── Example C — EOQ ──────────────────────────────────────────────────────────
def test_example_c_eoq():
    """D=3650, S=50, H=2 → EOQ = ceil(427.2) = 428"""
    raw = eoq(D_annual=3650, S=50, H=2)
    qty = constrained_order_qty(raw, moq=1, pack_size=1, max_storage=None)
    assert qty == 428


# ── Edge cases §6.6 ──────────────────────────────────────────────────────────
def test_zero_sigma_gives_zero_ss():
    ss = safety_stock(z=1.645, sigma_d=0, L=5, mu_d=10, sigma_L=0)
    assert ss == 0


def test_eoq_rejects_zero_holding_cost():
    with pytest.raises(ValueError):
        eoq(D_annual=1000, S=50, H=0)


def test_eoq_rejects_zero_order_cost():
    with pytest.raises(ValueError):
        eoq(D_annual=1000, S=0, H=2)
