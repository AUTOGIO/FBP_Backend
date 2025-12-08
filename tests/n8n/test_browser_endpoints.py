"""Tests for n8n-compatible browser endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_html_capture_endpoint_structure() -> None:
    """Test that HTML capture endpoint returns n8n-friendly format."""
    response = client.post(
        "/api/browser/html",
        json={"url": "https://example.com", "use_cursor": False},
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

    # Check HTML-specific fields
    if data["success"]:
        assert "url" in data["data"]
        assert "html_length" in data["data"]
        assert "html" in data["data"]
        assert "truncated" in data["data"]


def test_error_response_format() -> None:
    """Test that errors are properly formatted."""
    # Test with invalid URL
    response = client.post(
        "/api/browser/html",
        json={"url": "invalid-url", "use_cursor": False},
    )

    assert response.status_code == 200
    data = response.json()

    # Should have success=false and errors array
    assert data["success"] is False
    assert len(data["errors"]) > 0
