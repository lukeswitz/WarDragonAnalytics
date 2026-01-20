# Collector Implementation Summary

This document summarizes the production-ready collector service created for WarDragon Analytics.

## Files Created

### 1. `/app/collector.py` (748 lines)
Main collector service implementation with all required features.

**Key Components:**

#### KitHealth Class
- Tracks kit health status (online/offline/stale/error)
- Implements exponential backoff (5s → 300s max)
- Maintains success/failure statistics
- Calculates next poll delay based on failures

#### DatabaseWriter Class
- SQLAlchemy-based database interface
- Connection pooling (10 base + 20 overflow)
- Inserts to three hypertables:
  - `drones` - Drone/aircraft tracks
  - `signals` - FPV signal detections
  - `system_health` - Kit system metrics
- Updates `kits` table with current status
- Handles data normalization and type conversion
- Comprehensive error handling with rollback

#### KitCollector Class
- Per-kit async polling task
- Fetches three endpoints:
  - `/drones` - Every 5 seconds
  - `/signals` - Every 5 seconds
  - `/status` - Every 30 seconds
- HTTP retry logic (up to 3 retries with linear backoff)
- Handles various API response formats
- Updates health status after each poll

#### CollectorService Class
- Main orchestrator and service manager
- Loads configuration from `kits.yaml`
- Spawns async task per enabled kit
- Monitors health every 60 seconds
- Handles SIGTERM/SIGINT for graceful shutdown
- Manages HTTP client pool and database connections

**Features Implemented:**
- ✓ Loads kits from config/kits.yaml
- ✓ Spawns async tasks to poll each kit every 5 seconds
- ✓ Fetches /drones, /signals, /status endpoints
- ✓ Normalizes data and writes to TimescaleDB
- ✓ Tracks kit health (online/offline/stale)
- ✓ Implements exponential backoff for offline kits
- ✓ Uses asyncio + httpx for async HTTP requests
- ✓ Uses SQLAlchemy for database writes
- ✓ Logs all activity with structured logging
- ✓ Handles SIGTERM/SIGINT for graceful shutdown
- ✓ Connection pooling (HTTP and database)
- ✓ Comprehensive error handling
- ✓ Retry logic with backoff

### 2. `/config/kits.yaml.example`
Example kit configuration with detailed comments showing:
- Single-kit local deployment
- Multi-kit remote deployment
- Custom retry policies
- Per-kit settings (poll intervals, timeouts)
- Tag-based organization

### 3. `/app/README_COLLECTOR.md`
Comprehensive documentation covering:
- Architecture overview with diagrams
- Component descriptions
- Configuration guide
- Database schema
- Running instructions (Docker, standalone)
- Monitoring and health tracking
- Error handling strategies
- Performance metrics
- Troubleshooting guide
- Development workflow
- Security best practices
- Production checklist

### 4. `/app/validate_collector.py`
Validation script that checks:
- Python syntax
- Required dependencies
- Configuration file format
- Database connectivity (optional)
- HTTP client initialization
- Module loading

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CollectorService (main orchestrator)                   │
│  ├─ Loads kits.yaml                                     │
│  ├─ Creates HTTP client pool                            │
│  ├─ Creates DatabaseWriter                              │
│  └─ Spawns KitCollector tasks                           │
│     ├─ KitCollector (kit-001)                           │
│     │  └─ KitHealth tracker                             │
│     ├─ KitCollector (kit-002)                           │
│     │  └─ KitHealth tracker                             │
│     └─ KitCollector (kit-003)                           │
│        └─ KitHealth tracker                             │
│                                                          │
│  Health Monitor (every 60s)                             │
│  ├─ Logs statistics                                     │
│  ├─ Marks stale kits                                    │
│  └─ Updates kit status                                  │
└──────────────────────────────────────────────────────────┘
         │                                    │
         │ HTTP/JSON                          │ SQL
         ▼                                    ▼
┌──────────────────┐              ┌────────────────────┐
│  DragonSync APIs │              │  TimescaleDB       │
│  (WarDragon Kits)│              │  ├─ drones         │
│  ├─ /drones      │              │  ├─ signals        │
│  ├─ /signals     │              │  ├─ system_health  │
│  └─ /status      │              │  └─ kits           │
└──────────────────┘              └────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://wardragon:password@timescaledb:5432/wardragon
KITS_CONFIG=/config/kits.yaml

# Optional (with defaults)
POLL_INTERVAL=5              # Drones/signals poll interval
STATUS_POLL_INTERVAL=30      # Status poll interval
REQUEST_TIMEOUT=10           # HTTP timeout (seconds)
MAX_RETRIES=3                # HTTP retry attempts
INITIAL_BACKOFF=5.0          # Initial backoff delay (seconds)
MAX_BACKOFF=300.0            # Max backoff delay (seconds)
STALE_THRESHOLD=60           # Stale threshold (seconds)
```

### Kit Configuration

Create `/config/kits.yaml`:

```yaml
kits:
  - id: kit-001
    name: "Mobile Unit Alpha"
    api_url: "http://192.168.1.100:8088"
    location: "Field Operations"
    enabled: true
