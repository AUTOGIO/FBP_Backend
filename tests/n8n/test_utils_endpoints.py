"""Tests for n8n-compatible utility endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cep_validation_endpoint_structure() -> None:
    """Test that CEP validation endpoint returns n8n-friendly format."""
    response = client.post(
        "/api/utils/cep",
        json={"cep": "05424020", "enrich": False},
    )

    assert response.status_code == 200
    data = response.json()

    # Check n8n-friendly structure
    assert "success" in data
    assert "data" in data
    assert "errors" in data
    assert isinstance(data["success"], bool)
    assert isinstance(data["data"], dict)
    assert isinstance(data["errors"], list)


def test_cep_batch_endpoint_structure() -> None:
    """Test that batch CEP validation endpoint returns n8n-friendly format."""
    response = client.post(
        "/api/utils/cep/batch",
        json={"ceps": ["05424020", "01310100"]},
    )

    assert response.status_code == 200
    data = response.json()

    # Check n8n-friendly structure
    assert "success" in data
    assert "data" in data
    assert "errors" in data
    assert isinstance(data["success"], bool)
    assert isinstance(data["data"], dict)
    assert isinstance(data["errors"], list)

    # Check batch-specific fields
    assert "total" in data["data"]
    assert "validated" in data["data"]
    assert "valid_count" in data["data"]
    assert "invalid_count" in data["data"]


def test_invalid_cep_handling() -> None:
    """Test that invalid CEPs return proper error format."""
    response = client.post(
        "/api/utils/cep",
        json={"cep": "invalid", "enrich": False},
    )

    assert response.status_code == 200
    data = response.json()

    # Should have success=false and errors array
    assert data["success"] is False
    assert len(data["errors"]) > 0
