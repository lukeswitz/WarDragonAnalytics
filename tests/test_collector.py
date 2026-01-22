"""
Comprehensive unit tests for WarDragon Analytics collector service.

This test module provides full coverage for:
- KitHealth tracking (online/offline/stale detection)
- DatabaseWriter operations (insert_drones, insert_signals, insert_health)
- KitCollector polling logic (fetch_json, retry logic)
- CollectorService orchestration (config loading, graceful shutdown)
- Signal handlers (SIGTERM/SIGINT)
- Error handling and retry logic
- Exponential backoff for offline kits

All tests use mocks to avoid requiring actual database or network connections.
Target coverage: 80%+

NOTE: These tests require the collector module which has heavy dependencies.
Marked as 'collector' for selective running.
"""

import pytest

# Mark all tests in this module as collector tests
pytestmark = pytest.mark.collector

import asyncio
import signal
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
import httpx
import yaml
from sqlalchemy.exc import SQLAlchemyError

# Import collector module components
import app.collector as collector_module
from app.collector import (
    KitHealth,
    DatabaseWriter,
    KitCollector,
    CollectorService,
    signal_handler,
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    STALE_THRESHOLD,
    MAX_RETRIES,
)


# ==============================================================================
# KitHealth Tests
# ==============================================================================


class TestKitHealth:
    """Test suite for KitHealth class - tracks kit status and backoff logic."""

    def test_init(self):
        """Test KitHealth initialization with default values."""
        health = KitHealth('test-kit-01')

        assert health.kit_id == 'test-kit-01'
        assert health.status == 'unknown'
        assert health.last_seen is None
        assert health.last_error is None
        assert health.consecutive_failures == 0
        assert health.backoff_delay == INITIAL_BACKOFF
        assert health.total_requests == 0
        assert health.successful_requests == 0
        assert health.failed_requests == 0

    def test_mark_success(self):
        """Test marking a successful poll resets failure counters."""
        health = KitHealth('test-kit-01')
        health.consecutive_failures = 3
        health.backoff_delay = 40.0
        health.last_error = "Previous error"

        health.mark_success()

        assert health.status == 'online'
        assert health.last_seen is not None
        assert isinstance(health.last_seen, datetime)
        assert health.consecutive_failures == 0
        assert health.backoff_delay == INITIAL_BACKOFF
        assert health.total_requests == 1
        assert health.successful_requests == 1
        assert health.failed_requests == 0
        assert health.last_error is None

    def test_mark_failure(self):
        """Test marking a failed poll increments counters and calculates backoff."""
        health = KitHealth('test-kit-01')

        health.mark_failure("Connection timeout")

        assert health.status == 'offline'
        assert health.last_error == "Connection timeout"
        assert health.consecutive_failures == 1
        assert health.total_requests == 1
        assert health.successful_requests == 0
        assert health.failed_requests == 1
        # First failure: INITIAL_BACKOFF * 2^1 = 5 * 2 = 10
        assert health.backoff_delay == INITIAL_BACKOFF * 2

    def test_mark_failure_exponential_backoff(self):
        """Test exponential backoff calculation increases with consecutive failures."""
        health = KitHealth('test-kit-01')

        # Simulate multiple failures
        for i in range(5):
            health.mark_failure(f"Error {i}")

        # After 5 failures: 5 * 2^5 = 5 * 32 = 160 seconds
        expected_backoff = min(INITIAL_BACKOFF * (2 ** 5), MAX_BACKOFF)
        assert health.backoff_delay == expected_backoff
        assert health.consecutive_failures == 5
        assert health.failed_requests == 5

    def test_mark_failure_max_backoff(self):
        """Test backoff delay caps at MAX_BACKOFF."""
        health = KitHealth('test-kit-01')

        # Simulate many failures to exceed max
        for i in range(20):
            health.mark_failure(f"Error {i}")

        assert health.backoff_delay == MAX_BACKOFF
        assert health.consecutive_failures == 20

    def test_mark_stale_recent_data(self):
        """Test that recently seen kit is not marked stale."""
        health = KitHealth('test-kit-01')
        health.mark_success()  # Sets last_seen to now

        health.mark_stale()

        # Should still be online, not stale
        assert health.status == 'online'

    def test_mark_stale_old_data(self):
        """Test that kit with old data is marked stale."""
        health = KitHealth('test-kit-01')
        # Set last_seen to old timestamp
        health.last_seen = datetime.now(timezone.utc) - timedelta(seconds=STALE_THRESHOLD + 10)
        health.status = 'online'

        health.mark_stale()

        assert health.status == 'stale'

    def test_mark_stale_no_data(self):
        """Test mark_stale handles None last_seen gracefully."""
        health = KitHealth('test-kit-01')
        health.last_seen = None

        # Should not raise exception
        health.mark_stale()

        # Status should remain unknown
        assert health.status == 'unknown'

    def test_get_next_poll_delay_online(self):
        """Test poll delay is 0 for online kits."""
        health = KitHealth('test-kit-01')
        health.mark_success()

        delay = health.get_next_poll_delay()

        assert delay == 0.0

    def test_get_next_poll_delay_offline(self):
        """Test poll delay uses backoff for offline kits."""
        health = KitHealth('test-kit-01')
        health.mark_failure("Error")

        delay = health.get_next_poll_delay()

        assert delay == health.backoff_delay
        assert delay > 0

    def test_get_stats(self):
        """Test get_stats returns complete health statistics."""
        health = KitHealth('test-kit-01')

        # Generate some activity
        health.mark_success()
        health.mark_success()
        health.mark_failure("Test error")

        stats = health.get_stats()

        assert stats['status'] == 'offline'
        assert stats['last_seen'] is not None
        assert stats['consecutive_failures'] == 1
        assert stats['total_requests'] == 3
        assert stats['successful_requests'] == 2
        assert stats['failed_requests'] == 1
        assert '66.7%' in stats['success_rate']  # 2/3 = 66.7%
        assert 'next_retry_delay' in stats
        assert stats['last_error'] == "Test error"

    def test_get_stats_no_requests(self):
        """Test get_stats handles zero requests without division error."""
        health = KitHealth('test-kit-01')

        stats = health.get_stats()

        assert stats['success_rate'] == '0.0%'
        assert stats['total_requests'] == 0


