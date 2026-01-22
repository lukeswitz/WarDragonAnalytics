"""
Pytest configuration and shared fixtures for WarDragon Analytics tests.

This module provides reusable fixtures for testing the collector service and API,
including mocked database connections, HTTP clients, and configuration data.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import sys

import pytest
import yaml

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


@pytest.fixture
def event_loop():
    """
    Create an event loop for async tests.

    This fixture ensures a fresh event loop for each test,
    preventing issues with closed loops in async tests.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_db_engine():
    """
    Mock SQLAlchemy database engine.

    Returns a MagicMock configured to simulate database operations
    without requiring an actual database connection.
    """
    engine = MagicMock()
    connection = MagicMock()

    # Mock connection context manager
    connection.__enter__ = MagicMock(return_value=connection)
    connection.__exit__ = MagicMock(return_value=False)
    connection.execute = MagicMock()
    connection.commit = MagicMock()
    connection.rollback = MagicMock()

    engine.connect = MagicMock(return_value=connection)
    engine.dispose = MagicMock()

    return engine


@pytest.fixture
def mock_database_writer(mock_db_engine):
    """
    Mock DatabaseWriter instance with pre-configured engine.

    Returns a mock that simulates database write operations
    without actually connecting to a database.
    """
    from unittest.mock import patch

    with patch('app.collector.create_engine', return_value=mock_db_engine):
        from app.collector import DatabaseWriter

        db = DatabaseWriter('postgresql://test:test@localhost/test')
        db.engine = mock_db_engine

        return db


@pytest.fixture
def mock_httpx_client():
    """
    Mock httpx.AsyncClient for HTTP requests.

    Returns an AsyncMock configured to simulate HTTP GET requests
    without making actual network calls.
    """
    client = AsyncMock()

    # Create a mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={})
    mock_response.raise_for_status = MagicMock()

    client.get = AsyncMock(return_value=mock_response)
    client.aclose = AsyncMock()

    return client


@pytest.fixture
def sample_kit_config() -> Dict:
    """
    Sample kit configuration for testing.

    Returns a dictionary representing a valid kit configuration
    as would be loaded from kits.yaml.
    """
    return {
        'id': 'test-kit-01',
        'name': 'Test Kit 01',
        'api_url': 'http://test-kit-01.local:8080',
        'location': 'Test Location',
        'enabled': True
    }


@pytest.fixture
def sample_kits_config(sample_kit_config) -> List[Dict]:
    """
    Sample configuration with multiple kits.

    Returns a list of kit configurations for testing
    multi-kit scenarios.
    """
    return [
        sample_kit_config,
        {
            'id': 'test-kit-02',
            'name': 'Test Kit 02',
            'api_url': 'http://test-kit-02.local:8080',
            'location': 'Test Location 2',
            'enabled': True
        },
        {
            'id': 'test-kit-03',
            'name': 'Test Kit 03 (Disabled)',
            'api_url': 'http://test-kit-03.local:8080',
            'location': 'Test Location 3',
            'enabled': False
        }
    ]


@pytest.fixture
def sample_drone_data() -> List[Dict]:
    """
    Sample drone detection data.

    Returns a list of drone records as would be returned
    from the /drones endpoint.
    """
    return [
        {
            'timestamp': '2024-01-20T12:00:00Z',
            'drone_id': 'DJI-12345',
            'lat': 35.1234,
            'lon': -120.5678,
            'alt': 100.5,
            'speed': 15.2,
            'heading': 180.0,
            'pilot_lat': 35.1200,
            'pilot_lon': -120.5600,
            'home_lat': 35.1200,
            'home_lon': -120.5600,
            'mac': 'AA:BB:CC:DD:EE:FF',
            'rssi': -65,
            'freq': 2437.0,
            'ua_type': 'Multirotor',
            'operator_id': 'OP-123',
            'rid_make': 'DJI',
            'rid_model': 'Mavic 3',
            'rid_source': 'wifi',
            'track_type': 'drone'
        },
        {
            'timestamp': '2024-01-20T12:00:01Z',
            'icao': 'A12345',
            'lat': 35.2234,
            'lon': -120.6678,
            'altitude': 3000.0,
            'speed': 250.0,
            'heading': 90.0,
            'track_type': 'aircraft'
        }
    ]


@pytest.fixture
def sample_signal_data() -> List[Dict]:
    """
    Sample FPV signal detection data.

    Returns a list of signal records as would be returned
    from the /signals endpoint.
    """
    return [
        {
            'timestamp': '2024-01-20T12:00:00Z',
            'freq_mhz': 5800.0,
            'power_dbm': -45.5,
            'bandwidth_mhz': 20.0,
            'lat': 35.1234,
            'lon': -120.5678,
            'alt': 50.0,
            'type': 'analog'
        },
        {
            'timestamp': '2024-01-20T12:00:01Z',
            'freq': 5745.0,
            'power': -50.2,
            'bandwidth': 20.0,
            'lat': 35.1235,
            'lon': -120.5679,
            'alt': 51.0,
            'type': 'analog'
        }
    ]


