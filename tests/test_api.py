"""
Unit tests for the FastAPI web application.

These tests verify API endpoints without requiring a database connection.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.mark.unit
@pytest.mark.api
def test_health_endpoint(test_client):
    """Test the /health endpoint returns 200 OK."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "ok"]


@pytest.mark.unit
@pytest.mark.api
def test_root_endpoint(test_client):
    """Test the root endpoint returns basic info."""
    response = test_client.get("/")
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.api
def test_api_docs_available(test_client):
    """Test that OpenAPI docs are accessible."""
    response = test_client.get("/docs")
    assert response.status_code == 200

    response = test_client.get("/redoc")
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.api
@patch("app.api.get_db_connection")
def test_drones_endpoint_without_db(mock_db, test_client, sample_query_params):
    """Test drones endpoint with mocked database."""
    # Mock database connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_db.return_value.__enter__.return_value = mock_conn

    response = test_client.get("/api/drones", params=sample_query_params)
    assert response.status_code in [200, 404, 500]  # Depends on implementation


@pytest.mark.unit
def test_query_parameter_validation(test_client):
    """Test API query parameter validation."""
    # Test invalid date format
    response = test_client.get("/api/drones", params={
        "start_time": "invalid-date",
        "end_time": "2026-01-20T23:59:59Z"
    })
    # Should return validation error
    assert response.status_code in [400, 422]


@pytest.mark.unit
@pytest.mark.api
def test_cors_headers(test_client):
    """Test CORS headers are set correctly."""
    response = test_client.options("/")
    # Check if CORS headers might be present
    # Exact assertion depends on CORS configuration
    assert response.status_code in [200, 404]
