# Docker Compose Setup - Complete Summary

## Overview

A production-ready Docker Compose configuration for WarDragon Analytics has been created with comprehensive security, monitoring, and deployment features.

## Files Created

### Core Docker Configuration

1. **docker-compose.yml** (5.2 KB)
   - Main Docker Compose configuration
   - 4 services: timescaledb, collector, web, grafana
   - Health checks for all services
   - Restart policies (unless-stopped)
   - Optimized PostgreSQL settings
   - Secure networking (TimescaleDB localhost-only)
   - Volume management for persistent data
   - Environment variable integration

2. **docker-compose.prod.yml** (2.2 KB)
   - Production-specific overrides
   - Resource limits (CPU/memory)
   - Enhanced logging with compression
   - Restart policies with backoff
   - Production environment variables

3. **docker-compose.override.yml.example** (1.9 KB)
   - Development environment template
   - Source code hot-reload
   - Debug logging
   - Exposed debugging ports
   - Verbose query logging

### Environment and Configuration

4. **.env.example** (3.5 KB)
   - Environment variable template
   - Comprehensive documentation
   - Security notes and best practices
   - Password generation instructions
   - All configurable parameters

5. **.gitignore** (1.4 KB)
   - Excludes .env files (security)
   - Excludes volumes/ (data)
   - Excludes logs/ and backups/
   - Python cache files
   - IDE files
   - SSL certificates
   - Docker override files

6. **config/kits.yaml** (1.3 KB)
   - WarDragon kit configuration
   - Example configurations
   - Documentation and security notes

7. **grafana/datasources/timescaledb.yaml** (379 bytes)
   - Auto-provisioned TimescaleDB datasource
   - Environment variable integration
   - TimescaleDB-specific settings

8. **grafana/dashboards/dashboard-provider.yaml** (277 bytes)
   - Dashboard auto-provisioning
   - Folder organization

### Management Scripts

9. **Makefile** (5.7 KB)
   - 20+ common operations
   - Simple commands: setup, start, stop, restart
   - Advanced: backup, restore, health checks
   - Database operations: shell access, stats, queries
   - Development mode support

10. **quickstart.sh** (4.2 KB)
    - Automated setup script
    - Prerequisite checking
    - Password generation
    - Directory creation
    - Service deployment
    - Health verification
    - Access information display

11. **healthcheck.sh** (3.6 KB)
    - Comprehensive health monitoring
    - Service-specific checks
    - Resource usage display
    - Database statistics
    - Color-coded output
    - Troubleshooting guidance

### Systemd Integration

12. **wardragon-analytics.service** (1.6 KB)
    - Systemd service unit
    - Auto-start on boot
    - Production compose file
    - Runs as non-root user
    - Journal integration
    - Resource limits (optional)

### Documentation

13. **DEPLOYMENT.md** (9.8 KB)
    - Complete deployment guide
    - Quick start instructions
    - Production deployment
    - Security hardening
    - Reverse proxy setup (nginx)
    - Maintenance procedures
    - Backup/restore
    - Troubleshooting
    - Performance tuning
    - Monitoring and alerting

14. **SECURITY.md** (9.1 KB)
    - Security checklist
    - Network security
    - Application security
    - Data security
    - Access control
    - Monitoring and auditing
    - Hardening steps (OS, Docker, DB, Grafana)
    - Incident response procedures
    - Compliance considerations
    - Regular maintenance schedule

15. **DOCKER_SETUP.md** (10.5 KB)
    - Complete Docker configuration reference
    - Service architecture
    - Network diagram
    - Volume management
    - Troubleshooting guide
    - Upgrade procedures
    - Performance tuning
    - Production checklist

## Service Architecture

### TimescaleDB (PostgreSQL 15)
- **Image:** timescale/timescaledb:latest-pg15
- **Port:** 127.0.0.1:5432 (localhost only)
- **Volume:** timescale-data (persistent)
- **Health Check:** pg_isready
- **Features:**
  - Optimized for time-series data
  - Tuned PostgreSQL parameters
  - Automatic hypertable partitioning
  - Data retention policies
  - Connection pooling

