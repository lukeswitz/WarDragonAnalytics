# Collector Code Reference

Quick reference guide to key components in `app/collector.py`.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Key Classes](#key-classes)
- [Data Flow](#data-flow)
- [Error Handling](#error-handling)
- [Configuration](#configuration)

## Architecture Overview

```
CollectorService
    │
    ├─── Loads kits.yaml
    │
    ├─── Creates DatabaseWriter (connection pool)
    │
    ├─── Creates HTTP Client (httpx.AsyncClient)
    │
    ├─── Spawns KitCollector tasks (one per kit)
    │       │
    │       ├─── Polls /drones endpoint
    │       ├─── Polls /signals endpoint
    │       ├─── Polls /status endpoint
    │       │
    │       └─── Updates KitHealth tracker
    │
    └─── Monitors health (every 60s)
```

## Key Classes

### 1. KitHealth
**Purpose**: Tracks health status and backoff for a single kit

**Key Methods**:
```python
def mark_success(self):
    """Called after successful poll - resets backoff"""
    self.status = 'online'
    self.consecutive_failures = 0
    self.backoff_delay = INITIAL_BACKOFF

def mark_failure(self, error: str):
    """Called after failed poll - calculates exponential backoff"""
    self.consecutive_failures += 1
    self.backoff_delay = min(
        INITIAL_BACKOFF * (2 ** self.consecutive_failures),
        MAX_BACKOFF
    )

def get_next_poll_delay(self) -> float:
    """Returns delay until next poll"""
    if self.status == 'online':
        return 0.0  # Poll immediately
    return self.backoff_delay  # Use exponential backoff
```

**Health States**:
- `unknown` - Initial state
- `online` - Successfully polling
- `offline` - Failed to connect
- `stale` - No data for 60+ seconds
- `error` - Unexpected error

**Backoff Progression**:
```
Failure 1: 5s
Failure 2: 10s  (5 * 2^1)
Failure 3: 20s  (5 * 2^2)
Failure 4: 40s  (5 * 2^3)
Failure 5: 80s  (5 * 2^4)
Failure 6+: 300s (max)
```

### 2. DatabaseWriter
**Purpose**: Manages database connections and writes data

**Key Methods**:
```python
async def insert_drones(self, kit_id: str, drones: List[Dict]) -> int:
    """
    Insert drone records with UPSERT (ON CONFLICT UPDATE)

    Handles:
    - Remote ID drones (DJI, BLE, Wi-Fi)
    - ADS-B aircraft tracks
    - Pilot location, home point
    - RID metadata (make, model, operator_id)
    """

async def insert_signals(self, kit_id: str, signals: List[Dict]) -> int:
    """
    Insert FPV signal detections

    Handles:
    - 5.8GHz analog video
    - DJI digital systems
    - Power levels, bandwidth
    """

async def insert_health(self, kit_id: str, status: Dict) -> bool:
    """
    Insert system health metrics

    Includes:
    - Kit GPS location
    - CPU, memory, disk usage
    - Temperatures (CPU, GPU)
    - Uptime
    """

async def update_kit_status(self, kit_id: str, status: str, last_seen: datetime):
    """Update kit status in kits table"""
```

**Connection Pooling**:
```python
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,          # 10 base connections
    max_overflow=20,       # +20 overflow connections
    pool_pre_ping=True,    # Verify before use
    pool_recycle=3600,     # Recycle after 1 hour
)
```

**Data Normalization**:
```python
def _parse_timestamp(self, ts: Any) -> datetime:
    """Convert various timestamp formats to datetime"""

def _safe_float(self, value: Any) -> Optional[float]:
    """Safely convert to float, return None on error"""

def _safe_int(self, value: Any) -> Optional[int]:
    """Safely convert to int, return None on error"""
```

### 3. KitCollector
**Purpose**: Polls a single kit's DragonSync API

**Key Methods**:
```python
async def fetch_json(self, endpoint: str, retry: int = 0) -> Optional[Dict]:
    """
    Fetch JSON from kit endpoint with retry logic

    Handles:
    - Timeouts (retry up to MAX_RETRIES)
    - HTTP errors (4xx, 5xx)
    - Network errors
    - JSON parsing errors
    """

async def poll_drones(self) -> bool:
    """Poll /drones endpoint and insert to database"""

async def poll_signals(self) -> bool:
    """Poll /signals endpoint and insert to database"""

async def poll_status(self) -> bool:
    """Poll /status endpoint and insert to database"""

async def poll_all_endpoints(self) -> bool:
    """Poll all endpoints concurrently"""
    results = await asyncio.gather(
        self.poll_drones(),
        self.poll_signals(),
        return_exceptions=True
    )

async def run(self):
    """
    Main polling loop

    Flow:
    1. Poll /drones and /signals every 5s
    2. Poll /status every 30s
    3. Update health status
    4. Apply backoff if failed
    5. Wait for next poll or shutdown
    """
```

**Polling Flow**:
```python
while not shutdown_event.is_set():
    # Poll drones and signals
    success = await self.poll_all_endpoints()

    # Poll status less frequently
    status_poll_counter += 1
    if status_poll_counter >= status_interval_cycles:
        status_success = await self.poll_status()
        status_poll_counter = 0

    # Update health
    if success:
        self.health.mark_success()
        delay = POLL_INTERVAL
    else:
        self.health.mark_failure("Failed to fetch data")
        delay = self.health.get_next_poll_delay()

    # Wait for next poll
    await asyncio.sleep(delay)
```

### 4. CollectorService
**Purpose**: Main orchestrator that manages all kit collectors

**Key Methods**:
```python
def load_config(self) -> List[Dict]:
    """Load and validate kits.yaml"""

async def start(self):
    """
    Start the collector service

    Steps:
    1. Load configuration
    2. Initialize database
    3. Create HTTP client pool
    4. Create kit collectors
    5. Start collector tasks
    6. Start health monitoring
    7. Wait for shutdown signal
    """

async def monitor_health(self):
    """
    Log health statistics every 60 seconds

    Output example:
    === Kit Health Status ===
    Kit kit-001: online | Success rate: 98.5% | Requests: 720 (OK: 709, Failed: 11)
    Kit kit-002: offline | Success rate: 0.0% | Requests: 120 (OK: 0, Failed: 120)
      Last error: Request error fetching /drones: Connection refused
    ========================================
    """

async def shutdown(self):
    """Gracefully shutdown the service"""
```

## Data Flow

### 1. Drone Data Flow
```
DragonSync API (/drones)
    │
    ├─ JSON Response: {"drones": [...]}
    │
    ▼
KitCollector.poll_drones()
    │
    ├─ Parse JSON
    ├─ Extract drone array
    │
    ▼
DatabaseWriter.insert_drones()
    │
    ├─ For each drone:
    │   ├─ Parse timestamp
    │   ├─ Determine track_type (drone/aircraft)
    │   ├─ Normalize fields (lat, lon, alt, etc.)
    │   ├─ Safe type conversion (float/int)
    │   └─ UPSERT to drones table
    │
    ▼
TimescaleDB (drones hypertable)
```

**Example Drone Record**:
```json
{
  "drone_id": "DJI_ABC123",
  "lat": 37.7749,
  "lon": -122.4194,
  "alt": 120.5,
  "speed": 15.3,
  "heading": 180.0,
  "pilot_lat": 37.7750,
  "pilot_lon": -122.4195,
  "mac": "AA:BB:CC:DD:EE:FF",
  "rssi": -65,
  "rid_make": "DJI",
  "rid_model": "Mavic 3",
  "operator_id": "FAA123456",
  "track_type": "drone"
}
```

### 2. Signal Data Flow
```
DragonSync API (/signals)
    │
    ├─ JSON Response: {"signals": [...]}
    │
    ▼
KitCollector.poll_signals()
    │
    ├─ Parse JSON
    ├─ Extract signals array
    │
    ▼
DatabaseWriter.insert_signals()
    │
    ├─ For each signal:
    │   ├─ Parse timestamp
    │   ├─ Determine detection_type (analog/dji)
    │   ├─ Normalize frequency (MHz)
    │   ├─ Extract power (dBm)
    │   └─ UPSERT to signals table
    │
    ▼
TimescaleDB (signals hypertable)
```

**Example Signal Record**:
```json
{
  "freq_mhz": 5800.0,
  "power_dbm": -45.2,
  "bandwidth_mhz": 20.0,
  "lat": 37.7749,
  "lon": -122.4194,
  "detection_type": "analog"
}
```

### 3. Status Data Flow
```
DragonSync API (/status)
    │
    ├─ JSON Response: {"gps": {...}, "cpu": {...}, ...}
    │
    ▼
KitCollector.poll_status()
    │
    ├─ Parse JSON
    ├─ Extract nested objects (gps, cpu, memory, disk, temps)
    │
    ▼
DatabaseWriter.insert_health()
    │
    ├─ Parse timestamp
    ├─ Extract GPS coordinates
    ├─ Extract system metrics
    ├─ Extract temperatures
    └─ INSERT to system_health table
    │
    ▼
TimescaleDB (system_health hypertable)
```

**Example Status Record**:
```json
{
  "gps": {
    "lat": 37.7749,
    "lon": -122.4194,
    "alt": 10.5
  },
  "cpu": {"percent": 45.2},
  "memory": {"percent": 62.8},
  "disk": {"percent": 38.1},
  "temps": {
    "cpu": 55.0,
    "gpu": 48.5
  },
  "uptime_hours": 48.3
}
```

## Error Handling

### HTTP Errors
```python
try:
    response = await self.client.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()
except httpx.TimeoutException:
    # Retry with linear backoff
    if retry < MAX_RETRIES:
        await asyncio.sleep(1 * (retry + 1))
        return await self.fetch_json(endpoint, retry + 1)
except httpx.HTTPStatusError:
    # Log and return None (no retry)
    logger.error(f"HTTP {e.response.status_code}")
except httpx.RequestError:
    # Log and return None
    logger.error(f"Request error: {e}")
```

### Database Errors
```python
try:
    conn.execute(query, params)
    conn.commit()
except SQLAlchemyError as e:
    logger.error(f"Failed to insert: {e}")
    conn.rollback()
    continue  # Skip this record, continue with others
```

### Data Parsing Errors
```python
def _safe_float(self, value: Any) -> Optional[float]:
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None  # Graceful degradation
```

## Configuration

### Environment Variables
```python
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://...')
KITS_CONFIG = os.getenv('KITS_CONFIG', '/config/kits.yaml')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))
STATUS_POLL_INTERVAL = int(os.getenv('STATUS_POLL_INTERVAL', '30'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
INITIAL_BACKOFF = float(os.getenv('INITIAL_BACKOFF', '5.0'))
MAX_BACKOFF = float(os.getenv('MAX_BACKOFF', '300.0'))
STALE_THRESHOLD = int(os.getenv('STALE_THRESHOLD', '60'))
```

### Kit Configuration Schema
```yaml
kits:
  - id: string              # Required: Unique kit identifier
    name: string            # Optional: Human-readable name
    api_url: string         # Required: Full URL to DragonSync API
    location: string        # Optional: Physical location
    enabled: boolean        # Optional: Enable/disable polling (default: true)
```

## Graceful Shutdown

### Signal Handling
```python
def signal_handler(signum, frame):
    """Handle SIGTERM and SIGINT"""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received signal {sig_name}")
    shutdown_event.set()  # Trigger shutdown

# Register handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

### Shutdown Flow
```
Signal (SIGTERM/SIGINT)
    │
    ▼
shutdown_event.set()
    │
    ├─ All KitCollector tasks exit polling loop
    ├─ Health monitor task exits
    │
    ▼
CollectorService.shutdown()
    │
    ├─ Close HTTP client (await client.aclose())
    ├─ Close database pool (engine.dispose())
    │
    ▼
Clean exit
```

### Polling Loop Shutdown Check
```python
while not shutdown_event.is_set():
    # Perform polling...

    # Wait for next poll or shutdown
    try:
        await asyncio.wait_for(
            shutdown_event.wait(),
            timeout=delay
        )
        break  # Shutdown requested
    except asyncio.TimeoutError:
        pass  # Normal timeout, continue polling
```

## Performance Optimizations

### 1. Connection Pooling
```python
# HTTP client pool
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30.0
    )
)

# Database connection pool
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

### 2. Concurrent Polling
```python
# Poll multiple endpoints in parallel
results = await asyncio.gather(
    self.poll_drones(),
    self.poll_signals(),
    return_exceptions=True
)

# Each kit polls independently in its own async task
for kit in self.kits:
    task = asyncio.create_task(kit.run())
    self.tasks.append(task)
```

### 3. Batch Inserts
```python
# Process all drones in a single transaction
for drone in drones:
    conn.execute(query, params)
conn.commit()  # Single commit for all
```

### 4. Exponential Backoff
```python
# Reduce load on offline kits
if kit offline:
    delay = min(5 * (2 ** failures), 300)
    # Wait up to 5 minutes before retrying
```

## Logging

### Log Levels
```python
logger.info()    # Normal operations
logger.debug()   # Detailed information
logger.warning() # Potential issues
logger.error()   # Errors that don't stop service
```

### Log Examples
```
# Startup
2026-01-19 23:00:00 - __main__ - INFO - Starting WarDragon Analytics Collector
2026-01-19 23:00:00 - __main__ - INFO - Loaded 3 kits from configuration

# Normal operations
2026-01-19 23:00:05 - __main__ - INFO - Kit kit-001: Collected 5 drones, inserted 5
2026-01-19 23:00:05 - __main__ - INFO - Kit kit-001: Collected 12 signals, inserted 12

# Errors
2026-01-19 23:00:10 - __main__ - ERROR - Kit kit-002: Timeout fetching /drones
2026-01-19 23:00:10 - __main__ - WARNING - Kit kit-002 failed (attempt 1). Next retry in 5.0s

# Health monitoring
2026-01-19 23:01:00 - __main__ - INFO - === Kit Health Status ===
2026-01-19 23:01:00 - __main__ - INFO - Kit kit-001: online | Success rate: 98.5% | ...

# Shutdown
2026-01-19 23:59:00 - __main__ - INFO - Received signal SIGTERM, initiating shutdown...
2026-01-19 23:59:00 - __main__ - INFO - HTTP client closed
2026-01-19 23:59:00 - __main__ - INFO - Database connection pool closed
2026-01-19 23:59:00 - __main__ - INFO - Collector service stopped
```

## Testing

### Unit Tests (Example)
```python
import pytest
from collector import KitHealth, DatabaseWriter

@pytest.mark.asyncio
async def test_exponential_backoff():
    health = KitHealth("test-kit")

    health.mark_failure("Test error")
    assert health.backoff_delay == 10.0  # 5 * 2^1

    health.mark_failure("Test error")
    assert health.backoff_delay == 20.0  # 5 * 2^2

    health.mark_success()
    assert health.backoff_delay == 5.0   # Reset

@pytest.mark.asyncio
async def test_database_insert():
    db = DatabaseWriter("postgresql://...")

    drones = [{"drone_id": "test", "lat": 37.7749, "lon": -122.4194}]
    inserted = await db.insert_drones("kit-001", drones)

    assert inserted == 1
```

## File Locations

All paths are relative to `/home/dragon/Downloads/wardragon-fpv-detect/WarDragonAnalytics/`:

- **Main Implementation**: `app/collector.py` (748 lines, 29 KB)
- **Documentation**: `app/README_COLLECTOR.md` (14 KB)
- **Validation Script**: `app/validate_collector.py` (8 KB)
- **Configuration Example**: `config/kits.yaml.example` (4.3 KB)
- **Implementation Summary**: `COLLECTOR_IMPLEMENTATION.md` (15 KB)
- **Code Reference**: `COLLECTOR_CODE_REFERENCE.md` (this file)

## Quick Start

1. **Validate setup**:
   ```bash
   cd app
   python validate_collector.py
   ```

2. **Run collector**:
   ```bash
   export DATABASE_URL="postgresql://wardragon:password@localhost:5432/wardragon"
   export KITS_CONFIG="./config/kits.yaml"
   python collector.py
   ```

3. **View logs**:
   ```bash
   # Watch for health statistics every 60s
   # Monitor kit status and error messages
   ```

## Additional Resources

- Full documentation: `app/README_COLLECTOR.md`
- System architecture: `docs/ARCHITECTURE.md`
- Deployment guide: `COLLECTOR_IMPLEMENTATION.md`
- Requirements: `app/requirements.txt`
- Docker setup: `app/Dockerfile`