@pytest.fixture
def sample_status_data() -> Dict:
    """
    Sample system status/health data.

    Returns a dictionary as would be returned from
    the /status endpoint.
    """
    return {
        'timestamp': '2024-01-20T12:00:00Z',
        'gps': {
            'lat': 35.1234,
            'lon': -120.5678,
            'alt': 100.0
        },
        'cpu': {
            'percent': 45.2
        },
        'memory': {
            'percent': 62.8
        },
        'disk': {
            'percent': 35.5
        },
        'temps': {
            'cpu': 55.0,
            'gpu': 60.0
        },
        'uptime_hours': 24.5
    }


@pytest.fixture
def temp_kits_config(tmp_path, sample_kits_config):
    """
    Create a temporary kits.yaml configuration file.

    Args:
        tmp_path: Pytest's tmp_path fixture
        sample_kits_config: Sample kit configurations

    Returns:
        Path to the temporary configuration file
    """
    config_file = tmp_path / "kits.yaml"
    config_data = {'kits': sample_kits_config}

    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    return str(config_file)


@pytest.fixture
def mock_shutdown_event():
    """
    Mock shutdown event for testing graceful shutdown.

    Returns an asyncio.Event that can be set to trigger
    shutdown in collector loops.
    """
    return asyncio.Event()


