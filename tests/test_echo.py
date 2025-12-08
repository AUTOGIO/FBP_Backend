"""Tests for echo endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_echo_endpoint() -> None:
    """Test POST /echo endpoint."""
    response = client.post("/echo", json={"message": "hello"})

    assert response.status_code == 200
    data = response.json()

    assert data["echo"] == "hello"


def test_echo_empty_message() -> None:
    """Test POST /echo with empty message."""
    response = client.post("/echo", json={"message": ""})

    assert response.status_code == 200
    data = response.json()

    assert data["echo"] == ""
