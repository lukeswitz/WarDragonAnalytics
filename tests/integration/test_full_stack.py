#!/usr/bin/env python3
"""
Full-Stack Integration Tests for WarDragon Analytics

Tests the complete data flow: Collector → Database → API

These tests require Docker Compose to be running with the test stack.
Run with: pytest -m integration tests/integration/test_full_stack.py

Test coverage:
- Database operations (no mocks)
- API endpoints with real data
- Multi-kit data aggregation
- Time-based filtering
- CSV/KML export
- Data consistency across the stack
"""

import asyncio
import csv
import io
from datetime import datetime, timedelta, timezone
import pytest
import httpx


pytestmark = pytest.mark.integration


class TestHealthCheck:
    """Test basic health check endpoints."""

    def test_api_health(self, api_client):
        """Test that API health endpoint returns healthy status."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_database_connection(self, db_conn):
        """Test direct database connectivity."""
        result = await db_conn.fetchval("SELECT 1")
        assert result == 1


class TestKitsAPI:
    """Test kit management API endpoints."""

    @pytest.mark.asyncio
    async def test_list_all_kits(self, api_client, clean_database, sample_kits):
        """Test listing all configured kits."""
        response = api_client.get("/api/kits")
        assert response.status_code == 200

        data = response.json()
        assert "kits" in data
        assert "count" in data
        assert data["count"] == len(sample_kits)
        assert len(data["kits"]) == len(sample_kits)

        # Verify kit data structure
        kit = data["kits"][0]
        assert "kit_id" in kit
        assert "name" in kit
        assert "location" in kit
        assert "api_url" in kit
        assert "status" in kit
        assert "last_seen" in kit

    @pytest.mark.asyncio
    async def test_filter_kit_by_id(self, api_client, clean_database, sample_kits):
        """Test filtering kits by specific ID."""
        target_kit_id = "test-kit-001"
        response = api_client.get(f"/api/kits?kit_id={target_kit_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 1
        assert data["kits"][0]["kit_id"] == target_kit_id

    @pytest.mark.asyncio
    async def test_kit_status_calculation(self, api_client, clean_database, sample_kits):
        """Test that kit status is calculated correctly based on last_seen."""
        response = api_client.get("/api/kits")
        assert response.status_code == 200

        data = response.json()
        kits = {k["kit_id"]: k for k in data["kits"]}

        # Online kits should show online status (last_seen is recent)
        assert kits["test-kit-001"]["status"] == "online"
        assert kits["test-kit-002"]["status"] == "online"


class TestDronesAPI:
    """Test drone tracking API endpoints."""

    @pytest.mark.asyncio
    async def test_query_all_drones(self, api_client, clean_database, sample_kits, sample_drones):
        """Test querying all drone tracks."""
        response = api_client.get("/api/drones?time_range=1h")
        assert response.status_code == 200

        data = response.json()
        assert "drones" in data
        assert "count" in data
        assert "time_range" in data
        assert data["count"] == len(sample_drones)

        # Verify drone data structure
        drone = data["drones"][0]
        assert "time" in drone
        assert "kit_id" in drone
        assert "drone_id" in drone
        assert "track_type" in drone

    @pytest.mark.asyncio
    async def test_filter_drones_by_kit(self, api_client, clean_database, sample_kits, sample_drones):
        """Test filtering drones by kit ID."""
        target_kit = "test-kit-001"
        response = api_client.get(f"/api/drones?time_range=1h&kit_id={target_kit}")
        assert response.status_code == 200

        data = response.json()
        expected_count = sum(1 for d in sample_drones if d["kit_id"] == target_kit)
        assert data["count"] == expected_count

        # Verify all returned drones are from target kit
        for drone in data["drones"]:
            assert drone["kit_id"] == target_kit

    @pytest.mark.asyncio
    async def test_filter_drones_by_make(self, api_client, clean_database, sample_kits, sample_drones):
        """Test filtering drones by manufacturer (RID make)."""
        response = api_client.get("/api/drones?time_range=1h&rid_make=DJI")
        assert response.status_code == 200

        data = response.json()
        expected_count = sum(1 for d in sample_drones if d.get("rid_make") == "DJI")
        assert data["count"] == expected_count

        # Verify all returned drones are DJI
        for drone in data["drones"]:
            assert drone["rid_make"] == "DJI"

    @pytest.mark.asyncio
    async def test_filter_drones_by_track_type(self, api_client, clean_database, sample_kits, sample_drones):
        """Test filtering drones by track type (drone vs aircraft)."""
        # Test drone type
        response = api_client.get("/api/drones?time_range=1h&track_type=drone")
        assert response.status_code == 200
        data = response.json()
        drone_count = sum(1 for d in sample_drones if d["track_type"] == "drone")
        assert data["count"] == drone_count

        # Test aircraft type
        response = api_client.get("/api/drones?time_range=1h&track_type=aircraft")
        assert response.status_code == 200
        data = response.json()
        aircraft_count = sum(1 for d in sample_drones if d["track_type"] == "aircraft")
        assert data["count"] == aircraft_count

    @pytest.mark.asyncio
    async def test_multi_kit_tracking(self, api_client, clean_database, sample_kits, sample_drones):
        """Test that the same drone can be tracked by multiple kits."""
        # DJI-001 is tracked by both test-kit-001 and test-kit-002
        response = api_client.get("/api/drones?time_range=1h")
        assert response.status_code == 200

        data = response.json()
        dji_001_tracks = [d for d in data["drones"] if d["drone_id"] == "DJI-001"]

        # Should have 2 tracks for DJI-001 (one from each kit)
        assert len(dji_001_tracks) == 2
        kit_ids = {t["kit_id"] for t in dji_001_tracks}
        assert "test-kit-001" in kit_ids
        assert "test-kit-002" in kit_ids

    @pytest.mark.asyncio
    async def test_multiple_kit_filter(self, api_client, clean_database, sample_kits, sample_drones):
        """Test filtering by multiple kit IDs (comma-separated)."""
        response = api_client.get("/api/drones?time_range=1h&kit_id=test-kit-001,test-kit-002")
        assert response.status_code == 200

        data = response.json()
        # All drones from kit-001 and kit-002
        expected_count = sum(
            1 for d in sample_drones
            if d["kit_id"] in ["test-kit-001", "test-kit-002"]
        )
        assert data["count"] == expected_count

    @pytest.mark.asyncio
    async def test_limit_parameter(self, api_client, clean_database, sample_kits, sample_drones):
        """Test that limit parameter restricts result count."""
        response = api_client.get("/api/drones?time_range=1h&limit=2")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] <= 2
        assert len(data["drones"]) <= 2


class TestSignalsAPI:
    """Test FPV signal detection API endpoints."""

    @pytest.mark.asyncio
    async def test_query_all_signals(self, api_client, clean_database, sample_kits, sample_signals):
        """Test querying all signal detections."""
        response = api_client.get("/api/signals?time_range=1h")
        assert response.status_code == 200

        data = response.json()
        assert "signals" in data
        assert "count" in data
        assert data["count"] == len(sample_signals)

        # Verify signal data structure
        signal = data["signals"][0]
        assert "time" in signal
        assert "kit_id" in signal
        assert "freq_mhz" in signal
        assert "detection_type" in signal

    @pytest.mark.asyncio
    async def test_filter_signals_by_kit(self, api_client, clean_database, sample_kits, sample_signals):
        """Test filtering signals by kit ID."""
        target_kit = "test-kit-001"
        response = api_client.get(f"/api/signals?time_range=1h&kit_id={target_kit}")
        assert response.status_code == 200

        data = response.json()
        expected_count = sum(1 for s in sample_signals if s["kit_id"] == target_kit)
        assert data["count"] == expected_count

        # Verify all returned signals are from target kit
        for signal in data["signals"]:
            assert signal["kit_id"] == target_kit

    @pytest.mark.asyncio
    async def test_filter_signals_by_detection_type(self, api_client, clean_database, sample_kits, sample_signals):
        """Test filtering signals by detection type (analog vs DJI)."""
        # Test analog signals
        response = api_client.get("/api/signals?time_range=1h&detection_type=analog")
        assert response.status_code == 200
        data = response.json()
        analog_count = sum(1 for s in sample_signals if s["detection_type"] == "analog")
        assert data["count"] == analog_count

        # Test DJI signals
        response = api_client.get("/api/signals?time_range=1h&detection_type=dji")
        assert response.status_code == 200
        data = response.json()
        dji_count = sum(1 for s in sample_signals if s["detection_type"] == "dji")
        assert data["count"] == dji_count


class TestTimeRangeFiltering:
    """Test time-based filtering across endpoints."""

    @pytest.mark.asyncio
    async def test_time_range_1h(self, api_client, clean_database, sample_kits, sample_drones):
        """Test 1-hour time range filter."""
        response = api_client.get("/api/drones?time_range=1h")
        assert response.status_code == 200

        data = response.json()
        assert "time_range" in data
        assert data["count"] > 0  # Should include recent sample data

    @pytest.mark.asyncio
    async def test_time_range_24h(self, api_client, clean_database, sample_kits, sample_drones):
        """Test 24-hour time range filter."""
        response = api_client.get("/api/drones?time_range=24h")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] > 0

    @pytest.mark.asyncio
    async def test_time_range_7d(self, api_client, clean_database, sample_kits, sample_drones):
        """Test 7-day time range filter."""
        response = api_client.get("/api/drones?time_range=7d")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] > 0

    @pytest.mark.asyncio
    async def test_custom_time_range(self, api_client, clean_database, sample_kits, sample_drones):
        """Test custom time range with specific start and end times."""
        now = datetime.now(timezone.utc)
        start = (now - timedelta(hours=2)).isoformat()
        end = now.isoformat()

        response = api_client.get(f"/api/drones?time_range=custom:{start},{end}")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] > 0
        assert data["time_range"]["start"]
        assert data["time_range"]["end"]


class TestDataAggregation:
    """Test multi-kit data aggregation capabilities."""

    @pytest.mark.asyncio
    async def test_aggregate_drones_across_kits(self, api_client, clean_database, sample_kits, sample_drones):
        """Test aggregating drone data from all kits."""
        response = api_client.get("/api/drones?time_range=1h")
        assert response.status_code == 200

        data = response.json()

        # Count unique drones (by drone_id)
        unique_drones = set(d["drone_id"] for d in data["drones"])

        # Should have 4 unique drones: DJI-001, DJI-002, AUTEL-001, A1B2C3
        # Even though DJI-001 appears twice (tracked by 2 kits)
        assert len(unique_drones) == 4

    @pytest.mark.asyncio
    async def test_aggregate_signals_across_kits(self, api_client, clean_database, sample_kits, sample_signals):
        """Test aggregating signal data from all kits."""
        response = api_client.get("/api/signals?time_range=1h")
        assert response.status_code == 200

        data = response.json()

        # Verify we have signals from multiple kits
        kit_ids = set(s["kit_id"] for s in data["signals"])
        assert len(kit_ids) >= 2

        # Verify we have both analog and DJI detections
        detection_types = set(s["detection_type"] for s in data["signals"])
        assert "analog" in detection_types
        assert "dji" in detection_types


class TestCSVExport:
    """Test CSV export functionality with real data."""

    @pytest.mark.asyncio
    async def test_export_csv_basic(self, api_client, clean_database, sample_kits, sample_drones):
        """Test basic CSV export."""
        response = api_client.get("/api/export/csv?time_range=1h")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_csv_content_structure(self, api_client, clean_database, sample_kits, sample_drones):
        """Test that CSV content has correct structure and headers."""
        response = api_client.get("/api/export/csv?time_range=1h")
        assert response.status_code == 200

        # Parse CSV content
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        # Verify headers
        expected_headers = {
            "time", "kit_id", "drone_id", "lat", "lon", "alt",
            "speed", "heading", "track_type", "rid_make", "rid_model"
        }
        actual_headers = set(csv_reader.fieldnames)
        assert expected_headers.issubset(actual_headers)

        # Verify we have data rows
        rows = list(csv_reader)
        assert len(rows) == len(sample_drones)

    @pytest.mark.asyncio
    async def test_csv_filtered_export(self, api_client, clean_database, sample_kits, sample_drones):
        """Test CSV export with filters applied."""
        response = api_client.get("/api/export/csv?time_range=1h&rid_make=DJI")
        assert response.status_code == 200

        # Parse CSV and verify filtering
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        expected_count = sum(1 for d in sample_drones if d.get("rid_make") == "DJI")
        assert len(rows) == expected_count

        # Verify all rows are DJI
        for row in rows:
            assert row["rid_make"] == "DJI"

    @pytest.mark.asyncio
    async def test_csv_data_integrity(self, api_client, clean_database, sample_kits, sample_drones):
        """Test that CSV export contains accurate data from database."""
        response = api_client.get("/api/export/csv?time_range=1h&kit_id=test-kit-001")
        assert response.status_code == 200

        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        # Find a specific drone in both CSV and sample data
        dji_001_csv = next((r for r in rows if r["drone_id"] == "DJI-001"), None)
        dji_001_sample = next((d for d in sample_drones if d["drone_id"] == "DJI-001" and d["kit_id"] == "test-kit-001"), None)

        assert dji_001_csv is not None
        assert dji_001_sample is not None

        # Verify data matches
        assert float(dji_001_csv["lat"]) == pytest.approx(dji_001_sample["lat"], rel=1e-5)
        assert float(dji_001_csv["lon"]) == pytest.approx(dji_001_sample["lon"], rel=1e-5)
        assert dji_001_csv["rid_make"] == dji_001_sample["rid_make"]


class TestCollectorDatabaseFlow:
    """Test the Collector → Database data flow."""

    @pytest.mark.asyncio
    async def test_insert_drone_via_collector_functions(self, db_conn, clean_database):
        """Test inserting drone data directly (simulating collector behavior)."""
        now = datetime.now(timezone.utc)

        # Insert a kit first
        await db_conn.execute(
            """
            INSERT INTO kits (kit_id, name, api_url, status, last_seen)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "collector-test-kit", "Collector Test", "http://test:8088", "online", now
        )

        # Insert a drone (simulating collector.insert_drones)
        await db_conn.execute(
            """
            INSERT INTO drones (
                time, kit_id, drone_id, lat, lon, alt, speed, heading,
                rid_make, rid_model, track_type
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            now, "collector-test-kit", "TEST-DRONE-001",
            38.0, -122.0, 100.0, 10.0, 180.0,
            "TestMake", "TestModel", "drone"
        )

        # Verify insertion
        result = await db_conn.fetchrow(
            "SELECT * FROM drones WHERE drone_id = $1",
            "TEST-DRONE-001"
        )
        assert result is not None
        assert result["kit_id"] == "collector-test-kit"
        assert result["rid_make"] == "TestMake"

    @pytest.mark.asyncio
    async def test_insert_signal_via_collector_functions(self, db_conn, clean_database):
        """Test inserting signal data directly (simulating collector behavior)."""
        now = datetime.now(timezone.utc)

        # Insert a kit first
        await db_conn.execute(
            """
            INSERT INTO kits (kit_id, name, api_url, status, last_seen)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "collector-test-kit", "Collector Test", "http://test:8088", "online", now
        )

        # Insert a signal (simulating collector.insert_signals)
        await db_conn.execute(
            """
            INSERT INTO signals (
                time, kit_id, freq_mhz, power_dbm, bandwidth_mhz, detection_type
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            now, "collector-test-kit", 5800.0, -50.0, 10.0, "analog"
        )

        # Verify insertion
        result = await db_conn.fetchrow(
            "SELECT * FROM signals WHERE kit_id = $1 AND freq_mhz = $2",
            "collector-test-kit", 5800.0
        )
        assert result is not None
        assert result["power_dbm"] == pytest.approx(-50.0)
        assert result["detection_type"] == "analog"

    @pytest.mark.asyncio
    async def test_update_kit_status(self, db_conn, clean_database):
        """Test updating kit status (simulating collector.update_kit_status)."""
        now = datetime.now(timezone.utc)

        # Insert initial kit
        await db_conn.execute(
            """
            INSERT INTO kits (kit_id, name, api_url, status, last_seen)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "status-test-kit", "Status Test", "http://test:8088", "unknown", now
        )

        # Update status (simulating collector updating after successful poll)
        await db_conn.execute(
            """
            UPDATE kits SET status = $1, last_seen = $2 WHERE kit_id = $3
            """,
            "online", now, "status-test-kit"
        )

        # Verify update
        result = await db_conn.fetchrow(
            "SELECT * FROM kits WHERE kit_id = $1",
            "status-test-kit"
        )
        assert result["status"] == "online"


