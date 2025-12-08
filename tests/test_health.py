"""Tests for health endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    """Test GET /health endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "machine" in data
    assert data["project"] == "FBP"


def test_root_endpoint() -> None:
    """Test root endpoint."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["project"] == "FBP"
    assert "version" in data
    assert data["status"] == "running"
