# Test Data Generator - File Index

## Overview

The test data generator creates realistic drone detection data for testing WarDragon Analytics. This document provides an index of all related files and their purposes.

---

## Core Files

### `test_data_generator.py` (774 lines)
**Main test data generator script**

- Generates realistic drone tracks with GPS waypoints
- Simulates FPV signal detections (5.8 GHz analog + DJI)
- Creates system health metrics (CPU, memory, disk, temps)
- Supports two output modes: SQL statements or direct database writes
- Highly configurable via CLI arguments

**Usage:**
```bash
python app/test_data_generator.py --mode=db --duration=2h --kits=3 --drones=15
```

**Key Features:**
- ✓ Realistic drone makes/models (DJI, Autel, Skydio, Parrot)
- ✓ Waypoint-based flight simulation
- ✓ Time progression with 5-second intervals
- ✓ Batch inserts for performance (1,000 records per batch)
- ✓ Conflict handling (ON CONFLICT DO NOTHING)
- ✓ Progress reporting

---

## Documentation Files

### `README_TEST_DATA.md`
**Comprehensive documentation**

- Installation instructions
- Usage examples (basic and advanced)
- Generated data specifications
- Database schema reference
- Performance benchmarks
- Troubleshooting guide

**Best for:** Understanding all features and capabilities

---

### `QUICK_START.md`
**Quick reference guide**

- TL;DR commands
- Common usage scenarios
- Example output
- Realistic data features checklist
- Quick troubleshooting

**Best for:** Getting started quickly without reading full docs

---

### `DATA_FLOW.md`
**Visual data flow and architecture**

- Flowcharts showing data generation process
- Data volume estimates for different scenarios
- Database schema mapping with examples
- Batch insert performance metrics
- Realistic data pattern explanations

**Best for:** Understanding how the generator works internally

---

## Helper Scripts

### `example_usage.py`
**Interactive example runner**

- Pre-configured scenarios (quick test, standard demo, heavy load)
- Interactive menu for easy testing
- Command generation without execution
- Programmatic API usage examples

**Usage:**
```bash
python app/example_usage.py
```

**Best for:** New users exploring different test scenarios

---

### `validate_test_data.py`
**Data validation script**

- Verifies generated data quality
- Checks GPS bounds, speed ranges, RSSI values
- Validates frequency ranges for FPV signals
- Reports statistics and potential issues
- Ensures data looks realistic

**Usage:**
```bash
python app/validate_test_data.py --db-url="postgresql://..."
```

**Best for:** Confirming test data is valid after generation

---

## Configuration Files

### `requirements_test_generator.txt`
**Python dependencies**

```
psycopg2-binary>=2.9.9  # For --mode=db
```

**Installation:**
```bash
pip install -r app/requirements_test_generator.txt
```

---

## Quick Command Reference

### Generate Test Data

```bash
# Quick test (15 minutes)
python app/test_data_generator.py --mode=db --duration=15m --kits=1 --drones=3

# Standard demo (2 hours)
python app/test_data_generator.py --mode=db --duration=2h --kits=3 --drones=15

# Generate SQL file
python app/test_data_generator.py --mode=sql --duration=1h > test_data.sql

# Custom database URL
python app/test_data_generator.py --mode=db --db-url="postgresql://user:pass@host/db"

# High signal activity
python app/test_data_generator.py --mode=db --signal-probability=0.7
```

### Validate Data

```bash
# Validate generated data
python app/validate_test_data.py

# Custom database URL
python app/validate_test_data.py --db-url="postgresql://user:pass@host/db"
```

### Interactive Examples

```bash
# Run interactive menu
python app/example_usage.py
```

---

## File Size Reference

| File | Size | Purpose |
|------|------|---------|
| `test_data_generator.py` | 28 KB | Main generator script |
| `validate_test_data.py` | 11 KB | Data validation |
| `example_usage.py` | 5.2 KB | Interactive examples |
| `README_TEST_DATA.md` | 6.6 KB | Full documentation |
| `QUICK_START.md` | 3.0 KB | Quick reference |
| `DATA_FLOW.md` | 9.7 KB | Architecture diagrams |
| `requirements_test_generator.txt` | 251 B | Dependencies |

---

## Data Generation Workflow

```
1. Read documentation:
   → QUICK_START.md (for quick overview)
   → README_TEST_DATA.md (for full details)

2. Install dependencies:
   → pip install -r app/requirements_test_generator.txt

3. Choose approach:
   a) CLI: python app/test_data_generator.py --mode=db ...
   b) Interactive: python app/example_usage.py
   c) Programmatic: import test_data_generator

4. Generate data:
   → Customize --kits, --drones, --duration as needed

5. Validate results:
   → python app/validate_test_data.py

6. Use data:
   → Web UI: http://localhost:8080
   → Grafana: http://localhost:3000
   → SQL: psql -U wardragon -d wardragon
```

