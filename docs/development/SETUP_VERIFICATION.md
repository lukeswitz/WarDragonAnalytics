# Setup Verification Checklist

Use this checklist to verify your WarDragon Analytics Docker deployment is properly configured.

## File Verification

### Core Files
- [x] `docker-compose.yml` - Main compose configuration (5.2 KB)
- [x] `docker-compose.prod.yml` - Production overrides (2.2 KB)
- [x] `docker-compose.override.yml.example` - Dev template (1.9 KB)
- [x] `.env.example` - Environment template (3.5 KB)
- [x] `.gitignore` - Git exclusions (1.4 KB)

### Configuration Files
- [x] `config/kits.yaml` - Kit definitions (1.3 KB)
- [x] `grafana/datasources/timescaledb.yaml` - Datasource config (379 bytes)
- [x] `grafana/dashboards/dashboard-provider.yaml` - Dashboard config (277 bytes)

### Management Scripts
- [x] `Makefile` - Common operations (5.7 KB)
- [x] `quickstart.sh` - Automated setup (4.2 KB)
- [x] `healthcheck.sh` - Health monitoring (3.6 KB)

### Systemd Integration
- [x] `wardragon-analytics.service` - Systemd unit (1.6 KB)

### Documentation
- [x] `DEPLOYMENT.md` - Deployment guide (9.8 KB)
- [x] `SECURITY.md` - Security guidelines (9.1 KB)
- [x] `DOCKER_SETUP.md` - Docker reference (10.5 KB)
- [x] `DOCKER_COMPOSE_SUMMARY.md` - Complete summary (11.2 KB)

## Directory Structure Verification

```bash
WarDragonAnalytics/
├── docker-compose.yml              # Main compose file
├── docker-compose.prod.yml         # Production overrides
├── docker-compose.override.yml.example  # Dev template
├── .env.example                    # Environment template
├── .gitignore                      # Git exclusions
├── Makefile                        # Management commands
├── quickstart.sh                   # Automated setup
├── healthcheck.sh                  # Health monitoring
├── wardragon-analytics.service     # Systemd unit
├── DEPLOYMENT.md                   # Deployment guide
├── SECURITY.md                     # Security guide
├── DOCKER_SETUP.md                 # Docker reference
├── DOCKER_COMPOSE_SUMMARY.md       # Summary
├── config/
│   └── kits.yaml                   # Kit configuration
├── grafana/
│   ├── dashboards/
│   │   └── dashboard-provider.yaml # Dashboard provisioning
│   ├── datasources/
│   │   └── timescaledb.yaml        # Datasource config
│   └── dashboards-json/            # Dashboard JSON files (created)
├── logs/
│   └── collector/                  # Collector logs (created)
├── volumes/
│   ├── timescale-data/             # PostgreSQL data (created)
│   └── grafana-data/               # Grafana data (created)
├── app/                            # Application code
├── timescaledb/                    # Database init scripts
└── docs/                           # Documentation
```

## Configuration Verification

### 1. docker-compose.yml

#### Services Defined
- [ ] timescaledb (PostgreSQL 15 + TimescaleDB)
- [ ] collector (Python polling service)
- [ ] web (FastAPI interface)
- [ ] grafana (Visualization)

#### Service Features
- [ ] All services have health checks
- [ ] All services have restart policies
- [ ] TimescaleDB bound to localhost only (127.0.0.1:5432)
- [ ] Web and Grafana exposed to host
- [ ] Proper dependency order (depends_on)
- [ ] Environment variables from .env

#### Network Configuration
- [ ] Custom network "wardragon-net" defined
- [ ] Subnet configured (172.20.0.0/16)
- [ ] All services on same network

#### Volume Configuration
- [ ] timescale-data volume defined
- [ ] grafana-data volume defined
- [ ] Config files mounted read-only (:ro)
- [ ] Log directories mounted

### 2. .env.example

#### Required Variables
- [ ] DB_PASSWORD (with instructions)
- [ ] GRAFANA_PASSWORD (with instructions)
- [ ] GRAFANA_SECRET_KEY (with instructions)