### Collector Service
- **Build:** ./app/Dockerfile (target: collector)
- **Function:** Polls WarDragon kit APIs
- **Depends On:** timescaledb
- **Health Check:** File-based (/tmp/collector_healthy)
- **Features:**
  - Configurable polling intervals
  - Retry logic with exponential backoff
  - Multi-kit support
  - Error handling and logging
  - Graceful degradation

### Web Service (FastAPI)
- **Build:** ./app/Dockerfile (target: web)
- **Port:** 8080
- **Depends On:** timescaledb
- **Health Check:** HTTP /health endpoint
- **Features:**
  - RESTful API
  - CORS configuration
  - Query time limits
  - Health endpoint
  - Async operations

### Grafana
- **Image:** grafana/grafana:latest
- **Port:** 3000
- **Depends On:** timescaledb
- **Volume:** grafana-data (persistent)
- **Health Check:** HTTP /api/health
- **Features:**
  - Pre-configured datasource
  - Dashboard provisioning
  - WorldMap plugin
  - Secure configuration
  - TimescaleDB integration

## Network Configuration

```
wardragon-net (bridge)
├── Subnet: 172.20.0.0/16
├── Services communicate internally
└── Only web:8080 and grafana:3000 exposed to host
```

## Security Features

### Network Security
✅ Database bound to localhost only
✅ Internal Docker network
✅ Minimal port exposure
✅ Firewall-ready configuration

### Authentication & Authorization
✅ Strong password requirements
✅ Password generation guidance
✅ Grafana secret key
✅ No anonymous access
✅ User sign-up disabled

### Data Security
✅ Volume permissions (700)
✅ .env excluded from git
✅ Secure cookies
✅ SSL-ready (reverse proxy)
✅ Backup encryption guidance

### Operational Security
✅ Health checks on all services
✅ Automatic restart policies
✅ Log rotation configured
✅ Resource limits (production)
✅ Audit logging

## Quick Start

```bash
# 1. Clone and navigate
cd WarDragonAnalytics

# 2. Run quick start (automated)
./quickstart.sh

# OR manual setup:
cp .env.example .env
# Edit .env with strong passwords
make setup
make start

# 3. Access services
# Web UI: http://localhost:8080
# Grafana: http://localhost:3000
```

## Common Operations

```bash
# Management
make status          # Check service status
make logs            # View all logs
make health          # Health check
make restart         # Restart services

# Database
make backup          # Backup database
make restore         # Restore from backup
make shell-db        # psql shell
make db-stats        # Database statistics

# Development
make dev-setup       # Setup dev environment
make dev-start       # Start in dev mode

# Cleanup
make stop            # Stop services
make clean           # Remove everything (WARNING!)
```

## Production Deployment

### Using Makefile
```bash
make setup
# Edit .env with production passwords
# Edit config/kits.yaml
make start
```

### Using Production Compose
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Using Systemd
```bash
sudo cp wardragon-analytics.service /etc/systemd/system/
# Edit service file with correct paths
sudo systemctl daemon-reload
sudo systemctl enable wardragon-analytics
sudo systemctl start wardragon-analytics
```

## Environment Variables

### Required
- `DB_PASSWORD` - Database password (generate: `openssl rand -base64 32`)
- `GRAFANA_PASSWORD` - Grafana admin password
- `GRAFANA_SECRET_KEY` - Session signing key

### Optional
- `LOG_LEVEL` - Application log level (default: INFO)
- `POLL_INTERVAL_DRONES` - Drone polling interval (default: 5s)
- `POLL_INTERVAL_STATUS` - Status polling interval (default: 30s)
- `WEB_PORT` - Web UI port (default: 8080)
- `GRAFANA_PORT` - Grafana port (default: 3000)
- `CORS_ORIGINS` - Allowed CORS origins (default: *)
- `MAX_QUERY_RANGE_HOURS` - Max query range (default: 168 hours)

## Volume Management

### Locations
- `./volumes/timescale-data` - PostgreSQL data files
- `./volumes/grafana-data` - Grafana dashboards and config

### Permissions
```bash
chmod 700 volumes/timescale-data
chmod 700 volumes/grafana-data
chown -R 472:472 volumes/grafana-data  # Grafana user
```

