#!/bin/bash
################################################################################
# logs.sh - Tail logs from all WarDragon Analytics services
#
# Description:
#   Shows live logs from all Docker containers with timestamps.
#   Press Ctrl+C to exit.
#
# Usage:
#   ./scripts/logs.sh [service_name] [options]
#
# Examples:
#   ./scripts/logs.sh                    # All services
#   ./scripts/logs.sh collector          # Only collector service
#   ./scripts/logs.sh -f --tail=50       # Follow with last 50 lines
#
# Available services:
#   - timescaledb
#   - collector
#   - web
#   - grafana
#
################################################################################

# Color output
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo -e "${BLUE}WarDragon Analytics - Service Logs${NC}"
echo "=========================================="
echo "Press Ctrl+C to exit"
echo ""

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo "Error: docker-compose or docker command not found"
    exit 1
fi

# Determine docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# If no arguments, show all logs with follow and timestamps
if [ $# -eq 0 ]; then
    $DOCKER_COMPOSE logs -f --tail=100 --timestamps
else
    # Pass all arguments to docker-compose logs
    $DOCKER_COMPOSE logs "$@"
fi
