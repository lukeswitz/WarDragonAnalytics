#!/usr/bin/env python3
"""
Phase 2 Test Data Generator for WarDragon Analytics

Generates realistic test data with specific patterns for testing:
- Repeated drone detections (surveillance patterns)
- Coordinated activity (swarms)
- Operator reuse patterns
- Multi-kit detections (triangulation)
- Anomalous behavior (speed/altitude spikes)
- FPV signal detections

Usage:
    python tests/generate_test_data.py --scenario all
    python tests/generate_test_data.py --scenario coordinated --count 10
    python tests/generate_test_data.py --scenario repeated --drone-id TEST-123
    python tests/generate_test_data.py --clean
    python tests/generate_test_data.py --dry-run --scenario normal
"""

import argparse
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
import math

# Database imports
try:
    import psycopg2
    from psycopg2.extras import execute_batch
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: psycopg2 not installed. Install with: pip install psycopg2-binary", file=sys.stderr)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Realistic drone makes and models
DRONE_MAKES_MODELS = [
    ("DJI", "Mini 3 Pro"),
    ("DJI", "Air 3"),
    ("DJI", "Mavic 3"),
    ("DJI", "Mavic 3 Pro"),
    ("DJI", "Inspire 3"),
    ("DJI", "Phantom 4 Pro"),
    ("DJI", "Matrice 30"),
    ("DJI", "Avata 2"),
    ("Autel", "EVO II Pro"),
    ("Autel", "EVO Nano+"),
    ("Autel", "EVO Lite+"),
    ("Skydio", "X2"),
    ("Parrot", "ANAFI USA"),
    ("DJI", "FPV"),
]

# FPV frequency bands (5.8 GHz)
FPV_FREQUENCIES = {
    "analog": [5740, 5760, 5800, 5820, 5840, 5860],
    "dji": [5725, 5760, 5795, 5830, 5865],
}

# UA types (Remote ID)
UA_TYPES = ["Aeroplane", "Helicopter/Multirotor", "Gyroplane", "VTOL", "Glider"]

# Base location for test area (centered around a realistic coordinate)
BASE_LAT = 37.7749  # San Francisco area
BASE_LON = -122.4194


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def random_walk_gps(center_lat: float, center_lon: float, max_distance_km: float = 2.0) -> Tuple[float, float]:
    """Generate a random GPS coordinate within max_distance_km of center point."""
    lat_offset = (random.random() - 0.5) * 2 * (max_distance_km / 111.0)
    lon_offset = (random.random() - 0.5) * 2 * (max_distance_km / (111.0 * math.cos(math.radians(center_lat))))
    return (center_lat + lat_offset, center_lon + lon_offset)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two GPS coordinates."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def generate_mac() -> str:
    """Generate a random MAC address."""
    return ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])


def generate_drone_id(prefix: str = None) -> str:
    """Generate a realistic drone serial number."""
    if prefix is None:
        prefix = random.choice(["DJI", "AUT", "SKY", "PAR"])
    return f"{prefix}{random.randint(100000, 999999)}"


def generate_operator_id() -> str:
    """Generate a realistic operator ID (FAA format)."""
    return f"FAA{random.randint(1000000000000, 9999999999999)}"


def interpolate_position(start: Tuple[float, float], end: Tuple[float, float], fraction: float) -> Tuple[float, float]:
    """Linear interpolation between two GPS points."""
    lat = start[0] + (end[0] - start[0]) * fraction
    lon = start[1] + (end[1] - start[1]) * fraction
    return (lat, lon)


