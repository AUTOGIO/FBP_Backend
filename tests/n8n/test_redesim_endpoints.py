"""Tests for n8n-compatible REDESIM endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_extract_endpoint_structure() -> None:
    """Test that extract endpoint returns n8n-friendly format."""
    response = client.post(
        "/api/redesim/extract",
        json={"url": "https://atf.sefaz.pb.gov.br/"},
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


def test_create_draft_endpoint_structure() -> None:
    """Test that create draft endpoint returns n8n-friendly format."""
    response = client.post(
        "/api/redesim/email/create-draft",
        json={
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "Test Body",
        },
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


def test_send_email_endpoint_structure() -> None:
    """Test that send email endpoint returns n8n-friendly format."""
    response = client.post(
        "/api/redesim/email/send",
        json={"draft_id": "test_draft_id"},
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


def test_error_response_format() -> None:
    """Test that errors are properly formatted."""
    # Test with invalid request
    response = client.post(
        "/api/redesim/email/create-draft",
        json={},  # Missing required fields
    )

    assert response.status_code == 422  # Validation error