# ==============================================================================
# DatabaseWriter Tests
# ==============================================================================


class TestDatabaseWriter:
    """Test suite for DatabaseWriter class - handles database operations."""

    def test_init(self, mock_sqlalchemy_create_engine, mock_db_engine):
        """Test DatabaseWriter initialization creates engine."""
        db_url = 'postgresql://test:test@localhost/test'

        db = DatabaseWriter(db_url)

        assert db.database_url == db_url
        assert db.engine is not None
        mock_sqlalchemy_create_engine.assert_called_once()

    def test_init_failure(self):
        """Test DatabaseWriter init handles engine creation failure."""
        with patch('app.collector.create_engine', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                DatabaseWriter('postgresql://invalid')

    def test_test_connection_success(self, mock_database_writer):
        """Test test_connection returns True on successful connection."""
        result = mock_database_writer.test_connection()

        assert result is True

    def test_test_connection_failure(self, mock_database_writer):
        """Test test_connection returns False on connection error."""
        mock_database_writer.engine.connect.side_effect = Exception("Connection error")

        result = mock_database_writer.test_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_insert_drones_success(self, mock_database_writer, sample_drone_data):
        """Test successful insertion of drone records."""
        inserted = await mock_database_writer.insert_drones('test-kit-01', sample_drone_data)

        assert inserted == len(sample_drone_data)
        # Verify execute was called for each drone
        assert mock_database_writer.engine.connect().execute.call_count == len(sample_drone_data)

    @pytest.mark.asyncio
    async def test_insert_drones_empty_list(self, mock_database_writer):
        """Test insert_drones handles empty list gracefully."""
        inserted = await mock_database_writer.insert_drones('test-kit-01', [])

        assert inserted == 0

    @pytest.mark.asyncio
    async def test_insert_drones_partial_failure(self, mock_database_writer, sample_drone_data):
        """Test insert_drones continues on individual record failure."""
        # Make first execution fail, second succeed
        mock_conn = mock_database_writer.engine.connect()
        mock_conn.execute.side_effect = [
            SQLAlchemyError("Insert failed"),
            None,  # Second insert succeeds
        ]

        inserted = await mock_database_writer.insert_drones('test-kit-01', sample_drone_data)

        # Should have attempted both, succeeded with 1
        assert inserted == 1
        assert mock_conn.execute.call_count == 2
        assert mock_conn.rollback.call_count == 1

    @pytest.mark.asyncio
    async def test_insert_drones_with_aircraft(self, mock_database_writer):
        """Test insert_drones correctly identifies aircraft by ICAO field."""
        aircraft_data = [{
            'timestamp': '2024-01-20T12:00:00Z',
            'icao': 'A12345',
            'lat': 35.1234,
            'lon': -120.5678,
            'altitude': 3000.0,
        }]

        inserted = await mock_database_writer.insert_drones('test-kit-01', aircraft_data)

        assert inserted == 1
        # Verify track_type was set to 'aircraft'
        call_args = mock_database_writer.engine.connect().execute.call_args
        assert call_args[0][1]['track_type'] == 'aircraft'

    @pytest.mark.asyncio
    async def test_insert_signals_success(self, mock_database_writer, sample_signal_data):
        """Test successful insertion of signal records."""
        inserted = await mock_database_writer.insert_signals('test-kit-01', sample_signal_data)

        assert inserted == len(sample_signal_data)
        assert mock_database_writer.engine.connect().execute.call_count == len(sample_signal_data)

    @pytest.mark.asyncio
    async def test_insert_signals_empty_list(self, mock_database_writer):
        """Test insert_signals handles empty list gracefully."""
        inserted = await mock_database_writer.insert_signals('test-kit-01', [])

        assert inserted == 0

    @pytest.mark.asyncio
    async def test_insert_signals_fpv_detection(self, mock_database_writer):
        """Test insert_signals correctly identifies FPV signals by frequency."""
        fpv_signal = [{
            'timestamp': '2024-01-20T12:00:00Z',
            'freq_mhz': 5800.0,  # FPV frequency
            'power_dbm': -50.0,
            'type': 'analog',
        }]

        inserted = await mock_database_writer.insert_signals('test-kit-01', fpv_signal)

        assert inserted == 1
        # Verify detection_type was set
        call_args = mock_database_writer.engine.connect().execute.call_args
        assert call_args[0][1]['detection_type'] == 'analog'

    @pytest.mark.asyncio
    async def test_insert_health_success(self, mock_database_writer, sample_status_data):
        """Test successful insertion of health/status record."""
        result = await mock_database_writer.insert_health('test-kit-01', sample_status_data)

        assert result is True
        mock_database_writer.engine.connect().execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_health_failure(self, mock_database_writer, sample_status_data):
        """Test insert_health handles database errors gracefully."""
        mock_database_writer.engine.connect().execute.side_effect = Exception("DB error")

        result = await mock_database_writer.insert_health('test-kit-01', sample_status_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_kit_status_success(self, mock_database_writer):
        """Test successful kit status update."""
        now = datetime.now(timezone.utc)

        await mock_database_writer.update_kit_status('test-kit-01', 'online', now)

        mock_database_writer.engine.connect().execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_kit_status_failure(self, mock_database_writer):
        """Test update_kit_status handles errors gracefully."""
        mock_database_writer.engine.connect().execute.side_effect = Exception("DB error")
        now = datetime.now(timezone.utc)

        # Should not raise exception
        await mock_database_writer.update_kit_status('test-kit-01', 'online', now)

    def test_parse_timestamp_datetime(self, mock_database_writer):
        """Test _parse_timestamp handles datetime objects."""
        dt = datetime(2024, 1, 20, 12, 0, 0, tzinfo=timezone.utc)

        result = mock_database_writer._parse_timestamp(dt)

        assert result == dt

    def test_parse_timestamp_iso_string(self, mock_database_writer):
        """Test _parse_timestamp parses ISO format strings."""
        iso_string = '2024-01-20T12:00:00Z'

        result = mock_database_writer._parse_timestamp(iso_string)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 20

    def test_parse_timestamp_invalid(self, mock_database_writer):
        """Test _parse_timestamp returns current time for invalid input."""
        result = mock_database_writer._parse_timestamp("invalid")

        assert isinstance(result, datetime)
        # Should be close to now
        assert (datetime.now(timezone.utc) - result).total_seconds() < 1

    def test_safe_float_valid(self, mock_database_writer):
        """Test _safe_float converts valid numbers."""
        assert mock_database_writer._safe_float(123.45) == 123.45
        assert mock_database_writer._safe_float("67.89") == 67.89
        assert mock_database_writer._safe_float(100) == 100.0

    def test_safe_float_invalid(self, mock_database_writer):
        """Test _safe_float returns None for invalid input."""
        assert mock_database_writer._safe_float(None) is None
        assert mock_database_writer._safe_float("") is None
        assert mock_database_writer._safe_float("invalid") is None

    def test_safe_int_valid(self, mock_database_writer):
        """Test _safe_int converts valid integers."""
        assert mock_database_writer._safe_int(123) == 123
        assert mock_database_writer._safe_int("456") == 456
        assert mock_database_writer._safe_int(78.9) == 78

    def test_safe_int_invalid(self, mock_database_writer):
        """Test _safe_int returns None for invalid input."""
        assert mock_database_writer._safe_int(None) is None
        assert mock_database_writer._safe_int("") is None
        assert mock_database_writer._safe_int("invalid") is None

    def test_close(self, mock_database_writer):
        """Test close disposes of database engine."""
        mock_database_writer.close()

        mock_database_writer.engine.dispose.assert_called_once()


# ==============================================================================
# KitCollector Tests
# ==============================================================================


class TestKitCollector:
    """Test suite for KitCollector class - polls individual kits."""

    def test_init(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test KitCollector initialization."""
        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)

        assert collector.kit_id == 'test-kit-01'
        assert collector.name == 'Test Kit 01'
        assert collector.api_url == 'http://test-kit-01.local:8080'
        assert collector.location == 'Test Location'
        assert collector.enabled is True
        assert isinstance(collector.health, KitHealth)

    @pytest.mark.asyncio
    async def test_fetch_json_success(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test successful JSON fetch from kit endpoint."""
        expected_data = {'drones': [{'id': 'test'}]}
        mock_httpx_client.get.return_value.json.return_value = expected_data

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.fetch_json('/drones')

        assert result == expected_data
        mock_httpx_client.get.assert_called_once_with(
            'http://test-kit-01.local:8080/drones',
            timeout=10
        )

    @pytest.mark.asyncio
    async def test_fetch_json_timeout(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test fetch_json handles timeout with retry."""
        mock_httpx_client.get.side_effect = httpx.TimeoutException("Timeout")

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.fetch_json('/drones')

        assert result is None
        # Should retry MAX_RETRIES + 1 times
        assert mock_httpx_client.get.call_count == MAX_RETRIES + 1

    @pytest.mark.asyncio
    async def test_fetch_json_http_error(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test fetch_json handles HTTP errors."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        )
        mock_httpx_client.get.return_value = mock_response

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.fetch_json('/drones')

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_json_request_error(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test fetch_json handles request errors."""
        mock_httpx_client.get.side_effect = httpx.RequestError("Connection refused")

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.fetch_json('/drones')

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_json_retry_success(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test fetch_json succeeds on retry after initial failure."""
        expected_data = {'drones': []}

        # First call times out, second succeeds
        mock_httpx_client.get.side_effect = [
            httpx.TimeoutException("Timeout"),
            AsyncMock(json=AsyncMock(return_value=expected_data), raise_for_status=Mock())
        ]

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.fetch_json('/drones')

        assert result == expected_data
        assert mock_httpx_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_poll_drones_success(self, sample_kit_config, mock_database_writer, mock_httpx_client, sample_drone_data):
        """Test successful drone polling."""
        mock_httpx_client.get.return_value.json.return_value = {'drones': sample_drone_data}
        mock_database_writer.insert_drones = AsyncMock(return_value=len(sample_drone_data))

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.poll_drones()

        assert result is True
        mock_database_writer.insert_drones.assert_called_once_with('test-kit-01', sample_drone_data)

    @pytest.mark.asyncio
    async def test_poll_drones_list_format(self, sample_kit_config, mock_database_writer, mock_httpx_client, sample_drone_data):
        """Test poll_drones handles direct list response format."""
        mock_httpx_client.get.return_value.json.return_value = sample_drone_data
        mock_database_writer.insert_drones = AsyncMock(return_value=len(sample_drone_data))

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.poll_drones()

        assert result is True
        mock_database_writer.insert_drones.assert_called_once_with('test-kit-01', sample_drone_data)

    @pytest.mark.asyncio
    async def test_poll_drones_failure(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test poll_drones handles fetch failure."""
        mock_httpx_client.get.side_effect = httpx.RequestError("Connection error")

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.poll_drones()

        assert result is False

    @pytest.mark.asyncio
    async def test_poll_signals_success(self, sample_kit_config, mock_database_writer, mock_httpx_client, sample_signal_data):
        """Test successful signal polling."""
        mock_httpx_client.get.return_value.json.return_value = {'signals': sample_signal_data}
        mock_database_writer.insert_signals = AsyncMock(return_value=len(sample_signal_data))

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.poll_signals()

        assert result is True
        mock_database_writer.insert_signals.assert_called_once_with('test-kit-01', sample_signal_data)

    @pytest.mark.asyncio
    async def test_poll_status_success(self, sample_kit_config, mock_database_writer, mock_httpx_client, sample_status_data):
        """Test successful status polling."""
        mock_httpx_client.get.return_value.json.return_value = sample_status_data
        mock_database_writer.insert_health = AsyncMock(return_value=True)

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.poll_status()

        assert result is True
        mock_database_writer.insert_health.assert_called_once_with('test-kit-01', sample_status_data)

    @pytest.mark.asyncio
    async def test_poll_all_endpoints_success(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test poll_all_endpoints polls drones and signals concurrently."""
        mock_httpx_client.get.return_value.json.return_value = {}
        mock_database_writer.insert_drones = AsyncMock(return_value=0)
        mock_database_writer.insert_signals = AsyncMock(return_value=0)

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.poll_all_endpoints()

        assert result is True

    @pytest.mark.asyncio
    async def test_poll_all_endpoints_partial_success(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test poll_all_endpoints succeeds if at least one endpoint works."""
        call_count = 0

        async def side_effect_func(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (drones) fails
                raise httpx.RequestError("Connection error")
            else:
                # Second call (signals) succeeds
                mock_resp = AsyncMock()
                mock_resp.json.return_value = {}
                mock_resp.raise_for_status = Mock()
                return mock_resp

        mock_httpx_client.get.side_effect = side_effect_func
        mock_database_writer.insert_signals = AsyncMock(return_value=0)

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)
        result = await collector.poll_all_endpoints()

        assert result is True

    @pytest.mark.asyncio
    async def test_run_disabled_kit(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test run loop skips disabled kits."""
        sample_kit_config['enabled'] = False
        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)

        # Set shutdown event after short delay to stop loop
        async def trigger_shutdown():
            await asyncio.sleep(0.1)
            collector_module.shutdown_event.set()

        shutdown_task = asyncio.create_task(trigger_shutdown())

        await collector.run()
        await shutdown_task

        # Should not have called any endpoints
        mock_httpx_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_success_polling(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test run loop performs successful polling cycle."""
        mock_httpx_client.get.return_value.json.return_value = {}
        mock_database_writer.insert_drones = AsyncMock(return_value=0)
        mock_database_writer.insert_signals = AsyncMock(return_value=0)
        mock_database_writer.update_kit_status = AsyncMock()

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)

        # Set shutdown event after allowing one poll cycle
        async def trigger_shutdown():
            await asyncio.sleep(0.2)
            collector_module.shutdown_event.set()

        shutdown_task = asyncio.create_task(trigger_shutdown())

        await collector.run()
        await shutdown_task

        # Should have polled endpoints
        assert mock_httpx_client.get.call_count >= 2  # At least drones and signals

    @pytest.mark.asyncio
    async def test_run_failure_backoff(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test run loop applies backoff on failure."""
        mock_httpx_client.get.side_effect = httpx.RequestError("Connection error")
        mock_database_writer.update_kit_status = AsyncMock()

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)

        # Set shutdown event after short delay
        async def trigger_shutdown():
            await asyncio.sleep(0.2)
            collector_module.shutdown_event.set()

        shutdown_task = asyncio.create_task(trigger_shutdown())

        await collector.run()
        await shutdown_task

        # Should have marked failure
        assert collector.health.status == 'offline'
        assert collector.health.consecutive_failures > 0


# ==============================================================================
# CollectorService Tests
# ==============================================================================


class TestCollectorService:
    """Test suite for CollectorService - orchestrates all collectors."""

    def test_init(self):
        """Test CollectorService initialization."""
        service = CollectorService('/config/kits.yaml')

        assert service.config_path == '/config/kits.yaml'
        assert service.kits == []
        assert service.db is None
        assert service.client is None
        assert service.tasks == []
        assert service.health_stats == {}

    def test_load_config_success(self, temp_kits_config):
        """Test successful configuration loading."""
        service = CollectorService(temp_kits_config)

        kits = service.load_config()

        assert len(kits) == 3
        assert kits[0]['id'] == 'test-kit-01'
        assert kits[1]['id'] == 'test-kit-02'
        assert kits[2]['id'] == 'test-kit-03'

    def test_load_config_file_not_found(self):
        """Test load_config raises error for missing file."""
        service = CollectorService('/nonexistent/kits.yaml')

        with pytest.raises(FileNotFoundError):
            service.load_config()

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test load_config handles invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")

        service = CollectorService(str(config_file))

        with pytest.raises(yaml.YAMLError):
            service.load_config()

    def test_load_config_missing_id(self, tmp_path):
        """Test load_config validates required fields."""
        config_file = tmp_path / "kits.yaml"
        config_data = {
            'kits': [
                {'api_url': 'http://test.local'}  # Missing 'id'
            ]
        }
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        service = CollectorService(str(config_file))

        with pytest.raises(ValueError, match="missing 'id' field"):
            service.load_config()

    def test_load_config_missing_api_url(self, tmp_path):
        """Test load_config validates api_url field."""
        config_file = tmp_path / "kits.yaml"
        config_data = {
            'kits': [
                {'id': 'test-kit'}  # Missing 'api_url'
            ]
        }
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        service = CollectorService(str(config_file))

        with pytest.raises(ValueError, match="missing 'api_url' field"):
            service.load_config()

    @pytest.mark.asyncio
    async def test_start_db_connection_failure(self, temp_kits_config, mock_sqlalchemy_create_engine):
        """Test start exits if database connection fails."""
        service = CollectorService(temp_kits_config)

        with patch.object(DatabaseWriter, 'test_connection', return_value=False):
            with pytest.raises(SystemExit):
                await service.start()

    @pytest.mark.asyncio
    async def test_start_creates_collectors(self, temp_kits_config, mock_sqlalchemy_create_engine, mock_db_engine):
        """Test start creates collectors for enabled kits."""
        service = CollectorService(temp_kits_config)

        # Mock successful DB connection
        with patch.object(DatabaseWriter, 'test_connection', return_value=True):
            # Set shutdown immediately to exit start loop
            collector_module.shutdown_event.set()

            await service.start()

            # Should have created 2 collectors (2 enabled kits)
            assert len(service.kits) == 2
            assert len(service.health_stats) == 2

    @pytest.mark.asyncio
    async def test_monitor_health(self, temp_kits_config):
        """Test monitor_health logs kit statistics."""
        service = CollectorService(temp_kits_config)

        # Add mock health stats
        mock_health = KitHealth('test-kit-01')
        mock_health.mark_success()
        service.health_stats['test-kit-01'] = mock_health

        # Run monitor for short duration
        async def trigger_shutdown():
            await asyncio.sleep(0.1)
            collector_module.shutdown_event.set()

        shutdown_task = asyncio.create_task(trigger_shutdown())
        monitor_task = asyncio.create_task(service.monitor_health())

        await shutdown_task
        await monitor_task

        # Should have logged stats (verify no exceptions)
        assert True

    @pytest.mark.asyncio
    async def test_shutdown(self, temp_kits_config, mock_sqlalchemy_create_engine):
        """Test graceful shutdown closes resources."""
        service = CollectorService(temp_kits_config)
        service.client = AsyncMock()
        service.db = MagicMock()
        service.db.close = MagicMock()

        await service.shutdown()

        service.client.aclose.assert_called_once()
        service.db.close.assert_called_once()
        assert collector_module.shutdown_event.is_set()


# ==============================================================================
# Signal Handler Tests
# ==============================================================================


class TestSignalHandlers:
    """Test suite for signal handlers - SIGTERM/SIGINT handling."""

    def test_signal_handler_sigterm(self):
        """Test signal handler responds to SIGTERM."""
        # Clear shutdown event first
        collector_module.shutdown_event.clear()

        signal_handler(signal.SIGTERM, None)

        assert collector_module.shutdown_event.is_set()

    def test_signal_handler_sigint(self):
        """Test signal handler responds to SIGINT."""
        # Clear shutdown event first
        collector_module.shutdown_event.clear()

        signal_handler(signal.SIGINT, None)

        assert collector_module.shutdown_event.is_set()


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestIntegration:
    """Integration tests for end-to-end scenarios."""

    @pytest.mark.asyncio
    async def test_full_polling_cycle(self, sample_kit_config, mock_database_writer, mock_httpx_client,
                                       sample_drone_data, sample_signal_data, sample_status_data):
        """Test complete polling cycle with all endpoints."""
        # Setup mock responses
        responses = {
            '/drones': {'drones': sample_drone_data},
            '/signals': {'signals': sample_signal_data},
            '/status': sample_status_data,
        }

        async def mock_get(url, **kwargs):
            endpoint = url.split('/')[-1]
            mock_resp = AsyncMock()
            mock_resp.json.return_value = responses.get(f'/{endpoint}', {})
            mock_resp.raise_for_status = Mock()
            return mock_resp

        mock_httpx_client.get.side_effect = mock_get
        mock_database_writer.insert_drones = AsyncMock(return_value=len(sample_drone_data))
        mock_database_writer.insert_signals = AsyncMock(return_value=len(sample_signal_data))
        mock_database_writer.insert_health = AsyncMock(return_value=True)
        mock_database_writer.update_kit_status = AsyncMock()

        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)

        # Perform one polling cycle
        drones_success = await collector.poll_drones()
        signals_success = await collector.poll_signals()
        status_success = await collector.poll_status()

        assert drones_success is True
        assert signals_success is True
        assert status_success is True

        # Verify all insert methods were called
        mock_database_writer.insert_drones.assert_called_once()
        mock_database_writer.insert_signals.assert_called_once()
        mock_database_writer.insert_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_recovery_after_failure(self, sample_kit_config, mock_database_writer, mock_httpx_client):
        """Test kit recovers after temporary failure."""
        collector = KitCollector(sample_kit_config, mock_database_writer, mock_httpx_client)

        # Simulate failure
        mock_httpx_client.get.side_effect = httpx.RequestError("Connection error")
        result1 = await collector.poll_drones()

        assert result1 is False
        assert collector.health.status == 'offline'
        assert collector.health.consecutive_failures == 1

        # Simulate recovery
        mock_httpx_client.get.side_effect = None
        mock_httpx_client.get.return_value.json.return_value = {'drones': []}
        mock_database_writer.insert_drones = AsyncMock(return_value=0)

        result2 = await collector.poll_drones()

        assert result2 is True
        assert collector.health.status == 'online'
        assert collector.health.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_multiple_kits_concurrent(self, sample_kits_config, mock_sqlalchemy_create_engine, mock_db_engine):
        """Test multiple kits can be polled concurrently."""
        # Create service with multiple kits
        with patch.object(DatabaseWriter, 'test_connection', return_value=True):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock responses
                mock_resp = AsyncMock()
                mock_resp.json.return_value = {}
                mock_resp.raise_for_status = Mock()
                mock_client.get.return_value = mock_resp

                # Create collectors
                db = DatabaseWriter('postgresql://test:test@localhost/test')
                collectors = []

                for kit_config in sample_kits_config[:2]:  # Use first 2 enabled kits
                    collector = KitCollector(kit_config, db, mock_client)
                    collectors.append(collector)

                # Poll all concurrently
                results = await asyncio.gather(
                    collectors[0].poll_drones(),
                    collectors[1].poll_drones(),
                    return_exceptions=True
                )

                # All should succeed
                assert all(r is True for r in results)
