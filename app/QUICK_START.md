# Quick Start - Test Data Generator

## TL;DR

```bash
# Install dependencies
pip install psycopg2-binary

# Generate 2 hours of test data (3 kits, ~15 drones each)
python app/test_data_generator.py --mode=db --duration=2h --kits=3 --drones=15

# View in web UI
open http://localhost:8090
```

## Common Commands

### Quick Test (15 minutes, small dataset)
```bash
python app/test_data_generator.py --mode=db --duration=15m --kits=1 --drones=3
```

### Standard Demo (2 hours, 3 kits)
```bash
python app/test_data_generator.py --mode=db --duration=2h --kits=3 --drones=15
```

### Generate SQL file (for manual review/import)
```bash
python app/test_data_generator.py --mode=sql --duration=1h > test_data.sql
psql -U wardragon -d wardragon < test_data.sql
```

### High Activity (lots of FPV signals)
```bash
python app/test_data_generator.py --mode=db --duration=1h --signal-probability=0.7
```

## What Gets Generated

| Data Type | Rate | Details |
|-----------|------|---------|
| **Drone tracks** | Every 5s | Realistic flight paths with waypoints |
| **FPV signals** | Probabilistic (default 30%) | 5.8 GHz analog + DJI digital |
| **System health** | Every 30s | CPU, memory, disk, temps, GPS |
| **Kits** | One-time | Kit registry with locations |

## Example Output

```
Generating test data:
  Time range: 2026-01-19T21:00:00+00:00 to 2026-01-19T23:00:00+00:00
  Duration: 2:00:00
  Kits: 3
  Drones per kit: ~15

Generated 47 drone tracks
  Progress: 2026-01-19T21:10:00+00:00 | Drones: 2850, Signals: 432, Health: 120

============================================================
GENERATION COMPLETE
============================================================
Kits:          3
Drone records: 45,230
Signal records: 6,842
Health records: 720
Total records: 52,792
============================================================
```

## Realistic Data Features

- **DJI, Autel, Skydio, Parrot** makes/models
- **Waypoint-based flight paths** (not random GPS)
- **Realistic speeds** (5-20 m/s) and altitudes (30-120m)
- **Pilot and home locations** within 5km of kit
- **Flight durations** 5-45 minutes
- **RSSI signal strength** -90 to -40 dBm
- **FAA operator IDs** and serial numbers
- **System health variation** (CPU spikes, temp changes)

## Troubleshooting

**"psycopg2 not installed"**
```bash
pip install psycopg2-binary
```

**Database connection failed**
```bash
# Check TimescaleDB is running
docker ps | grep timescale

# Or use docker-compose
cd WarDragonAnalytics
docker-compose up -d timescaledb
```

**Need custom database URL**
```bash
python app/test_data_generator.py \
  --mode=db \
  --db-url="postgresql://user:pass@host:5432/wardragon"
```

## Next Steps

1. **View data in Grafana**: http://localhost:3000
2. **Use web UI**: http://localhost:8090
3. **Query database directly**:
   ```sql
   SELECT COUNT(*) FROM drones;
   SELECT DISTINCT rid_make, rid_model FROM drones;
   SELECT * FROM kits;
   ```

## Full Documentation

See [README_TEST_DATA.md](README_TEST_DATA.md) for complete documentation.