### Backups
```bash
# Automated
make backup

# Manual
docker exec wardragon-timescaledb pg_dump -U wardragon wardragon | \
  gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

## Health Monitoring

### Automated Health Check
```bash
./healthcheck.sh
```

### Manual Checks
```bash
# All services
docker-compose ps

# Database
docker exec wardragon-timescaledb pg_isready -U wardragon

# Web API
curl http://localhost:8080/health

# Grafana
curl http://localhost:3000/api/health
```

## Troubleshooting

### Services Won't Start
```bash
docker-compose logs <service-name>
docker-compose ps
```

### Database Issues
```bash
docker-compose logs timescaledb
docker exec wardragon-timescaledb pg_isready -U wardragon
```

### Permission Issues
```bash
sudo chown -R $(id -u):$(id -g) volumes/timescale-data
sudo chown -R 472:472 volumes/grafana-data
```

### Network Issues
```bash
docker network inspect wardragon-net
docker-compose down && docker-compose up -d
```

## Production Checklist

- [ ] Generate strong passwords in .env
- [ ] Set CORS_ORIGINS to specific domains
- [ ] Configure config/kits.yaml
- [ ] Set up reverse proxy with SSL
- [ ] Configure firewall
- [ ] Set up automated backups
- [ ] Enable systemd service
- [ ] Test backup/restore
- [ ] Review SECURITY.md
- [ ] Set up monitoring/alerting

## Architecture Highlights

### Scalability
- Horizontal scaling: Multiple collector instances
- Vertical scaling: Resource limits adjustable
- TimescaleDB hypertables for efficient time-series queries
- Connection pooling

### Reliability
- Health checks on all services
- Automatic restart policies
- Graceful degradation
- Retry logic with backoff
- Data persistence

### Observability
- Structured logging
- Health endpoints
- Resource monitoring
- Database statistics
- Grafana dashboards

### Security
- Network isolation
- Minimal attack surface
- Secret management
- Audit logging
- Security hardening guide

## Maintenance

### Daily
- Monitor logs: `make logs`
- Check health: `./healthcheck.sh`

### Weekly
- Backup database: `make backup`
- Check disk space: `df -h volumes/`

### Monthly
- Update images: `docker-compose pull`
- Review logs for errors
- Test backup restore
- Review security

### Quarterly
- Security audit
- Performance review
- Update dependencies
- Review documentation

## Support and Resources

### Documentation
- DEPLOYMENT.md - Deployment guide
- SECURITY.md - Security guidelines
- DOCKER_SETUP.md - Docker reference
- README.md - Project overview

### Commands
- `make help` - List all Makefile commands
- `./quickstart.sh` - Automated setup
- `./healthcheck.sh` - Health monitoring

### Logs
```bash
make logs              # All services
make logs-collector    # Collector only
make logs-web          # Web API only
make logs-grafana      # Grafana only
make logs-db           # Database only
```

## Success Criteria

A successful deployment should:
1. All services show HEALTHY in health check
2. Web UI accessible at http://localhost:8080
3. Grafana accessible at http://localhost:3000
4. Database accepting connections
5. Collector polling configured kits
6. No errors in logs
7. Volumes created with correct permissions
8. Services restart automatically on failure

## Next Steps

1. **Initial Setup:**
   ```bash
   ./quickstart.sh
   ```

2. **Configure Kits:**
   - Edit `config/kits.yaml`
   - Restart collector: `docker-compose restart collector`

3. **Access Services:**
   - Web UI: http://localhost:8080
   - Grafana: http://localhost:3000

4. **Production Deployment:**
   - Review DEPLOYMENT.md
   - Review SECURITY.md
   - Set up reverse proxy
   - Configure firewall
   - Enable systemd service

5. **Monitoring:**
   - Set up Grafana dashboards
   - Configure alerts
   - Monitor logs

## Conclusion

This Docker Compose setup provides a production-ready foundation for WarDragon Analytics with:
- Comprehensive security features
- Easy deployment and management
- Automated health monitoring
- Backup and recovery procedures
- Detailed documentation
- Development and production configurations

All configuration files follow best practices and include extensive inline documentation for maintainability.
