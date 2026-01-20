# Docker Compose Setup - File Overview

This document provides an overview of all Docker-related configuration files for WarDragon Analytics.

## Core Docker Files

### docker-compose.yml
**Purpose:** Main Docker Compose configuration file

**Services:**
1. **timescaledb** - PostgreSQL 15 with TimescaleDB extension
   - Image: `timescale/timescaledb:latest-pg15`
   - Port: `127.0.0.1:5432:5432` (localhost only for security)
   - Volume: `timescale-data` for persistent storage
   - Health check: `pg_isready`
   - Optimized PostgreSQL settings for time-series data

2. **collector** - Python service that polls WarDragon kits
   - Built from `./app/Dockerfile` (target: collector)
   - Depends on: timescaledb
   - Environment: Database URL, kit config path, polling intervals
   - Health check: Checks for `/tmp/collector_healthy` file
   - Restart policy: `unless-stopped`

3. **web** - FastAPI web interface
   - Built from `./app/Dockerfile` (target: web)
   - Port: `8080:8080`
   - Depends on: timescaledb
   - Health check: HTTP GET `/health`
   - Restart policy: `unless-stopped`

4. **grafana** - Visualization and dashboards
   - Image: `grafana/grafana:latest`
   - Port: `3000:3000`
   - Depends on: timescaledb
   - Plugins: worldmap-panel, piechart-panel
   - Uses TimescaleDB for internal Grafana database
   - Health check: HTTP GET `/api/health`
   - Restart policy: `unless-stopped`

**Networks:**
- `wardragon-net` - Bridge network with subnet 172.20.0.0/16

**Volumes:**
- `timescale-data` - PostgreSQL database files
- `grafana-data` - Grafana dashboards and configuration

### docker-compose.prod.yml
**Purpose:** Production-specific overrides

**Enhancements:**
- Resource limits (CPU/memory) for all services
- Enhanced logging with compression
- Restart policies with backoff
- Production environment variables
- Specific CORS origins (not wildcard)

**Usage:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### docker-compose.override.yml.example
**Purpose:** Development environment template

**Features:**
- Source code volume mounts for live development
- Debug logging enabled
- Hot reload for web service
- Exposed debugging ports
- Verbose database query logging
- Anonymous Grafana access for testing

**Usage:**
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
# Edit as needed
docker-compose up -d  # Automatically uses override file
```

## Environment Configuration

### .env.example
**Purpose:** Environment variable template

**Variables:**
- `DB_PASSWORD` - TimescaleDB password
- `GRAFANA_USER` - Grafana admin username
- `GRAFANA_PASSWORD` - Grafana admin password
- `GRAFANA_SECRET_KEY` - Secret key for signing cookies
- `GRAFANA_ROOT_URL` - Root URL for reverse proxy
- `GRAFANA_PORT` - Grafana port (default: 3000)
- `WEB_PORT` - Web UI port (default: 8080)
- `CORS_ORIGINS` - Allowed CORS origins
- `LOG_LEVEL` - Application log level
- `POLL_INTERVAL_DRONES` - Drone polling interval (seconds)
- `POLL_INTERVAL_STATUS` - Status polling interval (seconds)
- `MAX_RETRIES` - Max retry attempts for failed API calls
- `VOLUMES_PATH` - Path to persistent volumes

**Setup:**
```bash
cp .env.example .env
# Edit .env with strong passwords
chmod 600 .env
```

## Configuration Files

### config/kits.yaml
**Purpose:** Define WarDragon kits to monitor

**Structure:**
```yaml
kits:
  - id: kit-001
    name: "Mobile Unit Alpha"
    api_url: "http://192.168.1.100:8088"
    location: "Field Operations"
    enabled: true
```

### grafana/datasources/timescaledb.yaml
**Purpose:** Grafana datasource configuration

**Features:**
- Auto-provisioned TimescaleDB connection
- Uses Docker service name for connection
- Password from environment variable
- TimescaleDB-specific settings

### grafana/dashboards/dashboard-provider.yaml
**Purpose:** Grafana dashboard provisioning

**Features:**
- Auto-loads dashboards from `/var/lib/grafana/dashboards`
- Organized in "WarDragon Analytics" folder
- Allows UI updates

## Systemd Integration

### wardragon-analytics.service
**Purpose:** Systemd service unit for automatic startup

**Features:**
- Starts on boot after Docker
- Uses production compose file
- Runs as non-root user
- Integrates with system journal
- Automatic restart on failure

**Installation:**
```bash
sudo cp wardragon-analytics.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wardragon-analytics
sudo systemctl start wardragon-analytics
```

## Management Scripts

### Makefile
**Purpose:** Common Docker Compose operations

**Targets:**
- `make setup` - Initial setup
- `make start` - Start all services
- `make stop` - Stop all services
- `make restart` - Restart services
- `make logs` - View logs
- `make status` - Show service status
- `make health` - Check service health
- `make backup` - Backup database
- `make restore BACKUP_FILE=...` - Restore database
- `make shell-db` - Open psql shell
- `make clean` - Remove containers and volumes

### quickstart.sh
**Purpose:** Automated setup and deployment

**Features:**
- Checks prerequisites (Docker, docker-compose)
- Creates .env with generated passwords
- Creates necessary directories
- Pulls images and builds containers
- Starts services
- Waits for health checks
- Displays access information

**Usage:**
```bash
./quickstart.sh
```

### healthcheck.sh
**Purpose:** Comprehensive health check for all services

**Checks:**
- Docker containers running
- Service-specific health endpoints
- Database connectivity
- Disk space usage
- Container resource usage
- Database statistics

**Usage:**
```bash
./healthcheck.sh
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                          │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │        wardragon-net (172.20.0.0/16)              │ │
│  │                                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │  collector   │  │     web      │              │ │
│  │  │  (internal)  │  │  :8080       │◄─────────────┼─┤ External
│  │  └──────┬───────┘  └──────┬───────┘              │ │
│  │         │                 │                       │ │
│  │         ├─────────────────┤                       │ │
│  │         │                 │                       │ │
│  │  ┌──────▼─────────────────▼───────┐              │ │
│  │  │      timescaledb                │              │ │
│  │  │      :5432 (localhost only)     │              │ │
│  │  └──────┬──────────────────────────┘              │ │
│  │         │                                         │ │
│  │  ┌──────▼───────┐                                │ │
│  │  │   grafana    │                                │ │
│  │  │   :3000      │◄───────────────────────────────┼─┤ External
│  │  └──────────────┘                                │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  Volumes:                                               │
│  └─ timescale-data/  (PostgreSQL data)                 │
│  └─ grafana-data/    (Grafana config & dashboards)     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Security Features

