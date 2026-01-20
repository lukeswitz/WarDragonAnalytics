#!/usr/bin/env python3
"""
WarDragon Analytics FastAPI Web Application

Provides REST API and web UI for multi-kit drone surveillance visualization.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncpg
import csv
import io

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://wardragon:wardragon@timescaledb:5432/wardragon"
)
API_TITLE = os.environ.get("API_TITLE", "WarDragon Analytics API")
API_VERSION = os.environ.get("API_VERSION", "1.0.0")
MAX_QUERY_RANGE_HOURS = int(os.environ.get("MAX_QUERY_RANGE_HOURS", "168"))  # 7 days default

# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="Multi-kit drone surveillance aggregation and visualization"
)

# Mount static files directory
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Mounted static files from {static_dir}")

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


# Pydantic models
class KitStatus(BaseModel):
    kit_id: str
    name: str
    location: Optional[str]
    api_url: str
    last_seen: Optional[datetime]
    status: str  # online, offline, stale


class DroneTrack(BaseModel):
    time: datetime
    kit_id: str
    drone_id: str
    lat: Optional[float]
    lon: Optional[float]
    alt: Optional[float]
    speed: Optional[float]
    heading: Optional[float]
    pilot_lat: Optional[float]
    pilot_lon: Optional[float]
    home_lat: Optional[float]
    home_lon: Optional[float]
    mac: Optional[str]
    rssi: Optional[int]
    freq: Optional[float]
    ua_type: Optional[str]
    operator_id: Optional[str]
    caa_id: Optional[str]
    rid_make: Optional[str]
    rid_model: Optional[str]
    rid_source: Optional[str]
    track_type: Optional[str]


class SignalDetection(BaseModel):
    time: datetime
    kit_id: str
    freq_mhz: float
    power_dbm: Optional[float]
    bandwidth_mhz: Optional[float]
    lat: Optional[float]
    lon: Optional[float]
    alt: Optional[float]
    detection_type: Optional[str]


# Pattern detection models
class DroneLocation(BaseModel):
    lat: float
    lon: float
    kit_id: str
    timestamp: datetime


class RepeatedDrone(BaseModel):
    drone_id: str
    first_seen: datetime
    last_seen: datetime
    appearance_count: int
    locations: List[DroneLocation]


class CoordinatedDrone(BaseModel):
    drone_id: str
    lat: float
    lon: float
    timestamp: datetime
    kit_id: Optional[str]
    rid_make: Optional[str]


class CoordinatedGroup(BaseModel):
    group_id: int
    drone_count: int
    drones: List[dict]
    correlation_score: str


class PilotReuse(BaseModel):
    pilot_identifier: str
    drones: List[dict]
    correlation_method: str


class Anomaly(BaseModel):
    anomaly_type: str
    severity: str
    drone_id: str
    details: dict
    timestamp: datetime


class MultiKitDetection(BaseModel):
    drone_id: str
    kits: List[dict]
    triangulation_possible: bool


# Startup/Shutdown events
@app.on_event("startup")
async def startup():
    """Initialize database connection pool on startup."""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    """Close database connection pool on shutdown."""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")


# Helper functions
def parse_time_range(time_range: str) -> tuple[datetime, datetime]:
    """Parse time_range parameter into start and end datetimes."""
    now = datetime.utcnow()

    if time_range == "1h":
        start_time = now - timedelta(hours=1)
    elif time_range == "24h":
        start_time = now - timedelta(hours=24)
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
    elif time_range.startswith("custom:"):
        # Format: custom:YYYY-MM-DDTHH:MM:SS,YYYY-MM-DDTHH:MM:SS
        try:
            _, times = time_range.split(":", 1)
            start_str, end_str = times.split(",", 1)
            start_time = datetime.fromisoformat(start_str)
            end_time = datetime.fromisoformat(end_str)
            return start_time, end_time
        except Exception as e:
            logger.warning(f"Invalid custom time range format: {time_range}, error: {e}")
            start_time = now - timedelta(hours=1)
    else:
        start_time = now - timedelta(hours=1)

    # Enforce max query range
    max_range = timedelta(hours=MAX_QUERY_RANGE_HOURS)
    if now - start_time > max_range:
        start_time = now - max_range

    return start_time, now


async def get_kit_status(kit_id: Optional[str] = None) -> List[dict]:
    """Get status of configured kits."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with db_pool.acquire() as conn:
        if kit_id:
            query = """
                SELECT kit_id, name, location, api_url, last_seen, status, created_at
                FROM kits
                WHERE kit_id = $1
            """
            rows = await conn.fetch(query, kit_id)
        else:
            query = """
                SELECT kit_id, name, location, api_url, last_seen, status, created_at
                FROM kits
                ORDER BY name
            """
            rows = await conn.fetch(query)

        # Calculate status based on last_seen
        kits = []
        for row in rows:
            kit = dict(row)
            if kit["last_seen"]:
                time_since_seen = (datetime.utcnow() - kit["last_seen"]).total_seconds()
                if time_since_seen < 30:
                    kit["status"] = "online"
                elif time_since_seen < 120:
                    kit["status"] = "stale"
                else:
                    kit["status"] = "offline"
            else:
                kit["status"] = "unknown"
            kits.append(kit)

        return kits


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker healthcheck."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database pool not initialized")

    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")