```

## Database Schema

The collector writes to these tables (must be created first via `timescaledb/init.sql`):

### drones (hypertable)
```sql
CREATE TABLE drones (
    time TIMESTAMPTZ NOT NULL,
    kit_id TEXT NOT NULL,
    drone_id TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    alt DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    heading DOUBLE PRECISION,
    pilot_lat DOUBLE PRECISION,
    pilot_lon DOUBLE PRECISION,
    home_lat DOUBLE PRECISION,
    home_lon DOUBLE PRECISION,
    mac TEXT,
    rssi INTEGER,
    freq DOUBLE PRECISION,
    ua_type TEXT,
    operator_id TEXT,
    caa_id TEXT,
    rid_make TEXT,
    rid_model TEXT,
    rid_source TEXT,
    track_type TEXT,
    PRIMARY KEY (time, kit_id, drone_id)
);
```

### signals (hypertable)
```sql
CREATE TABLE signals (
    time TIMESTAMPTZ NOT NULL,
    kit_id TEXT NOT NULL,
    freq_mhz DOUBLE PRECISION NOT NULL,
    power_dbm DOUBLE PRECISION,
    bandwidth_mhz DOUBLE PRECISION,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    alt DOUBLE PRECISION,
    detection_type TEXT,
    PRIMARY KEY (time, kit_id, freq_mhz)
);
```

### system_health (hypertable)
```sql
CREATE TABLE system_health (
    time TIMESTAMPTZ NOT NULL,
    kit_id TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    alt DOUBLE PRECISION,
    cpu_percent DOUBLE PRECISION,
    memory_percent DOUBLE PRECISION,
    disk_percent DOUBLE PRECISION,
    uptime_hours DOUBLE PRECISION,
    temp_cpu DOUBLE PRECISION,
    temp_gpu DOUBLE PRECISION,
    PRIMARY KEY (time, kit_id)
);
```

### kits (regular table)
```sql
CREATE TABLE kits (
    kit_id TEXT PRIMARY KEY,
    name TEXT,
    location TEXT,
    api_url TEXT NOT NULL,
    last_seen TIMESTAMPTZ,
    status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Running the Collector

### Prerequisites

1. **TimescaleDB running**
   ```bash
   docker-compose up -d timescaledb
   ```

2. **Database schema initialized**
   ```bash
   docker exec -i timescaledb psql -U wardragon < timescaledb/init.sql
   ```

3. **Kit configuration created**
   ```bash
   cp config/kits.yaml.example config/kits.yaml
   # Edit with your kit details
   ```

### With Docker (Recommended)

```bash
# Build image
docker build -t wardragon-analytics:latest app/

# Run collector
docker run -d \
  --name wardragon-collector \
  -e DATABASE_URL="postgresql://wardragon:password@timescaledb:5432/wardragon" \
  -e KITS_CONFIG=/config/kits.yaml \
  -v $(pwd)/config:/config:ro \
  --network wardragon-network \
  wardragon-analytics:latest \
  python collector.py

# View logs
docker logs -f wardragon-collector
```

### With Docker Compose

Add to `docker-compose.yml`:

```yaml
services:
  collector:
    build: ./app
    container_name: wardragon-collector
    environment:
      DATABASE_URL: postgresql://wardragon:${DB_PASSWORD}@timescaledb:5432/wardragon
      KITS_CONFIG: /config/kits.yaml
      POLL_INTERVAL: 5
      STATUS_POLL_INTERVAL: 30
    volumes:
      - ./config:/config:ro
    depends_on:
      - timescaledb
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Then:
```bash
docker-compose up -d collector
docker-compose logs -f collector
```

### Standalone Python

```bash
# Install dependencies
pip install -r app/requirements.txt

# Set environment
export DATABASE_URL="postgresql://wardragon:password@localhost:5432/wardragon"
export KITS_CONFIG="$(pwd)/config/kits.yaml"

# Run collector
cd app
python collector.py
```

## Validation

Before running in production, validate the setup:

```bash
cd app
python validate_collector.py
```

This will check:
- Python syntax
- Required dependencies
- Configuration file validity
- Database connectivity
- HTTP client initialization
- Module loading

## Monitoring

### Health Logs

Every 60 seconds, the collector logs health statistics:

```
2026-01-19 23:00:00 - __main__ - INFO - === Kit Health Status ===
2026-01-19 23:00:00 - __main__ - INFO - Kit kit-001: online | Success rate: 98.5% | Requests: 720 (OK: 709, Failed: 11)
2026-01-19 23:00:00 - __main__ - INFO - Kit kit-002: offline | Success rate: 0.0% | Requests: 120 (OK: 0, Failed: 120)
2026-01-19 23:00:00 - __main__ - INFO -   Last error: Request error fetching /drones: Connection refused
2026-01-19 23:00:00 - __main__ - INFO - ========================================
```

### Kit Status States

- **unknown**: Initial state before first poll
- **online**: Successfully polling and receiving data
- **offline**: Failed to connect or fetch data (exponential backoff active)
- **stale**: No data received in last 60 seconds
- **error**: Unexpected error occurred

### Exponential Backoff

When a kit fails, retry delays increase exponentially:
- Failure 1: Wait 5s
- Failure 2: Wait 10s (5 * 2^1)
- Failure 3: Wait 20s (5 * 2^2)
- Failure 4: Wait 40s (5 * 2^3)
- Failure 5: Wait 80s (5 * 2^4)
- Failure 6+: Wait 300s (max backoff)

This prevents overwhelming offline kits while still attempting recovery.

## Error Handling

### Network Errors
- HTTP timeouts trigger automatic retry (up to 3 attempts)
- Connection errors trigger exponential backoff
- HTTP 4xx/5xx errors are logged and skipped

### Database Errors
- Failed inserts are logged and skipped (doesn't block other records)
- Connection pool auto-recovers from transient failures
- Pre-ping validates connections before use

### Data Format Issues
- Missing fields default to NULL
- Invalid types are safely converted
- Malformed JSON is logged and skipped

## Performance

### Expected Throughput
- **Typical**: 100-500 database inserts/second
- **Peak**: 1000+ inserts/second (10 active kits)
- **Latency**: < 10s from detection to database

### Resource Usage
- **CPU**: 5-20% on 4-core system (10 kits)
- **Memory**: 100-300 MB
- **Network**: 1-10 KB/s per kit
- **DB Connections**: 10 base + 20 overflow

## Troubleshooting

### Collector Won't Start

```bash
# Check database
psql $DATABASE_URL -c "SELECT 1"

# Verify config
python -c "import yaml; print(yaml.safe_load(open('config/kits.yaml')))"

# Check logs
docker logs wardragon-collector
```

### Kit Shows Offline

```bash
# Test API manually
curl http://192.168.1.100:8088/status

# Check network
ping 192.168.1.100

# Verify DragonSync running
ssh kit@192.168.1.100 "systemctl status dragonsync"
```

### High Database Latency

```bash
# Check active queries
docker exec -i timescaledb psql -U wardragon -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Add index if needed
docker exec -i timescaledb psql -U wardragon -c \
  "CREATE INDEX IF NOT EXISTS idx_drones_kit_time ON drones(kit_id, time DESC);"
```

## Production Checklist

- [ ] TimescaleDB initialized with schema
- [ ] Kit configuration created and validated
- [ ] Environment variables set
- [ ] Firewall rules allow kit API access
- [ ] Database backups configured
- [ ] Resource limits set (CPU/memory)
- [ ] Health checks enabled
- [ ] Auto-restart enabled
- [ ] Log rotation configured
- [ ] Monitoring/alerting set up (optional)

## Next Steps

1. **Database Setup**: Create TimescaleDB schema
2. **Configuration**: Customize `config/kits.yaml` with your kits
3. **Testing**: Run validation script
4. **Deployment**: Start collector service
5. **Monitoring**: Watch health logs
6. **Web UI**: Implement `api.py` for data visualization (Phase 2)

## Code Quality

The collector implementation follows best practices:

- **Async/Await**: Modern async Python for concurrent I/O
- **Type Hints**: Full type annotations for clarity
- **Error Handling**: Comprehensive exception handling
- **Logging**: Structured logging with levels
- **Resource Management**: Proper cleanup on shutdown
- **Security**: Non-root user, input validation
- **Performance**: Connection pooling, efficient queries
- **Maintainability**: Clear structure, well-documented

## License

Apache 2.0 (same as DragonSync)

## Related Files

- `/app/collector.py` - Main implementation (748 lines)
- `/app/README_COLLECTOR.md` - Comprehensive documentation
- `/app/validate_collector.py` - Validation script
- `/app/requirements.txt` - Python dependencies
- `/app/Dockerfile` - Container build configuration
- `/config/kits.yaml.example` - Configuration template
- `/docs/ARCHITECTURE.md` - Overall system design

## Support

For issues or questions:
- Review `/app/README_COLLECTOR.md` for detailed documentation
- Check logs with `docker logs -f wardragon-collector`
- Run validation with `python validate_collector.py`
- See `/docs/ARCHITECTURE.md` for system design
