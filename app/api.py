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
    uvicorn.run(app, host="0.0.0.0", port=8080)
