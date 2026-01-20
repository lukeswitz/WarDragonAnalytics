# WarDragon Analytics

**Multi-kit drone surveillance aggregation and visualization platform**

Centralized logging, analysis, and visualization of data from one or more WarDragon kits running [DragonSync](https://github.com/alphafox02/DragonSync).

---

## Status: ✅ Phase 2 Complete - Production Ready

WarDragon Analytics is fully operational with Phase 1 (core features) and Phase 2 (pattern detection and tactical intelligence) complete. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

---

## What It Does

- **Aggregates data** from multiple WarDragon kits via the DragonSync API
- **Stores time-series data** in TimescaleDB (PostgreSQL extension)
- **Visualizes** drone tracks, FPV signals, and system health in Grafana + custom web UI
- **Exports** data to CSV, KML (Google Earth)
- **Monitors** kit health and availability
- **Runs anywhere:** Docker container (local on kit, centralized server, or cloud)

---

## Architecture Overview

```
WarDragon Kits (Field)  →  Analytics (Docker)  →  Grafana/Web UI
   DragonSync APIs          TimescaleDB            Maps, Dashboards
   :8088                    Collector Service      CSV/KML Export
```

**Data Sources:**
- Drones (Remote ID: DJI, BLE, Wi-Fi)
- Aircraft (ADS-B tracks)
- FPV Signals (5.8GHz analog, DJI)
- System Health (GPS, CPU, memory, temps)

**Components:**
- **TimescaleDB:** Time-series database (30-day retention, 1-year aggregates)
- **Collector:** Python service polling DragonSync APIs every 5s
- **Web UI:** FastAPI + Leaflet map (all kits combined)
- **Grafana:** Pre-built dashboards for operations, health, analytics

---

## Quick Start (When Ready)

```bash
# Clone repo
git clone https://github.com/yourusername/WarDragonAnalytics.git
cd WarDragonAnalytics

# Configure kits
cp config/kits.yaml.example config/kits.yaml
# Edit kits.yaml to add your WarDragon kit IPs

# Set passwords
cp .env.example .env
# Edit .env to set DB and Grafana passwords

# Start services
docker-compose up -d

# Access UIs
# Web UI:  http://localhost:8090
# Grafana: http://localhost:3000  (admin / <GRAFANA_PASSWORD>)
```

---

## Deployment Options

### Option 1: Centralized Server (Recommended)
- Deploy Analytics on a server/cloud instance
- Configure multiple kits to report to it
- Best for operations with 3+ kits

### Option 2: Per-Kit Local
- Deploy Analytics alongside DragonSync on the same kit
- Point at `http://127.0.0.1:8088`
- Best for single-kit deployments or field testing

### Option 3: Hybrid
- Some kits report to central Analytics
- Some run local Analytics instances
- Best for mixed deployments (HQ + field units)

---

## Features Roadmap

### Phase 1: Core Platform ✅ COMPLETE
- [x] Architecture design
- [x] TimescaleDB schema + init scripts
- [x] Collector service (multi-kit polling)
- [x] Web UI (Leaflet map + table)
- [x] Docker Compose deployment
- [x] REST API endpoints (kits, drones, signals, CSV export)
- [x] Kit health monitoring
- [x] Multi-kit aggregation

### Phase 2: Pattern Detection & Intelligence ✅ COMPLETE
- [x] Pattern detection APIs (5 endpoints)
- [x] Database views and functions for pattern analysis
- [x] Grafana dashboards (4 tactical dashboards)
- [x] Enhanced web UI (alerts, filters, watchlist)
- [x] Test data generator with realistic scenarios
- [x] Comprehensive documentation

### Phase 3: Advanced Features (Planned)
- [ ] Geofencing alerts
- [ ] RID watchlist automation
- [ ] Continuous aggregates for historical analysis
- [ ] Data retention policies and archiving
- [ ] KML export for Google Earth
- [ ] Alert webhooks and notifications

### Phase 4: Production Hardening (Planned)
- [ ] Authentication (OAuth2, API keys)
- [ ] Role-based access control
- [ ] Encrypted database connections
- [ ] Mobile-optimized UI
- [ ] High-availability deployment options

---

## Requirements

**Server/Host:**
- Docker + Docker Compose
- 2GB RAM minimum (4GB recommended for multi-kit)
- 50GB disk (for 30 days of 5-kit data)

**WarDragon Kits:**
- DragonSync v2.0+ with API enabled (default port 8088)
- Network connectivity to Analytics host

---

## Testing

WarDragon Analytics includes comprehensive test coverage with both unit and integration tests.

### Quick Start

```bash
# Install test dependencies
make install-test-deps

# Run unit tests (fast, no Docker required)
make test

# Run integration tests (requires Docker Compose)
make start
make test-integration

# Generate coverage report
make coverage
```

### Test Categories

- **Unit Tests**: Fast tests without external dependencies (70%+ coverage required)
- **Integration Tests**: Full-stack tests with Docker Compose and database
- **CI/CD**: Automated testing on push/PR with GitHub Actions

### Test Commands

| Command | Description |
|---------|-------------|
| `make test` | Run unit tests only |
| `make test-integration` | Run integration tests (needs Docker) |
| `make test-all` | Run all tests |
| `make coverage` | Generate HTML coverage report |
| `make test-verbose` | Run with verbose output |

### Test Markers

Run specific test categories using pytest markers:

```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api           # API endpoint tests
pytest -m database      # Database tests
```

### Coverage Requirements

- **Minimum**: 70% code coverage (enforced in CI/CD)
- **Target**: 80%+ for production code
- **Reports**: HTML and XML coverage reports generated automatically

See [TESTING.md](TESTING.md) for comprehensive testing documentation.

---

## Phase 2 Features

WarDragon Analytics Phase 2 adds tactical intelligence and pattern detection capabilities for operators.

### Grafana Dashboards

Pre-built operational dashboards available at http://localhost:3000:

**Tactical Overview Dashboard**
- Active drones in last 5 minutes
- Kit status grid (online/offline/stale)
- Active alerts and anomalies
- Drone count timeline
- Top Remote ID manufacturers detected

**Pattern Analysis Dashboard**
- Repeated drone detections (surveillance patterns)
- Operator reuse tracking (same operator, multiple drones)
- Coordinated activity detection (swarms)
- Flight pattern analysis
- Frequency reuse patterns

**Multi-Kit Correlation Dashboard**
- Same drone seen by multiple kits (triangulation)
- Coverage overlap visualization
- Kit-to-kit handoff tracking
- Detection density heatmap

**Anomaly Detection Dashboard**
- Altitude anomalies (rapid climbs/descents)
- Speed anomalies (unusually fast/slow)
- Out-of-pattern behavior alerts
- Signal strength anomalies

### Pattern Detection APIs

New intelligence endpoints for tactical operations:

```bash
# Find drones seen multiple times (surveillance pattern)
curl http://localhost:8090/api/patterns/repeated-drones?hours=24

# Detect coordinated activity (swarms)
curl http://localhost:8090/api/patterns/coordinated?hours=6

# Find operator reuse across different drones
curl http://localhost:8090/api/patterns/pilot-reuse?hours=12

# Detect anomalous behavior
curl http://localhost:8090/api/patterns/anomalies?hours=6

# Find multi-kit detections (triangulation opportunities)
curl http://localhost:8090/api/patterns/multi-kit?hours=6
```

### Enhanced Web UI (Port 8090)

Tactical operations interface with:
- Live alert panel (new drones, pattern matches, anomalies)
- Quick filters: "Show unusual", "Show repeated", "Show coordinated"
- Pattern highlighting (coordinated drones grouped)
- Threat summary cards
- RID watchlist capability

### Test Data Generator

Generate realistic test scenarios with patterns:

```bash
# Generate all test scenarios (recommended for first-time setup)
python tests/generate_test_data.py --scenario all

# Generate specific scenarios
python tests/generate_test_data.py --scenario normal          # Baseline operations
python tests/generate_test_data.py --scenario repeated        # Surveillance pattern
python tests/generate_test_data.py --scenario coordinated     # Swarm behavior
python tests/generate_test_data.py --scenario operator        # Operator reuse
python tests/generate_test_data.py --scenario multikit        # Triangulation
python tests/generate_test_data.py --scenario anomalies       # Unusual behavior
python tests/generate_test_data.py --scenario fpv             # FPV signals

# Clean test data
python tests/generate_test_data.py --clean

# Preview without inserting (dry run)
python tests/generate_test_data.py --scenario all --dry-run
```

**Test Scenarios:**
- **Normal Operations**: 20-30 drones, typical flight patterns, 48 hours of data
- **Repeated Drone**: Same drone appearing 3-5 times over 24 hours (surveillance)
- **Coordinated Activity**: 4-6 drones together within 500m (swarms)
- **Operator Reuse**: Same operator ID across different drones, or pilots within 50m
- **Multi-Kit Detections**: Same drone seen by 2-3 kits simultaneously (triangulation)
- **Anomalies**: Speed spikes (0-40m/s), altitude drops (100m to 10m), erratic heading
- **FPV Signals**: 5.8GHz detections at common frequencies with realistic power levels

See [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) for tactical workflows and pattern interpretation.

---

## Documentation

### Getting Started
- **[README.md](README.md)** (this file) - Project overview and quick start
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Installation and deployment guide
- **[QUICKSTART.md](QUICKSTART.md)** - Fast setup for testing

### Operations
- **[OPERATOR_GUIDE.md](OPERATOR_GUIDE.md)** - Tactical operations manual and workflows
- **[GRAFANA_DASHBOARDS.md](GRAFANA_DASHBOARDS.md)** - Dashboard usage and interpretation guide
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete REST API documentation
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

### Development
- **[TESTING.md](TESTING.md)** - Testing guide and test data generation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and database schema
- **[SECURITY.md](SECURITY.md)** - Security hardening and best practices
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation index

### Reference
- **[grafana/DASHBOARD_QUERIES.md](grafana/DASHBOARD_QUERIES.md)** - SQL query reference for dashboards
- **[docs/development/](docs/development/)** - Development-specific documentation
- **[docs/archive/](docs/archive/)** - Archived implementation documents

---

## Related Projects

- **[DragonSync](https://github.com/alphafox02/DragonSync)** - Drone detection and TAK integration (runs on WarDragon kits)
- **[WarDragon](https://github.com/alphafox02/WarDragon)** - Hardware platform for drone detection
- **[DragonOS](https://cemaxecuter.com/)** - Custom Linux distribution for SDR and drone detection

---

## License

Apache 2.0 (same as DragonSync)

---

## Contributing

This project is in early planning. Contributions welcome once MVP is implemented.

**To contribute:**
1. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. Open an issue to discuss your idea
3. Fork, implement, test, submit PR

---

## Contact

- **Issues:** [GitHub Issues](https://github.com/yourusername/WarDragonAnalytics/issues)
- **DragonSync:** [alphafox02/DragonSync](https://github.com/alphafox02/DragonSync)

---

**Note:** This is a companion project to DragonSync. It does not replace on-kit logging (use `drone_logger.py` + `log_viewer.py` for that). Analytics is for multi-kit aggregation and advanced visualization.
