"""Tests for Intelligence Control Plane Admin API endpoints and RBAC."""

import json
import pytest
from app import app
from engine.security.auth import create_admin_token, AdminRole, Role


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def super_admin_headers():
    token = create_admin_token(user_id="super_admin_1", admin_role=AdminRole.SUPER_ADMIN.value)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def ml_engineer_headers():
    token = create_admin_token(user_id="ml_eng_1", admin_role=AdminRole.ML_ENGINEER.value)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def clinical_reviewer_headers():
    token = create_admin_token(user_id="dr_reviewer_1", admin_role=AdminRole.CLINICAL_REVIEWER.value)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_admin_login_validation(client):
    # Missing/invalid role
    res = client.post("/api/admin/auth/login", json={"role": "INVALID_ROLE", "secret": "xyz"})
    assert res.status_code == 400

    # In demo mode, admin login succeeds
    res_valid = client.post("/api/admin/auth/login", json={"role": "SUPER_ADMIN", "secret": "drishti-admin-secret-2026"})
    assert res_valid.status_code == 200
    data = res_valid.get_json()
    assert data["success"] is True
    assert "token" in data


def test_protected_dashboard_requires_auth(client):
    # No auth header -> 401
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 401

    # Invalid token -> 401
    res_bad = client.get("/api/admin/dashboard", headers={"Authorization": "Bearer invalid.token.xyz"})
    assert res_bad.status_code == 401


def test_dashboard_with_admin_token(client, super_admin_headers):
    res = client.get("/api/admin/dashboard", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "metrics" in data


def test_active_learning_queue_endpoint(client, ml_engineer_headers):
    res = client.get("/api/admin/active-learning?limit=10", headers=ml_engineer_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "candidates" in data


def test_datasets_endpoint(client, ml_engineer_headers):
    res = client.get("/api/admin/datasets", headers=ml_engineer_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "datasets" in data


def test_models_endpoint(client, super_admin_headers):
    res = client.get("/api/admin/models", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "models" in data


def test_drift_endpoint(client, ml_engineer_headers):
    res = client.get("/api/admin/drift", headers=ml_engineer_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "clinical_drift" in data


def test_system_health_endpoint(client, super_admin_headers):
    res = client.get("/api/admin/system", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["plane"] == "INTELLIGENCE_CONTROL_PLANE"