def calculate_heading(start: Tuple[float, float], end: Tuple[float, float]) -> float:
    """Calculate heading (degrees) from start to end point."""
    lat1, lon1 = math.radians(start[0]), math.radians(start[1])
    lat2, lon2 = math.radians(end[0]), math.radians(end[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    heading = math.degrees(math.atan2(x, y))
    return (heading + 360) % 360


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def get_db_connection(db_url: str = None):
    """Create database connection using DATABASE_URL environment variable or provided URL."""
    if not DB_AVAILABLE:
        raise RuntimeError("psycopg2 not available. Install with: pip install psycopg2-binary")

    if db_url is None:
        db_url = os.environ.get("DATABASE_URL", "postgresql://wardragon:test123@localhost:5432/wardragon")

    return psycopg2.connect(db_url)


def insert_drones_batch(conn, drones: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Batch insert drone records."""
    if not drones:
        return 0

    if dry_run:
        print(f"[DRY RUN] Would insert {len(drones)} drone records")
        return len(drones)

    query = """
        INSERT INTO drones (
            time, kit_id, drone_id, lat, lon, alt, speed, heading,
            pilot_lat, pilot_lon, home_lat, home_lon, mac, rssi, freq,
            ua_type, operator_id, caa_id, rid_make, rid_model, rid_source, track_type
        ) VALUES (
            %(time)s, %(kit_id)s, %(drone_id)s, %(lat)s, %(lon)s, %(alt)s, %(speed)s, %(heading)s,
            %(pilot_lat)s, %(pilot_lon)s, %(home_lat)s, %(home_lon)s, %(mac)s, %(rssi)s, %(freq)s,
            %(ua_type)s, %(operator_id)s, %(caa_id)s, %(rid_make)s, %(rid_model)s, %(rid_source)s, %(track_type)s
        )
        ON CONFLICT (time, kit_id, drone_id) DO NOTHING
    """

    with conn.cursor() as cur:
        execute_batch(cur, query, drones, page_size=1000)
    conn.commit()
    return len(drones)


def insert_signals_batch(conn, signals: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Batch insert signal records."""
    if not signals:
        return 0

    if dry_run:
        print(f"[DRY RUN] Would insert {len(signals)} signal records")
        return len(signals)

    query = """
        INSERT INTO signals (
            time, kit_id, freq_mhz, power_dbm, bandwidth_mhz,
            lat, lon, alt, detection_type
        ) VALUES (
            %(time)s, %(kit_id)s, %(freq_mhz)s, %(power_dbm)s, %(bandwidth_mhz)s,
            %(lat)s, %(lon)s, %(alt)s, %(detection_type)s
        )
        ON CONFLICT (time, kit_id, freq_mhz) DO NOTHING
    """

    with conn.cursor() as cur:
        execute_batch(cur, query, signals, page_size=1000)
    conn.commit()
    return len(signals)


def insert_health_batch(conn, health_records: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Batch insert system health records."""
    if not health_records:
        return 0

    if dry_run:
        print(f"[DRY RUN] Would insert {len(health_records)} health records")
        return len(health_records)

    query = """
        INSERT INTO system_health (
            time, kit_id, lat, lon, alt, cpu_percent, memory_percent,
            disk_percent, uptime_hours, temp_cpu, temp_gpu
        ) VALUES (
            %(time)s, %(kit_id)s, %(lat)s, %(lon)s, %(alt)s, %(cpu_percent)s, %(memory_percent)s,
            %(disk_percent)s, %(uptime_hours)s, %(temp_cpu)s, %(temp_gpu)s
        )
        ON CONFLICT (time, kit_id) DO NOTHING
    """

    with conn.cursor() as cur:
        execute_batch(cur, query, health_records, page_size=1000)
    conn.commit()
    return len(health_records)


def clean_test_data(conn, dry_run: bool = False):
    """Remove all test data from database."""
    if dry_run:
        print("[DRY RUN] Would clean all test data from database")
        return

    with conn.cursor() as cur:
        cur.execute("DELETE FROM drones WHERE kit_id LIKE 'test-kit-%'")
        drones_deleted = cur.rowcount
        cur.execute("DELETE FROM signals WHERE kit_id LIKE 'test-kit-%'")
        signals_deleted = cur.rowcount
        cur.execute("DELETE FROM system_health WHERE kit_id LIKE 'test-kit-%'")
        health_deleted = cur.rowcount
        cur.execute("DELETE FROM kits WHERE kit_id LIKE 'test-kit-%'")
        kits_deleted = cur.rowcount
    conn.commit()

    print(f"Cleaned test data:")
    print(f"  Kits: {kits_deleted}")
    print(f"  Drones: {drones_deleted}")
    print(f"  Signals: {signals_deleted}")
    print(f"  Health: {health_deleted}")


def upsert_kits(conn, kits: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """Insert or update kit records."""
    if not kits:
        return 0

    if dry_run:
        print(f"[DRY RUN] Would upsert {len(kits)} kits")
        return len(kits)

    query = """
        INSERT INTO kits (kit_id, name, location, api_url, last_seen, status, created_at)
        VALUES (%(kit_id)s, %(name)s, %(location)s, %(api_url)s, %(last_seen)s, %(status)s, %(created_at)s)
        ON CONFLICT (kit_id) DO UPDATE SET
            last_seen = EXCLUDED.last_seen,
            status = EXCLUDED.status
    """

    with conn.cursor() as cur:
        execute_batch(cur, query, kits, page_size=100)
    conn.commit()
    return len(kits)


# ============================================================================
# SCENARIO GENERATORS
# ============================================================================

def scenario_normal(conn, dry_run: bool = False) -> Dict[str, int]:
    """
    Normal operations baseline:
    - 3 kits detecting drones
    - 20-30 drones with random locations
    - Typical flight patterns (altitude 50-150m, speed 5-15m/s)
    - Data spread over last 48 hours
    """
    print("\n=== Scenario: Normal Operations Baseline ===\n")

    stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

    # Time range: last 48 hours
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=48)

    # Create 3 kits
    kits = []
    for i in range(3):
        kit_id = f"test-kit-{i+1:03d}"
        kit_lat, kit_lon = random_walk_gps(BASE_LAT, BASE_LON, 5.0)
        kits.append({
            "kit_id": kit_id,
            "name": f"Test Kit {i+1}",
            "location": f"Test Location {i+1}",
            "api_url": f"http://192.168.1.{100+i}:8088",
            "last_seen": end_time,
            "status": "online",
            "created_at": start_time,
            "lat": kit_lat,
            "lon": kit_lon,
        })

    stats["kits"] = upsert_kits(conn, kits, dry_run)
    print(f"Created {stats['kits']} kits")

    # Generate 20-30 drone tracks
    num_drones = random.randint(20, 30)
    drone_batch = []
    signal_batch = []
    health_batch = []

    for _ in range(num_drones):
        # Random kit
        kit = random.choice(kits)

        # Random start time in last 48 hours
        flight_start = start_time + timedelta(seconds=random.randint(0, int(48 * 3600 * 0.8)))
        flight_duration = timedelta(minutes=random.randint(10, 30))

        # Drone details
        drone_id = generate_drone_id()
        make, model = random.choice(DRONE_MAKES_MODELS)
        operator_id = generate_operator_id()
        pilot_lat, pilot_lon = random_walk_gps(kit["lat"], kit["lon"], 2.0)

        # Generate positions every 5 seconds
        current_time = flight_start
        while current_time < flight_start + flight_duration:
            # Normal flight pattern
            drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.5)
            alt = random.uniform(50, 150)  # Normal altitude
            speed = random.uniform(5, 15)  # Normal speed
            heading = random.uniform(0, 360)

            drone_batch.append({
                "time": current_time,
                "kit_id": kit["kit_id"],
                "drone_id": drone_id,
                "lat": round(drone_lat, 6),
                "lon": round(drone_lon, 6),
                "alt": round(alt, 1),
                "speed": round(speed, 1),
                "heading": round(heading, 1),
                "pilot_lat": round(pilot_lat, 6),
                "pilot_lon": round(pilot_lon, 6),
                "home_lat": round(pilot_lat, 6),
                "home_lon": round(pilot_lon, 6),
                "mac": generate_mac(),
                "rssi": random.randint(-85, -50),
                "freq": round(random.choice([2400.0, 2450.0, 5800.0]), 1),
                "ua_type": random.choice(UA_TYPES),
                "operator_id": operator_id,
                "caa_id": "",
                "rid_make": make,
                "rid_model": model,
                "rid_source": random.choice(["wifi", "ble", "dji"]),
                "track_type": "drone",
            })

            current_time += timedelta(seconds=5)

    stats["drones"] = insert_drones_batch(conn, drone_batch, dry_run)
    print(f"Generated {stats['drones']} drone records for {num_drones} drones")

    # Generate system health data
    for kit in kits:
        current_time = start_time
        while current_time <= end_time:
            health_batch.append({
                "time": current_time,
                "kit_id": kit["kit_id"],
                "lat": kit["lat"],
                "lon": kit["lon"],
                "alt": random.uniform(10, 50),
                "cpu_percent": random.uniform(20, 60),
                "memory_percent": random.uniform(30, 70),
                "disk_percent": random.uniform(20, 50),
                "uptime_hours": (current_time - start_time).total_seconds() / 3600,
                "temp_cpu": random.uniform(45, 60),
                "temp_gpu": random.uniform(40, 55),
            })
            current_time += timedelta(minutes=5)

    stats["health"] = insert_health_batch(conn, health_batch, dry_run)
    print(f"Generated {stats['health']} health records")

    return stats


def scenario_repeated_drone(conn, drone_id: str = None, count: int = 5, dry_run: bool = False) -> Dict[str, int]:
    """
    Repeated drone pattern (surveillance):
    - Same drone_id appearing 3-5 times over 24 hours
    - Different locations each time
    - Simulate surveillance pattern
    """
    print("\n=== Scenario: Repeated Drone (Surveillance Pattern) ===\n")

    stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

    if drone_id is None:
        drone_id = f"SURVEILLANCE-{random.randint(10000, 99999)}"

    # Use existing kit or create one
    kit_id = "test-kit-001"
    kit_lat, kit_lon = random_walk_gps(BASE_LAT, BASE_LON, 5.0)

    kits = [{
        "kit_id": kit_id,
        "name": "Test Kit 1",
        "location": "Test Location 1",
        "api_url": "http://192.168.1.100:8088",
        "last_seen": datetime.now(timezone.utc),
        "status": "online",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=48),
    }]

    stats["kits"] = upsert_kits(conn, kits, dry_run)

    # Generate 3-5 appearances over 24 hours
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)

    make, model = random.choice(DRONE_MAKES_MODELS)
    operator_id = generate_operator_id()

    drone_batch = []

    for appearance in range(count):
        # Different time slots throughout the day
        appearance_start = start_time + timedelta(hours=(24 / count) * appearance)
        flight_duration = timedelta(minutes=random.randint(15, 30))

        # Different location each time (but in same general area)
        pilot_lat, pilot_lon = random_walk_gps(kit_lat, kit_lon, 3.0)

        print(f"Appearance {appearance + 1}/{count}: {appearance_start.strftime('%Y-%m-%d %H:%M')} at ({pilot_lat:.4f}, {pilot_lon:.4f})")

        # Generate flight
        current_time = appearance_start
        while current_time < appearance_start + flight_duration:
            drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.5)

            drone_batch.append({
                "time": current_time,
                "kit_id": kit_id,
                "drone_id": drone_id,
                "lat": round(drone_lat, 6),
                "lon": round(drone_lon, 6),
                "alt": round(random.uniform(60, 120), 1),
                "speed": round(random.uniform(5, 12), 1),
                "heading": round(random.uniform(0, 360), 1),
                "pilot_lat": round(pilot_lat, 6),
                "pilot_lon": round(pilot_lon, 6),
                "home_lat": round(pilot_lat, 6),
                "home_lon": round(pilot_lon, 6),
                "mac": generate_mac(),
                "rssi": random.randint(-80, -50),
                "freq": 5800.0,
                "ua_type": "Helicopter/Multirotor",
                "operator_id": operator_id,
                "caa_id": "",
                "rid_make": make,
                "rid_model": model,
                "rid_source": "dji",
                "track_type": "drone",
            })

            current_time += timedelta(seconds=5)

    stats["drones"] = insert_drones_batch(conn, drone_batch, dry_run)
    print(f"Generated {stats['drones']} drone records for {count} appearances of {drone_id}")

    return stats


def scenario_coordinated_activity(conn, count: int = 1, dry_run: bool = False) -> Dict[str, int]:
    """
    Coordinated activity (potential swarm):
    - 4-6 drones appearing together (within 500m, within 5 min)
    - Similar flight patterns
    - Potential swarm behavior
    """
    print("\n=== Scenario: Coordinated Activity (Swarm) ===\n")

    stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

    # Create kit
    kit_id = "test-kit-001"
    kit_lat, kit_lon = random_walk_gps(BASE_LAT, BASE_LON, 5.0)

    kits = [{
        "kit_id": kit_id,
        "name": "Test Kit 1",
        "location": "Test Location 1",
        "api_url": "http://192.168.1.100:8088",
        "last_seen": datetime.now(timezone.utc),
        "status": "online",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=48),
    }]

    stats["kits"] = upsert_kits(conn, kits, dry_run)

    drone_batch = []

    for swarm_num in range(count):
        # Number of drones in swarm
        num_drones = random.randint(4, 6)

        # Start time (staggered within 5 minutes)
        base_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))

        # Central location for swarm
        central_lat, central_lon = random_walk_gps(kit_lat, kit_lon, 2.0)

        print(f"\nSwarm {swarm_num + 1}/{count}: {num_drones} drones at {base_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Location: ({central_lat:.4f}, {central_lon:.4f})")

        # Generate swarm drones
        for drone_num in range(num_drones):
            drone_id = f"SWARM-{swarm_num+1:02d}-{drone_num+1:02d}"

            # Slight time offset (within 5 minutes)
            start_time = base_time + timedelta(seconds=random.randint(0, 300))
            flight_duration = timedelta(minutes=random.randint(15, 25))

            # Position within 500m of central point
            pilot_lat, pilot_lon = random_walk_gps(central_lat, central_lon, 0.5)

            make, model = random.choice(DRONE_MAKES_MODELS)
            operator_id = generate_operator_id()

            # Generate coordinated flight
            current_time = start_time
            while current_time < start_time + flight_duration:
                # Stay close to swarm center
                drone_lat, drone_lon = random_walk_gps(central_lat, central_lon, 0.5)

                drone_batch.append({
                    "time": current_time,
                    "kit_id": kit_id,
                    "drone_id": drone_id,
                    "lat": round(drone_lat, 6),
                    "lon": round(drone_lon, 6),
                    "alt": round(random.uniform(80, 120), 1),  # Similar altitude
                    "speed": round(random.uniform(8, 12), 1),  # Similar speed
                    "heading": round(random.uniform(0, 360), 1),
                    "pilot_lat": round(pilot_lat, 6),
                    "pilot_lon": round(pilot_lon, 6),
                    "home_lat": round(pilot_lat, 6),
                    "home_lon": round(pilot_lon, 6),
                    "mac": generate_mac(),
                    "rssi": random.randint(-75, -50),
                    "freq": 5800.0,
                    "ua_type": "Helicopter/Multirotor",
                    "operator_id": operator_id,
                    "caa_id": "",
                    "rid_make": make,
                    "rid_model": model,
                    "rid_source": "dji",
                    "track_type": "drone",
                })

                current_time += timedelta(seconds=5)

    stats["drones"] = insert_drones_batch(conn, drone_batch, dry_run)
    print(f"\nGenerated {stats['drones']} drone records for {count} swarm(s)")

    return stats


def scenario_operator_reuse(conn, dry_run: bool = False) -> Dict[str, int]:
    """
    Operator reuse:
    - Same operator_id across 3 different drones
    - 2-3 pilots within 50m using different drones
    """
    print("\n=== Scenario: Operator Reuse ===\n")

    stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

    # Create kit
    kit_id = "test-kit-001"
    kit_lat, kit_lon = random_walk_gps(BASE_LAT, BASE_LON, 5.0)

    kits = [{
        "kit_id": kit_id,
        "name": "Test Kit 1",
        "location": "Test Location 1",
        "api_url": "http://192.168.1.100:8088",
        "last_seen": datetime.now(timezone.utc),
        "status": "online",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=48),
    }]

    stats["kits"] = upsert_kits(conn, kits, dry_run)

    drone_batch = []

    # Scenario A: Same operator_id, different drones
    shared_operator_id = generate_operator_id()
    pilot_lat, pilot_lon = random_walk_gps(kit_lat, kit_lon, 2.0)

    print(f"Operator ID reuse: {shared_operator_id}")
    print(f"  Pilot location: ({pilot_lat:.4f}, {pilot_lon:.4f})")

    for i in range(3):
        drone_id = generate_drone_id()
        make, model = random.choice(DRONE_MAKES_MODELS)

        # Different time slots
        start_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(2, 20))
        flight_duration = timedelta(minutes=random.randint(10, 20))

        print(f"  Drone {i+1}: {drone_id} ({make} {model}) at {start_time.strftime('%H:%M')}")

        current_time = start_time
        while current_time < start_time + flight_duration:
            drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.3)

            drone_batch.append({
                "time": current_time,
                "kit_id": kit_id,
                "drone_id": drone_id,
                "lat": round(drone_lat, 6),
                "lon": round(drone_lon, 6),
                "alt": round(random.uniform(50, 100), 1),
                "speed": round(random.uniform(5, 15), 1),
                "heading": round(random.uniform(0, 360), 1),
                "pilot_lat": round(pilot_lat, 6),
                "pilot_lon": round(pilot_lon, 6),
                "home_lat": round(pilot_lat, 6),
                "home_lon": round(pilot_lon, 6),
                "mac": generate_mac(),
                "rssi": random.randint(-80, -50),
                "freq": 5800.0,
                "ua_type": "Helicopter/Multirotor",
                "operator_id": shared_operator_id,  # SAME OPERATOR
                "caa_id": "",
                "rid_make": make,
                "rid_model": model,
                "rid_source": random.choice(["wifi", "ble", "dji"]),
                "track_type": "drone",
            })

            current_time += timedelta(seconds=5)

    # Scenario B: Different operators, pilots within 50m
    base_pilot_lat, base_pilot_lon = random_walk_gps(kit_lat, kit_lon, 2.0)

    print(f"\nPilot proximity pattern:")
    print(f"  Base location: ({base_pilot_lat:.4f}, {base_pilot_lon:.4f})")

    for i in range(3):
        # Pilots within 50m (0.05km)
        pilot_lat, pilot_lon = random_walk_gps(base_pilot_lat, base_pilot_lon, 0.05)
        dist = distance_km(base_pilot_lat, base_pilot_lon, pilot_lat, pilot_lon)

        drone_id = generate_drone_id()
        operator_id = generate_operator_id()
        make, model = random.choice(DRONE_MAKES_MODELS)

        start_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 12))
        flight_duration = timedelta(minutes=random.randint(10, 20))

        print(f"  Pilot {i+1}: {int(dist * 1000)}m away, Drone {drone_id} ({make} {model})")

        current_time = start_time
        while current_time < start_time + flight_duration:
            drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.3)

            drone_batch.append({
                "time": current_time,
                "kit_id": kit_id,
                "drone_id": drone_id,
                "lat": round(drone_lat, 6),
                "lon": round(drone_lon, 6),
                "alt": round(random.uniform(50, 100), 1),
                "speed": round(random.uniform(5, 15), 1),
                "heading": round(random.uniform(0, 360), 1),
                "pilot_lat": round(pilot_lat, 6),
                "pilot_lon": round(pilot_lon, 6),
                "home_lat": round(pilot_lat, 6),
                "home_lon": round(pilot_lon, 6),
                "mac": generate_mac(),
                "rssi": random.randint(-80, -50),
                "freq": 5800.0,
                "ua_type": "Helicopter/Multirotor",
                "operator_id": operator_id,
                "caa_id": "",
                "rid_make": make,
                "rid_model": model,
                "rid_source": random.choice(["wifi", "ble", "dji"]),
                "track_type": "drone",
            })

            current_time += timedelta(seconds=5)

    stats["drones"] = insert_drones_batch(conn, drone_batch, dry_run)
    print(f"\nGenerated {stats['drones']} drone records demonstrating operator reuse")

    return stats


def scenario_multi_kit_detections(conn, dry_run: bool = False) -> Dict[str, int]:
    """
    Multi-kit detections (triangulation):
    - Same drone seen by 2-3 kits simultaneously
    - Different RSSI values based on distance
    """
    print("\n=== Scenario: Multi-Kit Detections (Triangulation) ===\n")

    stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

    # Create 3 kits in triangular formation
    kits = []
    kit_locations = []
    for i in range(3):
        kit_id = f"test-kit-{i+1:03d}"
        # Spread kits 5km apart
        angle = (i * 120) * math.pi / 180  # 120 degrees apart
        kit_lat = BASE_LAT + (5.0 / 111.0) * math.cos(angle)
        kit_lon = BASE_LON + (5.0 / (111.0 * math.cos(math.radians(BASE_LAT)))) * math.sin(angle)

        kits.append({
            "kit_id": kit_id,
            "name": f"Test Kit {i+1}",
            "location": f"Test Location {i+1}",
            "api_url": f"http://192.168.1.{100+i}:8088",
            "last_seen": datetime.now(timezone.utc),
            "status": "online",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=48),
        })
        kit_locations.append((kit_lat, kit_lon))

        print(f"Kit {i+1}: ({kit_lat:.4f}, {kit_lon:.4f})")

    stats["kits"] = upsert_kits(conn, kits, dry_run)

    drone_batch = []

    # Generate drones that are visible to multiple kits
    num_drones = 5

    for _ in range(num_drones):
        drone_id = generate_drone_id()
        make, model = random.choice(DRONE_MAKES_MODELS)
        operator_id = generate_operator_id()

        # Position drone in center area (visible to all kits)
        pilot_lat, pilot_lon = random_walk_gps(BASE_LAT, BASE_LON, 1.0)

        start_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 12))
        flight_duration = timedelta(minutes=random.randint(10, 20))

        print(f"\nDrone {drone_id} at ({pilot_lat:.4f}, {pilot_lon:.4f})")

        current_time = start_time
        while current_time < start_time + flight_duration:
            drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.5)

            # Generate detection from each kit
            for kit_idx, kit in enumerate(kits):
                kit_lat, kit_lon = kit_locations[kit_idx]

                # Calculate distance from kit to drone
                dist_km = distance_km(kit_lat, kit_lon, drone_lat, drone_lon)

                # RSSI decreases with distance (rough model)
                rssi_base = -50
                rssi = int(rssi_base - (dist_km * 10))  # -10 dB per km
                rssi = max(rssi, -95)  # Floor at -95

                # Only detect if RSSI > -90 (within ~4km)
                if rssi > -90:
                    drone_batch.append({
                        "time": current_time,
                        "kit_id": kit["kit_id"],
                        "drone_id": drone_id,
                        "lat": round(drone_lat, 6),
                        "lon": round(drone_lon, 6),
                        "alt": round(random.uniform(60, 120), 1),
                        "speed": round(random.uniform(5, 15), 1),
                        "heading": round(random.uniform(0, 360), 1),
                        "pilot_lat": round(pilot_lat, 6),
                        "pilot_lon": round(pilot_lon, 6),
                        "home_lat": round(pilot_lat, 6),
                        "home_lon": round(pilot_lon, 6),
                        "mac": generate_mac(),
                        "rssi": rssi,
                        "freq": 5800.0,
                        "ua_type": "Helicopter/Multirotor",
                        "operator_id": operator_id,
                        "caa_id": "",
                        "rid_make": make,
                        "rid_model": model,
                        "rid_source": "dji",
                        "track_type": "drone",
                    })

            current_time += timedelta(seconds=5)

    stats["drones"] = insert_drones_batch(conn, drone_batch, dry_run)
    print(f"\nGenerated {stats['drones']} drone records for multi-kit detection")

    return stats


def scenario_anomalies(conn, dry_run: bool = False) -> Dict[str, int]:
    """
    Anomalous behavior:
    - Speed spike (0 to 40m/s in 10s)
    - Rapid altitude change (100m to 10m in 20s)
    - Erratic direction changes
    """
    print("\n=== Scenario: Anomalous Behavior ===\n")

    stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

    # Create kit
    kit_id = "test-kit-001"
    kit_lat, kit_lon = random_walk_gps(BASE_LAT, BASE_LON, 5.0)

    kits = [{
        "kit_id": kit_id,
        "name": "Test Kit 1",
        "location": "Test Location 1",
        "api_url": "http://192.168.1.100:8088",
        "last_seen": datetime.now(timezone.utc),
        "status": "online",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=48),
    }]

    stats["kits"] = upsert_kits(conn, kits, dry_run)

    drone_batch = []

    # Anomaly 1: Speed spike
    print("Anomaly 1: Speed spike (0 to 40m/s in 10 seconds)")
    drone_id = f"ANOMALY-SPEED-{random.randint(1000, 9999)}"
    make, model = random.choice(DRONE_MAKES_MODELS)
    operator_id = generate_operator_id()
    pilot_lat, pilot_lon = random_walk_gps(kit_lat, kit_lon, 2.0)

    start_time = datetime.now(timezone.utc) - timedelta(hours=2)

    # Normal flight, then speed spike
    for i in range(30):  # 30 * 5s = 150 seconds
        current_time = start_time + timedelta(seconds=i * 5)
        drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.3)

        # Speed spike at 60 seconds (i=12) lasting 10 seconds
        if 12 <= i <= 14:
            speed = 40 + random.uniform(-2, 2)  # ANOMALY: Very high speed
        else:
            speed = random.uniform(5, 12)  # Normal speed

        drone_batch.append({
            "time": current_time,
            "kit_id": kit_id,
            "drone_id": drone_id,
            "lat": round(drone_lat, 6),
            "lon": round(drone_lon, 6),
            "alt": round(random.uniform(80, 100), 1),
            "speed": round(speed, 1),
            "heading": round(random.uniform(0, 360), 1),
            "pilot_lat": round(pilot_lat, 6),
            "pilot_lon": round(pilot_lon, 6),
            "home_lat": round(pilot_lat, 6),
            "home_lon": round(pilot_lon, 6),
            "mac": generate_mac(),
            "rssi": random.randint(-80, -50),
            "freq": 5800.0,
            "ua_type": "Helicopter/Multirotor",
            "operator_id": operator_id,
            "caa_id": "",
            "rid_make": make,
            "rid_model": model,
            "rid_source": "dji",
            "track_type": "drone",
        })

    # Anomaly 2: Rapid altitude drop
    print("Anomaly 2: Rapid altitude drop (100m to 10m in 20 seconds)")
    drone_id = f"ANOMALY-ALT-{random.randint(1000, 9999)}"
    make, model = random.choice(DRONE_MAKES_MODELS)
    operator_id = generate_operator_id()
    pilot_lat, pilot_lon = random_walk_gps(kit_lat, kit_lon, 2.0)

    start_time = datetime.now(timezone.utc) - timedelta(hours=3)

    for i in range(30):
        current_time = start_time + timedelta(seconds=i * 5)
        drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.3)

        # Altitude drop at 60 seconds (i=12) lasting 20 seconds
        if i < 12:
            alt = random.uniform(95, 105)  # Normal high altitude
        elif 12 <= i <= 16:
            # Linear drop from 100 to 10 over 20 seconds
            progress = (i - 12) / 4.0
            alt = 100 - (90 * progress)  # ANOMALY: Rapid descent
        else:
            alt = random.uniform(8, 12)  # Low altitude after drop

        drone_batch.append({
            "time": current_time,
            "kit_id": kit_id,
            "drone_id": drone_id,
            "lat": round(drone_lat, 6),
            "lon": round(drone_lon, 6),
            "alt": round(alt, 1),
            "speed": round(random.uniform(5, 12), 1),
            "heading": round(random.uniform(0, 360), 1),
            "pilot_lat": round(pilot_lat, 6),
            "pilot_lon": round(pilot_lon, 6),
            "home_lat": round(pilot_lat, 6),
            "home_lon": round(pilot_lon, 6),
            "mac": generate_mac(),
            "rssi": random.randint(-80, -50),
            "freq": 5800.0,
            "ua_type": "Helicopter/Multirotor",
            "operator_id": operator_id,
            "caa_id": "",
            "rid_make": make,
            "rid_model": model,
            "rid_source": "dji",
            "track_type": "drone",
        })

    # Anomaly 3: Erratic direction changes
    print("Anomaly 3: Erratic direction changes")
    drone_id = f"ANOMALY-HEADING-{random.randint(1000, 9999)}"
    make, model = random.choice(DRONE_MAKES_MODELS)
    operator_id = generate_operator_id()
    pilot_lat, pilot_lon = random_walk_gps(kit_lat, kit_lon, 2.0)

    start_time = datetime.now(timezone.utc) - timedelta(hours=1)

    for i in range(30):
        current_time = start_time + timedelta(seconds=i * 5)
        drone_lat, drone_lon = random_walk_gps(pilot_lat, pilot_lon, 0.3)

        # Erratic heading changes every 5 seconds starting at i=10
        if i >= 10:
            heading = random.uniform(0, 360)  # ANOMALY: Completely random heading
        else:
            heading = 90 + random.uniform(-10, 10)  # Normal: roughly eastward

        drone_batch.append({
            "time": current_time,
            "kit_id": kit_id,
            "drone_id": drone_id,
            "lat": round(drone_lat, 6),
            "lon": round(drone_lon, 6),
            "alt": round(random.uniform(70, 90), 1),
            "speed": round(random.uniform(5, 12), 1),
            "heading": round(heading, 1),
            "pilot_lat": round(pilot_lat, 6),
            "pilot_lon": round(pilot_lon, 6),
            "home_lat": round(pilot_lat, 6),
            "home_lon": round(pilot_lon, 6),
            "mac": generate_mac(),
            "rssi": random.randint(-80, -50),
            "freq": 5800.0,
            "ua_type": "Helicopter/Multirotor",
            "operator_id": operator_id,
            "caa_id": "",
            "rid_make": make,
            "rid_model": model,
            "rid_source": "dji",
            "track_type": "drone",
        })

    stats["drones"] = insert_drones_batch(conn, drone_batch, dry_run)
    print(f"\nGenerated {stats['drones']} drone records with anomalous behavior")

    return stats


def scenario_fpv_signals(conn, dry_run: bool = False) -> Dict[str, int]:
    """
    FPV signal detections:
    - 5.8GHz signals at known frequencies
    - Power levels -60 to -90 dBm
    - Intermittent detections
    """
    print("\n=== Scenario: FPV Signal Detections ===\n")

    stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

    # Create kit
    kit_id = "test-kit-001"
    kit_lat, kit_lon = random_walk_gps(BASE_LAT, BASE_LON, 5.0)

    kits = [{
        "kit_id": kit_id,
        "name": "Test Kit 1",
        "location": "Test Location 1",
        "api_url": "http://192.168.1.100:8088",
        "last_seen": datetime.now(timezone.utc),
        "status": "online",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=48),
    }]

    stats["kits"] = upsert_kits(conn, kits, dry_run)

    signal_batch = []

    # Generate FPV signals over last 6 hours
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=6)

    # Common FPV frequencies
    frequencies = FPV_FREQUENCIES["analog"][:6]  # Use 6 common frequencies

    print(f"Generating FPV signals on frequencies: {frequencies}")

    current_time = start_time
    while current_time <= end_time:
        # Intermittent detection (30% probability per interval)
        if random.random() < 0.3:
            # Random frequency
            freq = random.choice(frequencies)
            detection_type = random.choice(["analog", "dji"])

            signal_batch.append({
                "time": current_time,
                "kit_id": kit_id,
                "freq_mhz": freq,
                "power_dbm": round(random.uniform(-90, -60), 1),
                "bandwidth_mhz": 20.0 if detection_type == "dji" else 8.0,
                "lat": kit_lat,
                "lon": kit_lon,
                "alt": random.uniform(10, 50),
                "detection_type": detection_type,
            })

        current_time += timedelta(seconds=10)  # Check every 10 seconds

    stats["signals"] = insert_signals_batch(conn, signal_batch, dry_run)
    print(f"Generated {stats['signals']} FPV signal records")

    return stats


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Phase 2 Test Data Generator for WarDragon Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all scenarios
  python tests/generate_test_data.py --scenario all

  # Generate specific scenario
  python tests/generate_test_data.py --scenario coordinated --count 5

  # Generate repeated drone pattern
  python tests/generate_test_data.py --scenario repeated --drone-id SURVEILLANCE-12345 --count 5

  # Clean all test data
  python tests/generate_test_data.py --clean

  # Dry run (preview without inserting)
  python tests/generate_test_data.py --scenario normal --dry-run

  # Custom database URL
  python tests/generate_test_data.py --scenario all --db-url "postgresql://user:pass@localhost/wardragon"

Scenarios:
  normal         - Normal operations baseline (3 kits, 20-30 drones, 48 hours)
  repeated       - Repeated drone pattern (surveillance, same drone multiple times)
  coordinated    - Coordinated activity (swarms, 4-6 drones together)
  operator       - Operator reuse (same operator/pilot, different drones)
  multikit       - Multi-kit detections (triangulation opportunities)
  anomalies      - Anomalous behavior (speed/altitude spikes)
  fpv            - FPV signal detections (5.8GHz signals)
  all            - Run all scenarios
        """
    )

    parser.add_argument(
        "--scenario",
        choices=["all", "normal", "repeated", "coordinated", "operator", "multikit", "anomalies", "fpv"],
        required=False,
        help="Scenario to generate"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Count parameter for scenarios (e.g., number of appearances, swarms)"
    )

    parser.add_argument(
        "--drone-id",
        type=str,
        help="Specific drone ID for repeated scenario"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean all test data from database"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without inserting data"
    )

    parser.add_argument(
        "--db-url",
        type=str,
        help="Database URL (default: from DATABASE_URL env or localhost)"
    )

    args = parser.parse_args()

    # Validate
    if not args.scenario and not args.clean:
        parser.error("Must specify --scenario or --clean")

    if not DB_AVAILABLE:
        print("Error: psycopg2 not installed. Install with: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    # Connect to database
    try:
        conn = get_db_connection(args.db_url)
        print(f"Connected to database")

        if args.clean:
            clean_test_data(conn, args.dry_run)
            conn.close()
            return

        # Run scenarios
        total_stats = {"kits": 0, "drones": 0, "signals": 0, "health": 0}

        scenarios_to_run = []
        if args.scenario == "all":
            scenarios_to_run = [
                ("normal", {}),
                ("repeated", {"count": args.count, "drone_id": args.drone_id}),
                ("coordinated", {"count": 3}),
                ("operator", {}),
                ("multikit", {}),
                ("anomalies", {}),
                ("fpv", {}),
            ]
        else:
            scenarios_to_run = [(args.scenario, {"count": args.count, "drone_id": args.drone_id})]

        for scenario_name, scenario_args in scenarios_to_run:
            try:
                if scenario_name == "normal":
                    stats = scenario_normal(conn, args.dry_run)
                elif scenario_name == "repeated":
                    stats = scenario_repeated_drone(conn, scenario_args.get("drone_id"), scenario_args.get("count"), args.dry_run)
                elif scenario_name == "coordinated":
                    stats = scenario_coordinated_activity(conn, scenario_args.get("count"), args.dry_run)
                elif scenario_name == "operator":
                    stats = scenario_operator_reuse(conn, args.dry_run)
                elif scenario_name == "multikit":
                    stats = scenario_multi_kit_detections(conn, args.dry_run)
                elif scenario_name == "anomalies":
                    stats = scenario_anomalies(conn, args.dry_run)
                elif scenario_name == "fpv":
                    stats = scenario_fpv_signals(conn, args.dry_run)

                # Accumulate stats
                for key in total_stats:
                    total_stats[key] += stats.get(key, 0)

            except Exception as e:
                print(f"\nError in scenario '{scenario_name}': {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()

        conn.close()

        # Summary
        print("\n" + "="*60)
        print("GENERATION COMPLETE")
        print("="*60)
        print(f"Kits:          {total_stats['kits']}")
        print(f"Drone records: {total_stats['drones']}")
        print(f"Signal records: {total_stats['signals']}")
        print(f"Health records: {total_stats['health']}")
        print(f"Total records: {total_stats['drones'] + total_stats['signals'] + total_stats['health']}")
        print("="*60)

        if args.dry_run:
            print("\n[DRY RUN] No data was actually inserted")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