---

## Typical Use Cases

### 1. Quick UI Testing
```bash
# Generate 15 minutes of data, 1 kit, 3 drones
python app/test_data_generator.py --mode=db --duration=15m --kits=1 --drones=3
```
**Result:** ~700 records, takes ~3 seconds

---

### 2. Demo for Stakeholders
```bash
# Generate 2 hours of data, 3 kits, 15 drones
python app/test_data_generator.py --mode=db --duration=2h --kits=3 --drones=15
```
**Result:** ~52,000 records, takes ~30 seconds

---

### 3. Performance Testing
```bash
# Generate 4 hours of data, 5 kits, 20 drones
python app/test_data_generator.py --mode=db --duration=4h --kits=5 --drones=20
```
**Result:** ~144,000 records, takes ~2 minutes

---

### 4. SQL Review/Import
```bash
# Generate SQL to file for review
python app/test_data_generator.py --mode=sql --duration=1h > test_data.sql

# Review generated SQL
less test_data.sql

# Import to database
psql -U wardragon -d wardragon < test_data.sql
```

---

### 5. FPV Signal Heavy Testing
```bash
# Generate data with 70% signal detection probability
python app/test_data_generator.py --mode=db --duration=1h --signal-probability=0.7
```
**Result:** More FPV signal records for testing signal analytics

---

## Data Characteristics Summary

### Drones
- **Makes:** DJI, Autel, Skydio, Parrot
- **Models:** Mini 3 Pro, Mavic 3, Air 3, EVO II Pro, etc.
- **Flight duration:** 5-45 minutes
- **Speed:** 5-20 m/s
- **Altitude:** 30-120 meters
- **Update rate:** Every 5 seconds
- **Waypoints:** 3-8 per flight

### FPV Signals
- **Frequencies:** 5.3-6.0 GHz (Bands A, B, E, F, R, DJI)
- **Power:** -85 to -45 dBm
- **Types:** 70% analog, 30% DJI digital
- **Detection rate:** 30% per 5s interval (configurable)

### System Health
- **CPU:** 20-60%
- **Memory:** 40-70%
- **Disk:** 30-52% (slowly increasing)
- **CPU temp:** 40-70°C
- **GPU temp:** 35-60°C
- **Update rate:** Every 30 seconds

### Kits
- **Locations:** Major US cities (SF, LA, NYC, Chicago, etc.)
- **Status:** All online
- **GPS jitter:** ±10 meters (realistic stationary drift)

---

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| "psycopg2 not installed" | `pip install psycopg2-binary` |
| Database connection failed | Check TimescaleDB is running: `docker ps` |
| Too much data | Reduce `--duration`, `--kits`, or `--drones` |
| Not enough signals | Increase `--signal-probability` (0.0-1.0) |
| Need custom DB URL | Use `--db-url="postgresql://..."` |
| Want to review SQL | Use `--mode=sql` instead of `--mode=db` |

---

## Integration with Analytics Platform

After generating test data:

1. **View in Web UI**
   ```bash
   # Assuming web UI is running
   open http://localhost:8080
   ```

2. **View in Grafana**
   ```bash
   # Assuming Grafana is running
   open http://localhost:3000
   ```

3. **Query Database Directly**
   ```bash
   psql -U wardragon -d wardragon
   ```
   ```sql
   -- Check counts
   SELECT COUNT(*) FROM drones;
   SELECT COUNT(*) FROM signals;
   SELECT COUNT(*) FROM system_health;

   -- View sample data
   SELECT * FROM kits;
   SELECT * FROM drones ORDER BY time DESC LIMIT 10;
   SELECT * FROM signals ORDER BY time DESC LIMIT 10;
   ```

---

## Next Steps

1. **First time users:** Start with `QUICK_START.md`
2. **Want full details:** Read `README_TEST_DATA.md`
3. **Curious how it works:** Review `DATA_FLOW.md`
4. **Ready to generate:** Run `python app/test_data_generator.py`
5. **Want interactive mode:** Run `python app/example_usage.py`
6. **Need validation:** Run `python app/validate_test_data.py`

---

## Support

For issues or questions:
- Review troubleshooting section in `README_TEST_DATA.md`
- Check database schema in `docs/ARCHITECTURE.md`
- Validate data with `validate_test_data.py`
- Review examples in `example_usage.py`

---

**Last Updated:** 2026-01-19
**Version:** 1.0
**License:** Apache 2.0