class TestFullStackIntegration:
    """End-to-end integration tests covering the complete stack."""

    @pytest.mark.asyncio
    async def test_complete_data_flow(self, db_conn, api_client, clean_database):
        """
        Test complete flow: Insert data via collector → Query via API → Verify results.

        This simulates the real-world scenario:
        1. Collector inserts kit configuration
        2. Collector inserts drone detections
        3. User queries API for drone data
        4. API returns correct data from database
        """
        now = datetime.now(timezone.utc)

        # Step 1: Collector registers kit
        await db_conn.execute(
            """
            INSERT INTO kits (kit_id, name, location, api_url, status, last_seen)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            "integration-kit", "Integration Test Kit", "Field Site",
            "http://integration:8088", "online", now
        )

        # Step 2: Collector inserts drone data from multiple detections
        drones_to_insert = [
            ("DRONE-A", 37.5, -122.5, "DJI", "Mavic 3"),
            ("DRONE-B", 37.6, -122.6, "Autel", "EVO II"),
            ("AIRCRAFT-1", 37.7, -122.7, None, None),
        ]

        for drone_id, lat, lon, make, model in drones_to_insert:
            track_type = "aircraft" if drone_id.startswith("AIRCRAFT") else "drone"
            await db_conn.execute(
                """
                INSERT INTO drones (
                    time, kit_id, drone_id, lat, lon, alt, track_type, rid_make, rid_model
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                now, "integration-kit", drone_id, lat, lon, 100.0,
                track_type, make, model
            )

        # Step 3: User queries API for drones from this kit
        response = api_client.get("/api/drones?time_range=1h&kit_id=integration-kit")
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 3

        # Step 4: Verify all drones are present with correct data
        drone_ids = {d["drone_id"] for d in data["drones"]}
        assert drone_ids == {"DRONE-A", "DRONE-B", "AIRCRAFT-1"}

        # Verify specific drone data
        drone_a = next(d for d in data["drones"] if d["drone_id"] == "DRONE-A")
        assert drone_a["lat"] == pytest.approx(37.5)
        assert drone_a["lon"] == pytest.approx(-122.5)
        assert drone_a["rid_make"] == "DJI"
        assert drone_a["track_type"] == "drone"

    @pytest.mark.asyncio
    async def test_multi_kit_aggregation_flow(self, db_conn, api_client, clean_database):
        """
        Test multi-kit aggregation: Multiple kits track same drone.

        Scenario:
        1. Two kits are deployed in the field
        2. Both detect the same drone
        3. API aggregates data from both kits
        """
        now = datetime.now(timezone.utc)

        # Register two kits
        for kit_num in [1, 2]:
            await db_conn.execute(
                """
                INSERT INTO kits (kit_id, name, api_url, status, last_seen)
                VALUES ($1, $2, $3, $4, $5)
                """,
                f"field-kit-{kit_num}", f"Field Kit {kit_num}",
                f"http://field-{kit_num}:8088", "online", now
            )

        # Both kits detect the same drone
        shared_drone_id = "SHARED-DRONE-999"
        for kit_num in [1, 2]:
            await db_conn.execute(
                """
                INSERT INTO drones (
                    time, kit_id, drone_id, lat, lon, alt, rssi, track_type
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                now, f"field-kit-{kit_num}", shared_drone_id,
                37.8, -122.8, 150.0, -60 - (kit_num * 5), "drone"
            )

        # Query for all detections
        response = api_client.get("/api/drones?time_range=1h")
        assert response.status_code == 200

        data = response.json()
        shared_tracks = [d for d in data["drones"] if d["drone_id"] == shared_drone_id]

        # Should have 2 tracks (one from each kit)
        assert len(shared_tracks) == 2
        kit_ids = {t["kit_id"] for t in shared_tracks}
        assert kit_ids == {"field-kit-1", "field-kit-2"}

    @pytest.mark.asyncio
    async def test_export_after_data_insertion(self, db_conn, api_client, clean_database):
        """
        Test CSV export immediately after data insertion.

        Ensures exported data matches inserted data.
        """
        now = datetime.now(timezone.utc)

        # Insert test data
        await db_conn.execute(
            """
            INSERT INTO kits (kit_id, name, api_url, status, last_seen)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "export-test-kit", "Export Test", "http://test:8088", "online", now
        )

        test_drones = [
            ("EXPORT-DRONE-1", 40.0, -120.0, "DJI"),
            ("EXPORT-DRONE-2", 40.1, -120.1, "Autel"),
        ]

        for drone_id, lat, lon, make in test_drones:
            await db_conn.execute(
                """
                INSERT INTO drones (
                    time, kit_id, drone_id, lat, lon, alt, track_type, rid_make
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                now, "export-test-kit", drone_id, lat, lon, 100.0, "drone", make
            )

        # Export to CSV
        response = api_client.get("/api/export/csv?time_range=1h&kit_id=export-test-kit")
        assert response.status_code == 200

        # Verify CSV content
        csv_reader = csv.DictReader(io.StringIO(response.text))
        rows = list(csv_reader)

        assert len(rows) == 2
        exported_ids = {r["drone_id"] for r in rows}
        assert exported_ids == {"EXPORT-DRONE-1", "EXPORT-DRONE-2"}


class TestDataConsistency:
    """Test data consistency and integrity across the stack."""

    @pytest.mark.asyncio
    async def test_database_api_consistency(self, db_conn, api_client, clean_database, sample_kits, sample_drones):
        """Verify API returns exact data that exists in database."""
        # Query database directly
        db_drones = await db_conn.fetch(
            "SELECT drone_id, kit_id, lat, lon FROM drones ORDER BY drone_id"
        )

        # Query API
        response = api_client.get("/api/drones?time_range=1h&limit=10000")
        assert response.status_code == 200
        api_drones = sorted(response.json()["drones"], key=lambda d: d["drone_id"])

        # Compare counts
        assert len(db_drones) == len(api_drones)

        # Compare data
        for db_drone, api_drone in zip(db_drones, api_drones):
            assert db_drone["drone_id"] == api_drone["drone_id"]
            assert db_drone["kit_id"] == api_drone["kit_id"]
            if db_drone["lat"] is not None:
                assert db_drone["lat"] == pytest.approx(api_drone["lat"], rel=1e-5)
            if db_drone["lon"] is not None:
                assert db_drone["lon"] == pytest.approx(api_drone["lon"], rel=1e-5)

    @pytest.mark.asyncio
    async def test_duplicate_prevention(self, db_conn, clean_database):
        """Test that duplicate drone records are handled correctly."""
        now = datetime.now(timezone.utc)

        await db_conn.execute(
            """
            INSERT INTO kits (kit_id, name, api_url, status, last_seen)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "dup-test-kit", "Duplicate Test", "http://test:8088", "online", now
        )

        # Insert initial drone record
        await db_conn.execute(
            """
            INSERT INTO drones (
                time, kit_id, drone_id, lat, lon, alt, track_type
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            now, "dup-test-kit", "DUP-DRONE", 37.0, -122.0, 100.0, "drone"
        )

        # Try to insert duplicate (same time, kit_id, drone_id)
        # Should update existing record due to ON CONFLICT clause
        await db_conn.execute(
            """
            INSERT INTO drones (
                time, kit_id, drone_id, lat, lon, alt, track_type
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (time, kit_id, drone_id) DO UPDATE SET
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon
            """,
            now, "dup-test-kit", "DUP-DRONE", 37.1, -122.1, 100.0, "drone"
        )

        # Verify only one record exists with updated coordinates
        result = await db_conn.fetchrow(
            """
            SELECT COUNT(*) as count, lat, lon
            FROM drones
            WHERE drone_id = $1
            GROUP BY lat, lon
            """,
            "DUP-DRONE"
        )

        assert result["count"] == 1
        assert result["lat"] == pytest.approx(37.1)
        assert result["lon"] == pytest.approx(-122.1)