#### Optional Variables
- [ ] LOG_LEVEL
- [ ] POLL_INTERVAL_DRONES
- [ ] POLL_INTERVAL_STATUS
- [ ] WEB_PORT
- [ ] GRAFANA_PORT
- [ ] CORS_ORIGINS
- [ ] MAX_RETRIES
- [ ] VOLUMES_PATH

#### Documentation
- [ ] Password generation instructions
- [ ] Security notes
- [ ] Production deployment notes

### 3. .gitignore

#### Critical Exclusions
- [ ] .env (security)
- [ ] volumes/ (data)
- [ ] logs/ (logs)
- [ ] backups/ (backups)
- [ ] docker-compose.override.yml (local config)

#### Python Exclusions
- [ ] __pycache__/
- [ ] *.pyc
- [ ] venv/

#### Security Exclusions
- [ ] *.pem, *.key, *.crt (SSL certs)
- [ ] config/*_secret.yaml

### 4. Makefile

#### Basic Commands
- [ ] help - Show help
- [ ] setup - Initial setup
- [ ] start - Start services
- [ ] stop - Stop services
- [ ] restart - Restart services
- [ ] status - Show status
- [ ] logs - View logs

#### Advanced Commands
- [ ] health - Health check
- [ ] backup - Backup database
- [ ] restore - Restore database
- [ ] clean - Clean up
- [ ] shell-db - Database shell
- [ ] db-stats - Database statistics

### 5. Security Features

#### Network Security
- [ ] TimescaleDB localhost-only binding
- [ ] Internal Docker network
- [ ] Minimal port exposure
- [ ] Ready for reverse proxy

#### Authentication
- [ ] Strong password requirements documented
- [ ] Password generation commands provided
- [ ] Grafana secret key required
- [ ] Anonymous access disabled in Grafana

#### Data Security
- [ ] .env in .gitignore
- [ ] volumes/ in .gitignore
- [ ] Volume permissions documented (700)
- [ ] Backup encryption documented

#### Operational Security
- [ ] Health checks configured
- [ ] Restart policies set
- [ ] Log rotation configured
- [ ] Resource limits (production)

## Functional Verification

### Pre-Deployment Checks

```bash
# Check file existence
ls -l docker-compose.yml
ls -l .env.example
ls -l Makefile
ls -l quickstart.sh
ls -l healthcheck.sh

# Check scripts are executable
[ -x quickstart.sh ] && echo "✓ quickstart.sh executable" || echo "✗ quickstart.sh not executable"
[ -x healthcheck.sh ] && echo "✓ healthcheck.sh executable" || echo "✗ healthcheck.sh not executable"

# Verify directory structure
[ -d config ] && echo "✓ config/ exists" || echo "✗ config/ missing"
[ -d grafana ] && echo "✓ grafana/ exists" || echo "✗ grafana/ missing"
[ -d volumes ] && echo "✓ volumes/ exists" || echo "✗ volumes/ missing"

# Check configuration files
[ -f config/kits.yaml ] && echo "✓ config/kits.yaml exists" || echo "✗ config/kits.yaml missing"
[ -f grafana/datasources/timescaledb.yaml ] && echo "✓ grafana datasource config exists" || echo "✗ grafana datasource missing"
```

### Docker Compose Validation

```bash
# Validate compose file syntax
docker-compose config > /dev/null && echo "✓ docker-compose.yml valid" || echo "✗ docker-compose.yml invalid"

# Check for required images
docker-compose config | grep -q "timescale/timescaledb:latest-pg15" && echo "✓ TimescaleDB image specified" || echo "✗ TimescaleDB image missing"
docker-compose config | grep -q "grafana/grafana:latest" && echo "✓ Grafana image specified" || echo "✗ Grafana image missing"

# Verify services are defined
docker-compose config --services | grep -q timescaledb && echo "✓ timescaledb service defined" || echo "✗ timescaledb service missing"
docker-compose config --services | grep -q collector && echo "✓ collector service defined" || echo "✗ collector service missing"
docker-compose config --services | grep -q web && echo "✓ web service defined" || echo "✗ web service missing"
docker-compose config --services | grep -q grafana && echo "✓ grafana service defined" || echo "✗ grafana service missing"
```

### Post-Deployment Checks

After running `./quickstart.sh` or `make start`:

```bash
# Check containers are running
docker-compose ps | grep -q "wardragon-timescaledb" && echo "✓ TimescaleDB running" || echo "✗ TimescaleDB not running"
docker-compose ps | grep -q "wardragon-collector" && echo "✓ Collector running" || echo "✗ Collector not running"
docker-compose ps | grep -q "wardragon-web" && echo "✓ Web running" || echo "✗ Web not running"
docker-compose ps | grep -q "wardragon-grafana" && echo "✓ Grafana running" || echo "✗ Grafana not running"

# Check health status
docker exec wardragon-timescaledb pg_isready -U wardragon && echo "✓ Database healthy" || echo "✗ Database unhealthy"
curl -sf http://localhost:8090/health && echo "✓ Web API healthy" || echo "✗ Web API unhealthy"
curl -sf http://localhost:3000/api/health && echo "✓ Grafana healthy" || echo "✗ Grafana unhealthy"

# Check volumes
docker volume ls | grep -q "timescale-data" && echo "✓ timescale-data volume exists" || echo "✗ timescale-data volume missing"
docker volume ls | grep -q "grafana-data" && echo "✓ grafana-data volume exists" || echo "✗ grafana-data volume missing"

# Check network
docker network ls | grep -q "wardragon-net" && echo "✓ wardragon-net network exists" || echo "✗ wardragon-net network missing"
```

## Security Verification

### Environment Security

```bash
# Check .env permissions
[ -f .env ] && [ "$(stat -c %a .env)" = "600" ] && echo "✓ .env has correct permissions (600)" || echo "⚠ .env should have 600 permissions"

# Verify .env not in git
git check-ignore .env > /dev/null && echo "✓ .env ignored by git" || echo "✗ .env NOT ignored by git (SECURITY RISK!)"

# Check volume permissions
[ -d volumes/timescale-data ] && [ "$(stat -c %a volumes/timescale-data)" = "700" ] && echo "✓ timescale-data has correct permissions (700)" || echo "⚠ timescale-data should have 700 permissions"
```

### Password Strength

```bash
# Check if default passwords are still present in .env
if [ -f .env ]; then
    grep -q "CHANGEME" .env && echo "✗ Default passwords still present in .env (MUST CHANGE!)" || echo "✓ Passwords updated in .env"
fi
```

### Network Exposure

```bash
# Check TimescaleDB is localhost-only
grep -q "127.0.0.1:5432:5432" docker-compose.yml && echo "✓ TimescaleDB bound to localhost only" || echo "✗ TimescaleDB exposed to network (SECURITY RISK!)"

# Check CORS is configured
[ -f .env ] && grep -q "CORS_ORIGINS" .env && echo "✓ CORS_ORIGINS configured" || echo "⚠ CORS_ORIGINS should be configured"
```

## Documentation Verification

### Required Documentation Present
- [ ] README.md - Project overview
- [ ] DEPLOYMENT.md - Deployment instructions
- [ ] SECURITY.md - Security guidelines
- [ ] DOCKER_SETUP.md - Docker reference
- [ ] DOCKER_COMPOSE_SUMMARY.md - Summary
- [ ] docs/ARCHITECTURE.md - Architecture design

### Documentation Quality
- [ ] Instructions are clear and actionable
- [ ] Examples provided where applicable
- [ ] Security considerations documented
- [ ] Troubleshooting sections included
- [ ] References to external resources

## Production Readiness Checklist

Before deploying to production:

### Security
- [ ] Strong passwords generated and set in .env
- [ ] .env file permissions set to 600
- [ ] CORS_ORIGINS set to specific domains (not *)
- [ ] Volume permissions set correctly
- [ ] .env excluded from git
- [ ] Review SECURITY.md completed

### Configuration
- [ ] config/kits.yaml configured with actual kits
- [ ] Polling intervals optimized
- [ ] Log levels appropriate for production
- [ ] Resource limits configured (docker-compose.prod.yml)
- [ ] Environment variables reviewed

### Infrastructure
- [ ] Reverse proxy configured with SSL
- [ ] Firewall rules configured
- [ ] Backup strategy implemented
- [ ] Monitoring/alerting configured
- [ ] Log rotation configured

### Testing
- [ ] All services start successfully
- [ ] Health checks pass
- [ ] Data collection working
- [ ] Grafana dashboards accessible
- [ ] Backup/restore tested
- [ ] Restart/recovery tested

### Documentation
- [ ] Deployment documented
- [ ] Access credentials documented (securely)
- [ ] Maintenance procedures documented
- [ ] Contact information updated
- [ ] Runbook created

## Automated Verification Script

Save this as `verify-setup.sh`:

```bash
#!/bin/bash
# Automated setup verification

echo "WarDragon Analytics Setup Verification"
echo "======================================="
echo ""

ERRORS=0
WARNINGS=0

check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1 exists"
    else
        echo "✗ $1 missing"
        ((ERRORS++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo "✓ $1/ exists"
    else
        echo "✗ $1/ missing"
        ((ERRORS++))
    fi
}

echo "Checking files..."
check_file "docker-compose.yml"
check_file ".env.example"
check_file ".gitignore"
check_file "Makefile"
check_file "quickstart.sh"
check_file "healthcheck.sh"
echo ""

echo "Checking directories..."
check_dir "config"
check_dir "grafana"
check_dir "volumes"
echo ""

echo "Checking configuration files..."
check_file "config/kits.yaml"
check_file "grafana/datasources/timescaledb.yaml"
check_file "grafana/dashboards/dashboard-provider.yaml"
echo ""

echo "Validating docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    echo "✓ docker-compose.yml is valid"
else
    echo "✗ docker-compose.yml is invalid"
    ((ERRORS++))
fi
echo ""

if [ -f .env ]; then
    echo "Checking .env security..."
    if grep -q "CHANGEME" .env; then
        echo "⚠ Default passwords still in .env"
        ((WARNINGS++))
    else
        echo "✓ Passwords updated"
    fi

    if [ "$(stat -c %a .env)" = "600" ]; then
        echo "✓ .env permissions correct (600)"
    else
        echo "⚠ .env permissions should be 600"
        ((WARNINGS++))
    fi
    echo ""
fi

echo "Summary:"
echo "--------"
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "✓ Setup verification passed!"
    exit 0
else
    echo "✗ Setup verification failed!"
    exit 1
fi
```

Run with:
```bash
chmod +x verify-setup.sh
./verify-setup.sh
```

## Quick Verification Commands

```bash
# One-liner to check everything
./healthcheck.sh && docker-compose ps && echo "✓ All systems operational"

# Verify git security
git check-ignore .env volumes/ logs/ && echo "✓ Sensitive files ignored"

# Verify compose file
docker-compose config > /dev/null && echo "✓ Compose file valid"

# Verify services
docker-compose ps | grep -c "Up" | grep -q "4" && echo "✓ All 4 services running"
```

## Success Indicators

Your setup is ready when:

1. ✅ All configuration files present
2. ✅ docker-compose.yml validates successfully
3. ✅ .env created with strong passwords
4. ✅ .env excluded from git
5. ✅ config/kits.yaml configured
6. ✅ All services start without errors
7. ✅ Health checks pass
8. ✅ Web UI accessible (http://localhost:8090)
9. ✅ Grafana accessible (http://localhost:3000)
10. ✅ Database accepting connections

## Need Help?

If verification fails:

1. Check logs: `docker-compose logs -f`
2. Review documentation: DEPLOYMENT.md, SECURITY.md
3. Run health check: `./healthcheck.sh`
4. Verify docker-compose: `docker-compose config`
5. Check permissions: `ls -la .env volumes/`

## Conclusion

This checklist ensures your WarDragon Analytics Docker deployment is:
- Properly configured
- Secure by default
- Production-ready
- Fully documented
- Easy to verify

Complete all items before deploying to production!