@app.get("/api/kits")
async def list_kits(kit_id: Optional[str] = Query(None, description="Filter by specific kit ID")):
    """
    List all configured kits with their status.

    Returns:
        List of kit objects with status, last seen time, etc.
    """
    try:
        kits = await get_kit_status(kit_id)
        return {"kits": kits, "count": len(kits)}
    except Exception as e:
        logger.error(f"Failed to list kits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/drones")
async def query_drones(
    time_range: str = Query("1h", description="Time range: 1h, 24h, 7d, or custom:START,END"),
    kit_id: Optional[str] = Query(None, description="Filter by kit ID (comma-separated for multiple)"),
    rid_make: Optional[str] = Query(None, description="Filter by RID make (e.g., DJI, Autel)"),
    track_type: Optional[str] = Query(None, description="Filter by track type: drone or aircraft"),
    limit: int = Query(1000, description="Maximum number of results", le=10000)
):
    """
    Query drone/aircraft tracks with filters.

    Returns:
        List of drone tracks matching the filter criteria.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        start_time, end_time = parse_time_range(time_range)

        # Build query
        query = """
            SELECT
                time, kit_id, drone_id, lat, lon, alt, speed, heading,
                pilot_lat, pilot_lon, home_lat, home_lon, mac, rssi, freq,
                ua_type, operator_id, caa_id, rid_make, rid_model, rid_source, track_type
            FROM drones
            WHERE time >= $1 AND time <= $2
        """
        params = [start_time, end_time]
        param_counter = 3

        # Add kit_id filter
        if kit_id:
            kit_ids = [k.strip() for k in kit_id.split(",")]
            query += f" AND kit_id = ANY(${param_counter})"
            params.append(kit_ids)
            param_counter += 1

        # Add rid_make filter
        if rid_make:
            query += f" AND rid_make = ${param_counter}"
            params.append(rid_make)
            param_counter += 1

        # Add track_type filter
        if track_type:
            query += f" AND track_type = ${param_counter}"
            params.append(track_type)
            param_counter += 1

        query += f" ORDER BY time DESC LIMIT ${param_counter}"
        params.append(limit)

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        drones = [dict(row) for row in rows]

        return {
            "drones": drones,
            "count": len(drones),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to query drones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals")
async def query_signals(
    time_range: str = Query("1h", description="Time range: 1h, 24h, 7d, or custom:START,END"),
    kit_id: Optional[str] = Query(None, description="Filter by kit ID (comma-separated for multiple)"),
    detection_type: Optional[str] = Query(None, description="Filter by detection type: analog or dji"),
    limit: int = Query(1000, description="Maximum number of results", le=10000)
):
    """
    Query FPV signal detections with filters.

    Returns:
        List of signal detections matching the filter criteria.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        start_time, end_time = parse_time_range(time_range)

        # Build query
        query = """
            SELECT
                time, kit_id, freq_mhz, power_dbm, bandwidth_mhz,
                lat, lon, alt, detection_type
            FROM signals
            WHERE time >= $1 AND time <= $2
        """
        params = [start_time, end_time]
        param_counter = 3

        # Add kit_id filter
        if kit_id:
            kit_ids = [k.strip() for k in kit_id.split(",")]
            query += f" AND kit_id = ANY(${param_counter})"
            params.append(kit_ids)
            param_counter += 1

        # Add detection_type filter
        if detection_type:
            query += f" AND detection_type = ${param_counter}"
            params.append(detection_type)
            param_counter += 1

        query += f" ORDER BY time DESC LIMIT ${param_counter}"
        params.append(limit)

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        signals = [dict(row) for row in rows]

        return {
            "signals": signals,
            "count": len(signals),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to query signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/csv")
async def export_csv(
    time_range: str = Query("1h", description="Time range: 1h, 24h, 7d, or custom:START,END"),
    kit_id: Optional[str] = Query(None, description="Filter by kit ID (comma-separated for multiple)"),
    rid_make: Optional[str] = Query(None, description="Filter by RID make"),
    track_type: Optional[str] = Query(None, description="Filter by track type: drone or aircraft")
):
    """
    Export drones to CSV format.

    Returns:
        CSV file with drone tracks.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        start_time, end_time = parse_time_range(time_range)

        # Build query (same as /api/drones but without limit)
        query = """
            SELECT
                time, kit_id, drone_id, lat, lon, alt, speed, heading,
                pilot_lat, pilot_lon, home_lat, home_lon, mac, rssi, freq,
                ua_type, operator_id, caa_id, rid_make, rid_model, rid_source, track_type
            FROM drones
            WHERE time >= $1 AND time <= $2
        """
        params = [start_time, end_time]
        param_counter = 3

        if kit_id:
            kit_ids = [k.strip() for k in kit_id.split(",")]
            query += f" AND kit_id = ANY(${param_counter})"
            params.append(kit_ids)
            param_counter += 1

        if rid_make:
            query += f" AND rid_make = ${param_counter}"
            params.append(rid_make)
            param_counter += 1

        if track_type:
            query += f" AND track_type = ${param_counter}"
            params.append(track_type)
            param_counter += 1

        query += " ORDER BY time DESC"

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Generate CSV
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        csv_content = output.getvalue()
        output.close()

        # Return as downloadable file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"wardragon_drones_{timestamp}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patterns/repeated-drones")
async def get_repeated_drones(
    time_window_hours: int = Query(24, description="Time window in hours", ge=1, le=168),
    min_appearances: int = Query(2, description="Minimum number of appearances", ge=2)
):
    """
    Find drones seen multiple times within the time window.

    Returns:
        List of drones with multiple appearances, including all locations.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        query = """
            WITH recent_drones AS (
                SELECT
                    drone_id,
                    time,
                    kit_id,
                    lat,
                    lon
                FROM drones
                WHERE time >= NOW() - ($1 || ' hours')::INTERVAL
                    AND lat IS NOT NULL
                    AND lon IS NOT NULL
            ),
            drone_counts AS (
                SELECT
                    drone_id,
                    COUNT(*) AS appearance_count,
                    MIN(time) AS first_seen,
                    MAX(time) AS last_seen
                FROM recent_drones
                GROUP BY drone_id
                HAVING COUNT(*) >= $2
            )
            SELECT
                dc.drone_id,
                dc.first_seen,
                dc.last_seen,
                dc.appearance_count,
                json_agg(
                    json_build_object(
                        'lat', rd.lat,
                        'lon', rd.lon,
                        'kit_id', rd.kit_id,
                        'timestamp', rd.time
                    ) ORDER BY rd.time
                ) AS locations
            FROM drone_counts dc
            JOIN recent_drones rd ON dc.drone_id = rd.drone_id
            GROUP BY dc.drone_id, dc.first_seen, dc.last_seen, dc.appearance_count
            ORDER BY dc.appearance_count DESC, dc.last_seen DESC
            LIMIT 100
        """

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, time_window_hours, min_appearances)

        results = [dict(row) for row in rows]

        return {
            "repeated_drones": results,
            "count": len(results),
            "time_window_hours": time_window_hours,
            "min_appearances": min_appearances
        }

    except Exception as e:
        logger.error(f"Failed to query repeated drones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patterns/coordinated")
