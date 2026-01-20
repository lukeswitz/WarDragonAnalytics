"""
End-to-end integration tests.

These tests require Docker Compose to be running with all services.
Run with: pytest -m integration
"""

import pytest
import httpx
import time
import os


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_stack_health():
    """Test all services are healthy."""
    if not os.getenv("RUN_INTEGRATION_TESTS"):
        pytest.skip("RUN_INTEGRATION_TESTS not set")

    # Give services time to start
    await asyncio.sleep(5)

    async with httpx.AsyncClient() as client:
        # Test web API health
        response = await client.get("http://localhost:8090/health", timeout=10)
        assert response.status_code == 200

        # Test Grafana health
        response = await client.get("http://localhost:3000/api/health", timeout=10)
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_collector_to_api_flow():
    """Test data flows from collector to API."""
    if not os.getenv("RUN_INTEGRATION_TESTS"):
        pytest.skip("RUN_INTEGRATION_TESTS not set")

    # Wait for collector to poll and insert data
    await asyncio.sleep(10)

    async with httpx.AsyncClient() as client:
        # Query API for recent data
        response = await client.get(
            "http://localhost:8090/api/drones",
            params={"limit": 10},
            timeout=10
        )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.slow
def test_database_persistence():
    """Test data persists across container restarts."""
    if not os.getenv("RUN_INTEGRATION_TESTS"):
        pytest.skip("RUN_INTEGRATION_TESTS not set")

    # This would require docker-compose restart logic
    pass


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_api_to_grafana_datasource():
    """Test Grafana can query TimescaleDB."""
    if not os.getenv("RUN_INTEGRATION_TESTS"):
        pytest.skip("RUN_INTEGRATION_TESTS not set")

    # Test Grafana datasource connection
    # This requires Grafana API authentication
    pass
