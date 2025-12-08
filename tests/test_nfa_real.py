"""Tests for NFA real endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_nfa_job() -> None:
    """Test POST /nfa/create endpoint."""
    payload = {
        "emitente": {"cnpj": "12345678000190", "nome": "Test Emitente"},
        "destinatario": {"cnpj": "98765432000110", "nome": "Test Dest"},
    }
    response = client.post("/nfa/create", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "job_id" in data
    assert data["status"] == "queued"
    assert len(data["job_id"]) > 0


def test_create_nfa_job_missing_fields() -> None:
    """Test POST /nfa/create with missing required fields."""
    payload = {"emitente": {"cnpj": "12345678000190"}}
    response = client.post("/nfa/create", json=payload)

    assert response.status_code == 400


def test_get_nfa_job_status() -> None:
    """Test GET /nfa/status/{job_id} endpoint."""
    # First create a job
    payload = {
        "emitente": {"cnpj": "12345678000190", "nome": "Test"},
        "destinatario": {"cnpj": "98765432000110", "nome": "Test"},
    }
    create_response = client.post("/nfa/create", json=payload)
    job_id = create_response.json()["job_id"]

    # Then get status
    response = client.get(f"/nfa/status/{job_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["job_id"] == job_id
    assert data["job_type"] == "nfa_create"
    assert data["status"] in ["queued", "running", "completed", "failed"]


def test_get_nfa_job_status_not_found() -> None:
    """Test GET /nfa/status/{job_id} with non-existent job."""
    response = client.get("/nfa/status/non-existent-job-id")

    assert response.status_code == 404