async def get_coordinated_drones(
    time_window_minutes: int = Query(60, description="Time window in minutes", ge=1, le=1440),
    distance_threshold_m: float = Query(500, description="Distance threshold in meters", ge=10)
):
    """
    Detect coordinated drone activity using time and location clustering.

    Returns:
        Groups of drones appearing together in time and space.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Use the database function for coordinated activity detection
        query = "SELECT detect_coordinated_activity($1, $2) AS groups"

        async with db_pool.acquire() as conn:
            result = await conn.fetchval(query, time_window_minutes, distance_threshold_m)

        # Parse JSON result
        import json
        groups = json.loads(result) if result else []

        return {
            "coordinated_groups": groups,
            "count": len(groups),
            "time_window_minutes": time_window_minutes,
            "distance_threshold_m": distance_threshold_m
        }

    except Exception as e:
        logger.error(f"Failed to detect coordinated activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patterns/pilot-reuse")
async def get_pilot_reuse(
    time_window_hours: int = Query(24, description="Time window in hours", ge=1, le=168),
    proximity_threshold_m: float = Query(50, description="Proximity threshold in meters", ge=10)
):
    """
    Find potential operator reuse across different drone IDs.

    Uses two methods:
    1. Exact operator_id matches
    2. Pilot locations within proximity threshold

    Returns:
        List of operators/locations with associated drones.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Method 1: Exact operator_id matches
        operator_query = """
            WITH recent_drones AS (
                SELECT
                    drone_id,
                    operator_id,
                    time,
                    pilot_lat,
                    pilot_lon
                FROM drones
                WHERE time >= NOW() - ($1 || ' hours')::INTERVAL
                    AND operator_id IS NOT NULL
            )
            SELECT
                operator_id AS pilot_identifier,
                'operator_id' AS correlation_method,
                json_agg(
                    json_build_object(
                        'drone_id', drone_id,
                        'timestamp', time,
                        'pilot_lat', pilot_lat,
                        'pilot_lon', pilot_lon
                    ) ORDER BY time DESC
                ) AS drones,
                COUNT(DISTINCT drone_id) AS drone_count
            FROM recent_drones
            GROUP BY operator_id
            HAVING COUNT(DISTINCT drone_id) >= 2
            ORDER BY drone_count DESC
        """

        # Method 2: Proximity-based clustering
        proximity_query = """
            WITH recent_pilots AS (
                SELECT DISTINCT ON (drone_id)
                    drone_id,
                    pilot_lat,
                    pilot_lon,
                    time
                FROM drones
                WHERE time >= NOW() - ($1 || ' hours')::INTERVAL
                    AND pilot_lat IS NOT NULL
                    AND pilot_lon IS NOT NULL
                    AND operator_id IS NULL
                ORDER BY drone_id, time DESC
            ),
            pilot_pairs AS (
                SELECT
                    p1.drone_id AS drone1_id,
                    p2.drone_id AS drone2_id,
                    p1.pilot_lat AS pilot1_lat,
                    p1.pilot_lon AS pilot1_lon,
                    calculate_distance_m(p1.pilot_lat, p1.pilot_lon, p2.pilot_lat, p2.pilot_lon) AS distance_m
                FROM recent_pilots p1
                CROSS JOIN recent_pilots p2
                WHERE p1.drone_id < p2.drone_id
                    AND calculate_distance_m(p1.pilot_lat, p1.pilot_lon, p2.pilot_lat, p2.pilot_lon) <= $2
            )
            SELECT
                CONCAT('PILOT_', ROUND(AVG(rp.pilot_lat)::numeric, 4), '_', ROUND(AVG(rp.pilot_lon)::numeric, 4)) AS pilot_identifier,
                'proximity' AS correlation_method,
                json_agg(
                    json_build_object(
                        'drone_id', rp.drone_id,
                        'timestamp', rp.time,
                        'pilot_lat', rp.pilot_lat,
                        'pilot_lon', rp.pilot_lon
                    ) ORDER BY rp.time DESC
                ) AS drones,
                COUNT(DISTINCT rp.drone_id) AS drone_count
            FROM pilot_pairs pp
            JOIN recent_pilots rp ON rp.drone_id = pp.drone1_id OR rp.drone_id = pp.drone2_id
            GROUP BY pp.drone1_id
            HAVING COUNT(DISTINCT rp.drone_id) >= 2
            ORDER BY drone_count DESC
        """

        async with db_pool.acquire() as conn:
            operator_rows = await conn.fetch(operator_query, time_window_hours)
            proximity_rows = await conn.fetch(proximity_query, time_window_hours, proximity_threshold_m)

        results = [dict(row) for row in operator_rows] + [dict(row) for row in proximity_rows]

        return {
            "pilot_reuse": results,
            "count": len(results),
            "time_window_hours": time_window_hours,
            "proximity_threshold_m": proximity_threshold_m
        }

    except Exception as e:
        logger.error(f"Failed to detect pilot reuse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patterns/anomalies")
