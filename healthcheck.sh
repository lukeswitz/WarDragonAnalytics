#!/bin/bash
# WarDragon Analytics Health Check Script
# Checks the health of all services and reports status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "WarDragon Analytics Health Check"
echo "=========================================="
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERROR: docker-compose not found${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Run 'make setup' to create it"
    exit 1
fi

# Function to check service health
check_service() {
    local service=$1
    local container=$2
    local check_cmd=$3

    echo -n "Checking $service... "

    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${RED}NOT RUNNING${NC}"
        return 1
    fi

    if eval "$check_cmd" &> /dev/null; then
        echo -e "${GREEN}HEALTHY${NC}"
        return 0
    else
        echo -e "${YELLOW}UNHEALTHY${NC}"
        return 1
    fi
}

# Track overall health
OVERALL_HEALTHY=0

# Check TimescaleDB
if ! check_service "TimescaleDB" "wardragon-timescaledb" "docker exec wardragon-timescaledb pg_isready -U wardragon"; then
    OVERALL_HEALTHY=1
    echo "  Issue: Database not ready or not responding"
fi

# Check Collector
if ! check_service "Collector" "wardragon-collector" "docker exec wardragon-collector ls /tmp/collector_healthy 2>/dev/null"; then
    OVERALL_HEALTHY=1
    echo "  Issue: Collector not healthy (check logs: docker-compose logs collector)"
fi

# Check Web API
if ! check_service "Web API" "wardragon-web" "curl -sf http://localhost:8080/health"; then
    OVERALL_HEALTHY=1
    echo "  Issue: Web API not responding on port 8080"
fi

# Check Grafana
if ! check_service "Grafana" "wardragon-grafana" "curl -sf http://localhost:3000/api/health"; then
    OVERALL_HEALTHY=1
    echo "  Issue: Grafana not responding on port 3000"
fi

echo ""
echo "=========================================="

# Check disk space
echo "Disk Usage:"
df -h volumes/ 2>/dev/null || echo "  Volumes directory not found"
echo ""

# Check Docker stats
echo "Container Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    wardragon-timescaledb wardragon-collector wardragon-web wardragon-grafana 2>/dev/null || \
    echo "  Unable to get container stats"
echo ""

# Database stats
if docker exec wardragon-timescaledb pg_isready -U wardragon &> /dev/null; then
    echo "Database Statistics:"
    docker exec wardragon-timescaledb psql -U wardragon wardragon -c "
        SELECT
            'Database Size' as metric,
            pg_size_pretty(pg_database_size('wardragon')) as value
        UNION ALL
        SELECT
            'Active Connections',
            count(*)::text
        FROM pg_stat_activity
        WHERE datname = 'wardragon';
    " 2>/dev/null || echo "  Unable to query database"
    echo ""
fi

# Service URLs
echo "Service URLs:"
echo "  Web UI:   http://localhost:8080"
echo "  Grafana:  http://localhost:3000"
echo ""

# Overall status
if [ $OVERALL_HEALTHY -eq 0 ]; then
    echo -e "${GREEN}Overall Status: HEALTHY${NC}"
    exit 0
else
    echo -e "${RED}Overall Status: UNHEALTHY${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check logs: docker-compose logs -f"
    echo "  2. Check status: docker-compose ps"
    echo "  3. Restart services: docker-compose restart"
    echo "  4. View full diagnostics: docker-compose logs"
    exit 1
fi
