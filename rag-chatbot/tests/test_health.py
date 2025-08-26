import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_healthz():
    """Test health endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_without_auth():
    """Test health endpoint doesn't require auth."""
    response = client.get("/healthz")
    assert response.status_code == 200


def test_config_without_auth():
    """Test config endpoint requires auth."""
    response = client.get("/config")
    assert response.status_code == 401


def test_config_with_auth():
    """Test config endpoint with auth."""
    response = client.get("/config", headers={"x-api-key": "changeme"})
    assert response.status_code == 200
    data = response.json()
    assert "app_env" in data
    assert "vector_store" in data 