async def get_anomalies(
    time_window_hours: int = Query(1, description="Time window in hours", ge=1, le=24)
):
    """
    Detect anomalous drone behavior.

    Detects:
    - Speed anomalies (>30 m/s)
    - Altitude anomalies (>400m for drones)
    - Rapid altitude changes (>50m in 10 seconds)
    - Multiple appearances (repeated sightings)

    Returns:
        List of anomalies with type, severity, and details.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        query = """
            WITH recent_drones AS (
                SELECT
                    drone_id,
                    time,
                    kit_id,
                    lat,
                    lon,
                    alt,
                    speed,
                    heading,
                    track_type,
                    rid_make,
                    rid_model,
                    LAG(alt) OVER (PARTITION BY drone_id ORDER BY time) AS prev_alt,
                    LAG(time) OVER (PARTITION BY drone_id ORDER BY time) AS prev_time
                FROM drones
                WHERE time >= NOW() - ($1 || ' hours')::INTERVAL
                    AND track_type = 'drone'
            ),
            speed_anomalies AS (
                SELECT
                    'speed' AS anomaly_type,
                    CASE
                        WHEN speed > 50 THEN 'critical'
                        WHEN speed > 40 THEN 'high'
                        ELSE 'medium'
                    END AS severity,
                    drone_id,
                    json_build_object(
                        'speed_ms', speed,
                        'lat', lat,
                        'lon', lon,
                        'kit_id', kit_id,
                        'rid_make', rid_make
                    ) AS details,
                    time AS timestamp
                FROM recent_drones
                WHERE speed > 30
            ),
            altitude_anomalies AS (
                SELECT
                    'altitude' AS anomaly_type,
                    CASE
                        WHEN alt > 500 THEN 'critical'
                        WHEN alt > 450 THEN 'high'
                        ELSE 'medium'
                    END AS severity,
                    drone_id,
                    json_build_object(
                        'altitude_m', alt,
                        'lat', lat,
                        'lon', lon,
                        'kit_id', kit_id,
                        'rid_make', rid_make
                    ) AS details,
                    time AS timestamp
                FROM recent_drones
                WHERE alt > 400
            ),
            rapid_altitude_changes AS (
                SELECT
                    'rapid_altitude_change' AS anomaly_type,
                    CASE
                        WHEN ABS(alt - prev_alt) > 100 THEN 'critical'
                        WHEN ABS(alt - prev_alt) > 75 THEN 'high'
                        ELSE 'medium'
                    END AS severity,
                    drone_id,
                    json_build_object(
                        'altitude_change_m', ABS(alt - prev_alt),
                        'time_diff_seconds', EXTRACT(EPOCH FROM (time - prev_time)),
                        'from_alt', prev_alt,
                        'to_alt', alt,
                        'lat', lat,
                        'lon', lon,
                        'kit_id', kit_id
                    ) AS details,
                    time AS timestamp
                FROM recent_drones
                WHERE prev_alt IS NOT NULL
                    AND prev_time IS NOT NULL
                    AND ABS(alt - prev_alt) > 50
                    AND EXTRACT(EPOCH FROM (time - prev_time)) <= 10
            )
            SELECT * FROM speed_anomalies
            UNION ALL
            SELECT * FROM altitude_anomalies
            UNION ALL
            SELECT * FROM rapid_altitude_changes
            ORDER BY timestamp DESC, severity DESC
            LIMIT 200
        """

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, time_window_hours)

        results = [dict(row) for row in rows]

        return {
            "anomalies": results,
            "count": len(results),
            "time_window_hours": time_window_hours
        }

    except Exception as e:
        logger.error(f"Failed to detect anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patterns/multi-kit")
async def get_multi_kit_detections(
    time_window_minutes: int = Query(15, description="Time window in minutes", ge=1, le=1440)
):
    """
    Find drones detected by multiple kits.

    Useful for triangulation and correlation analysis.

    Returns:
        List of drones with detections from multiple kits.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        query = """
            WITH recent_detections AS (
                SELECT
                    time_bucket($1 || ' minutes', time) AS bucket,
                    drone_id,
                    kit_id,
                    lat,
                    lon,
                    alt,
                    freq,
                    rssi,
                    time,
                    rid_make,
                    rid_model
                FROM drones
                WHERE time >= NOW() - ($1 || ' minutes')::INTERVAL
                    AND lat IS NOT NULL
                    AND lon IS NOT NULL
            ),
            multi_kit_groups AS (
                SELECT
                    drone_id,
                    COUNT(DISTINCT kit_id) AS kit_count,
                    json_agg(
                        json_build_object(
                            'kit_id', kit_id,
                            'rssi', rssi,
                            'freq', freq,
                            'timestamp', time,
                            'lat', lat,
                            'lon', lon,
                            'alt', alt
                        ) ORDER BY rssi DESC
                    ) AS kits,
                    MAX(rid_make) AS rid_make,
                    MAX(rid_model) AS rid_model,
                    MAX(time) AS latest_detection
                FROM recent_detections
                GROUP BY drone_id
                HAVING COUNT(DISTINCT kit_id) >= 2
            )
            SELECT
                drone_id,
                kits,
                (kit_count >= 3) AS triangulation_possible,
                rid_make,
                rid_model,
                latest_detection
            FROM multi_kit_groups
            ORDER BY kit_count DESC, latest_detection DESC
            LIMIT 100
        """

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, time_window_minutes)

        results = [dict(row) for row in rows]

        return {
            "multi_kit_detections": results,
            "count": len(results),
            "time_window_minutes": time_window_minutes
        }

    except Exception as e:
        logger.error(f"Failed to query multi-kit detections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """
    Serve the main web UI with Leaflet map.

    Returns:
        HTML page with embedded map and filters.
    """
    template_path = Path(__file__).parent / "templates" / "index.html"

    if not template_path.exists():
        raise HTTPException(status_code=500, detail="Template not found")

    try:
        with open(template_path, "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Failed to serve UI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
