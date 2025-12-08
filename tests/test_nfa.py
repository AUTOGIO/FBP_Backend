"""Tests for NFA endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_nfa_test_endpoint() -> None:
    """Test POST /nfa/test endpoint."""
    response = client.post("/nfa/test", json={})

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "message" in data
    assert "NFA test stub executed" in data["message"]
