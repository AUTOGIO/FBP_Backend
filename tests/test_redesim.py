"""Tests for REDESIM endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_extract_emails() -> None:
    """Test POST /redesim/email-extract endpoint."""
    payload = {"cnpj": "12345678000190"}
    response = client.post("/redesim/email-extract", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "job_id" in data
    assert data["status"] == "queued"
    assert len(data["job_id"]) > 0


def test_extract_emails_with_filters() -> None:
    """Test POST /redesim/email-extract with filters."""
    payload = {
        "filters": {"subject": "REDESIM", "from": "sefaz.pb.gov.br"},
    }
    response = client.post("/redesim/email-extract", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "job_id" in data
    assert data["status"] == "queued"


def test_get_redesim_job_status() -> None:
    """Test GET /redesim/status/{job_id} endpoint."""
    # First create a job
    payload = {"cnpj": "12345678000190"}
    create_response = client.post("/redesim/email-extract", json=payload)
    job_id = create_response.json()["job_id"]

    # Then get status
    response = client.get(f"/redesim/status/{job_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["job_id"] == job_id
    assert data["job_type"] == "redesim_extract"
    assert data["status"] in ["queued", "running", "completed", "failed"]


def test_get_redesim_job_status_not_found() -> None:
    """Test GET /redesim/status/{job_id} with non-existent job."""
    response = client.get("/redesim/status/non-existent-job-id")

    assert response.status_code == 404