@pytest.fixture
def mock_datetime_now():
    """
    Mock datetime.now() for consistent timestamps in tests.

    Returns a fixed datetime for predictable test results.
    """
    return datetime(2024, 1, 20, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_logger():
    """
    Mock logger to capture log messages during tests.

    Returns a MagicMock configured to simulate logging
    without actual log output.
    """
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()

    return logger


@pytest.fixture(autouse=True)
def reset_module_state():
    """
    Reset module-level state between tests.

    This fixture automatically runs for each test to ensure
    clean state, particularly for the global shutdown_event.
    """
    try:
        import app.collector as collector_module

        # Reset shutdown event
        if hasattr(collector_module, 'shutdown_event'):
            collector_module.shutdown_event.clear()

        yield

        # Cleanup after test
        if hasattr(collector_module, 'shutdown_event'):
            collector_module.shutdown_event.clear()
    except ImportError:
        # Collector module may not be importable in all environments
        yield


@pytest.fixture
def mock_sqlalchemy_create_engine(mock_db_engine):
    """
    Patch SQLAlchemy's create_engine to return a mock.

    This fixture patches the create_engine function to prevent
    actual database connections during testing.
    """
    from unittest.mock import patch

    with patch('app.collector.create_engine', return_value=mock_db_engine) as mock:
        yield mock


# ==============================================================================
# API-SPECIFIC FIXTURES
# ==============================================================================

@pytest.fixture
def sample_datetime_api():
    """Provide a consistent datetime for API testing."""
    return datetime(2026, 1, 20, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_asyncpg_connection():
    """
    Create a mock asyncpg connection with common query responses.

    Returns:
        AsyncMock: Mock connection object with fetch/fetchval methods.
    """
    conn = AsyncMock()

    # Default responses
    conn.fetchval.return_value = 1  # For health checks
    conn.fetch.return_value = []  # Default empty result

    return conn


@pytest.fixture
def mock_asyncpg_pool(mock_asyncpg_connection):
    """
    Create a mock asyncpg pool with acquire context manager.

    Args:
        mock_asyncpg_connection: The mock connection to return when acquiring.

    Returns:
        AsyncMock: Mock pool object.
    """
    pool = AsyncMock()

    # Mock the acquire context manager
    acquire_context = AsyncMock()
    acquire_context.__aenter__.return_value = mock_asyncpg_connection
    acquire_context.__aexit__.return_value = None
    pool.acquire.return_value = acquire_context

    return pool


@pytest.fixture
def api_sample_kits(sample_datetime_api):
    """
    Generate sample kit status data for API testing.

    Returns:
        List[Dict]: List of kit dictionaries with status information.
    """
    return [
        {
            "kit_id": "kit001",
            "name": "Downtown Station",
            "location": "Downtown",
            "api_url": "http://kit001.local:8080",
            "last_seen": sample_datetime_api - timedelta(seconds=10),
            "status": "online",
            "created_at": sample_datetime_api - timedelta(days=30)
        },
        {
            "kit_id": "kit002",
            "name": "Airport Monitor",
            "location": "Airport",
            "api_url": "http://kit002.local:8080",
            "last_seen": sample_datetime_api - timedelta(seconds=60),
            "status": "stale",
            "created_at": sample_datetime_api - timedelta(days=20)
        },
        {
            "kit_id": "kit003",
            "name": "Harbor Watch",
            "location": "Harbor",
            "api_url": "http://kit003.local:8080",
            "last_seen": sample_datetime_api - timedelta(hours=2),
            "status": "offline",
            "created_at": sample_datetime_api - timedelta(days=10)
        }
    ]


@pytest.fixture
def api_sample_drones(sample_datetime_api):
    """
    Generate sample drone track data for API testing.

    Returns:
        List[Dict]: List of drone track dictionaries.
    """
    return [
        {
            "time": sample_datetime_api - timedelta(minutes=5),
            "kit_id": "kit001",
            "drone_id": "drone001",
            "lat": 37.7749,
            "lon": -122.4194,
            "alt": 100.0,
            "speed": 15.5,
            "heading": 90.0,
            "pilot_lat": 37.7750,
            "pilot_lon": -122.4200,
            "home_lat": 37.7750,
            "home_lon": -122.4200,
            "mac": "AA:BB:CC:DD:EE:01",
            "rssi": -65,
            "freq": 5800.0,
            "ua_type": "Multirotor",
            "operator_id": "OP123456",
            "caa_id": None,
            "rid_make": "DJI",
            "rid_model": "Mavic 3",
            "rid_source": "BT",
            "track_type": "drone"
        },
        {
            "time": sample_datetime_api - timedelta(minutes=3),
            "kit_id": "kit002",
            "drone_id": "drone002",
            "lat": 37.7850,
            "lon": -122.4094,
            "alt": 50.0,
            "speed": 8.2,
            "heading": 180.0,
            "pilot_lat": None,
            "pilot_lon": None,
            "home_lat": None,
            "home_lon": None,
            "mac": "AA:BB:CC:DD:EE:02",
            "rssi": -70,
            "freq": 5850.0,
            "ua_type": "Helicopter",
            "operator_id": None,
            "caa_id": None,
            "rid_make": "Autel",
            "rid_model": "EVO II",
            "rid_source": "WiFi",
            "track_type": "drone"
        },
        {
            "time": sample_datetime_api - timedelta(minutes=1),
            "kit_id": "kit001",
            "drone_id": "aircraft001",
            "lat": 37.7650,
            "lon": -122.4294,
            "alt": 3000.0,
            "speed": 150.0,
            "heading": 45.0,
            "pilot_lat": None,
            "pilot_lon": None,
            "home_lat": None,
            "home_lon": None,
            "mac": None,
            "rssi": None,
            "freq": None,
            "ua_type": "Fixed Wing",
            "operator_id": None,
            "caa_id": "N12345",
            "rid_make": None,
            "rid_model": None,
            "rid_source": "ADSB",
            "track_type": "aircraft"
        }
    ]


@pytest.fixture
def api_sample_signals(sample_datetime_api):
    """
    Generate sample FPV signal detection data for API testing.

    Returns:
        List[Dict]: List of signal detection dictionaries.
    """
    return [
        {
            "time": sample_datetime_api - timedelta(minutes=2),
            "kit_id": "kit001",
            "freq_mhz": 5800.0,
            "power_dbm": -45.0,
            "bandwidth_mhz": 8.0,
            "lat": 37.7749,
            "lon": -122.4194,
            "alt": 10.0,
            "detection_type": "analog"
        },
        {
            "time": sample_datetime_api - timedelta(minutes=4),
            "kit_id": "kit002",
            "freq_mhz": 5850.0,
            "power_dbm": -50.0,
            "bandwidth_mhz": 10.0,
            "lat": 37.7850,
            "lon": -122.4094,
            "alt": 15.0,
            "detection_type": "dji"
        },
        {
            "time": sample_datetime_api - timedelta(minutes=6),
            "kit_id": "kit001",
            "freq_mhz": 5900.0,
            "power_dbm": -55.0,
            "bandwidth_mhz": 6.0,
            "lat": 37.7749,
            "lon": -122.4194,
            "alt": 10.0,
            "detection_type": "analog"
        }
    ]


@pytest.fixture
def mock_asyncpg_row():
    """
    Factory function to create mock asyncpg Record objects.

    Returns:
        Callable: Function that creates mock row with dict() and keys() methods.
    """
    def create_row(data: Dict[str, Any]):
        """Create a mock asyncpg Record object from a dictionary."""
        # Create a simple class that behaves like asyncpg.Record
        class MockRecord(dict):
            def __init__(self, data):
                super().__init__(data)
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        return MockRecord(data)

    return create_row


@pytest.fixture
def client_with_mocked_db(mock_asyncpg_pool):
    """
    Create a FastAPI TestClient with mocked database.

    This fixture patches the global db_pool and provides a test client
    that doesn't require actual database connections.

    Args:
        mock_asyncpg_pool: The mock database pool fixture.

    Yields:
        TestClient: FastAPI test client instance.
    """
    from fastapi.testclient import TestClient

    # Import after adding to sys.path
    from api import app

    with patch("api.db_pool", mock_asyncpg_pool):
        with TestClient(app) as client:
            yield client


@pytest.fixture
def mock_template_file(tmp_path):
    """
    Create a temporary template file for UI testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path: Path to the temporary template file.
    """
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    template_file = template_dir / "index.html"
    template_file.write_text("<html><body>WarDragon Analytics Dashboard</body></html>")
    return template_file