### Network Security
- TimescaleDB bound to localhost only (127.0.0.1)
- Internal Docker network for service communication
- Only web and grafana exposed to host

### Authentication
- Strong password requirements in .env.example
- Grafana secret key for session security
- Database password-protected

### Data Security
- Volumes with restricted permissions (700)
- .env file excluded from git (.gitignore)
- Secure cookie settings in Grafana
- CORS configuration for web API

### Operational Security
- Health checks for all services
- Automatic restart on failure
- Log rotation configured
- Resource limits (production)

## Volume Management

### Creating Volumes
```bash
mkdir -p ./volumes/timescale-data ./volumes/grafana-data
chmod 700 ./volumes/timescale-data ./volumes/grafana-data
sudo chown -R 472:472 ./volumes/grafana-data  # Grafana user
```

### Backing Up Volumes
```bash
# Database
docker exec wardragon-timescaledb pg_dump -U wardragon wardragon | gzip > backup.sql.gz

# Grafana dashboards
tar -czf grafana-backup.tar.gz volumes/grafana-data/
```

### Restoring Volumes
```bash
# Database
gunzip -c backup.sql.gz | docker exec -i wardragon-timescaledb psql -U wardragon wardragon

# Grafana
tar -xzf grafana-backup.tar.gz -C volumes/
```

## Troubleshooting

### Services Won't Start
```bash
# Check Docker daemon
sudo systemctl status docker

# Check logs
docker-compose logs -f

# Verify .env file exists
ls -l .env

# Check port conflicts
sudo netstat -tlnp | grep -E ':(5432|8080|3000)'
```

### Database Connection Issues
```bash
# Test database
docker exec wardragon-timescaledb pg_isready -U wardragon

# Check database logs
docker-compose logs timescaledb

# Verify network
docker network inspect wardragon-net
```

### Permission Issues
```bash
# Fix volume permissions
sudo chown -R $(id -u):$(id -g) volumes/timescale-data
sudo chown -R 472:472 volumes/grafana-data
```

### Out of Space
```bash
# Check Docker disk usage
docker system df

# Clean up
docker system prune -a

# Check volume sizes
du -sh volumes/*
```

## Production Deployment Checklist

- [ ] Generate strong passwords in .env
- [ ] Configure kits.yaml with actual kit URLs
- [ ] Set CORS_ORIGINS to specific domains
- [ ] Set up reverse proxy (nginx/Traefik) with SSL
- [ ] Configure firewall rules
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Test backup/restore procedures
- [ ] Review SECURITY.md
- [ ] Document custom configurations
- [ ] Set up systemd service for auto-start

## Upgrading

### Pulling Latest Images
```bash
docker-compose pull
docker-compose up -d
```

### Rebuilding Application Containers
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Zero-Downtime Upgrade
```bash
# Backup first
make backup

# Pull new images
docker-compose pull

# Restart services one at a time
docker-compose up -d --no-deps --build web
docker-compose up -d --no-deps --build collector
docker-compose restart grafana
```

## Performance Tuning

### TimescaleDB
- Adjust shared_buffers (25% of RAM)
- Adjust effective_cache_size (50-75% of RAM)
- Tune work_mem for complex queries
- Enable compression for hypertables

### Collector
- Adjust POLL_INTERVAL_DRONES for lower latency
- Increase MAX_RETRIES for unstable networks
- Scale horizontally with multiple collector instances

### Web API
- Implement caching for frequent queries
- Adjust MAX_QUERY_RANGE_HOURS to prevent abuse
- Use connection pooling

### Grafana
- Use continuous aggregates for dashboards
- Limit dashboard time ranges
- Cache dashboard queries

## References

- Docker Compose: https://docs.docker.com/compose/
- TimescaleDB: https://docs.timescale.com/
- Grafana: https://grafana.com/docs/
- PostgreSQL: https://www.postgresql.org/docs/

## Support

See DEPLOYMENT.md for detailed deployment instructions.
See SECURITY.md for security hardening guidelines.
See README.md for project overview.
