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

# Find docker command
DOCKER_CMD=""
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
elif [ -x /usr/bin/docker ]; then
    DOCKER_CMD="/usr/bin/docker"
elif [ -x /usr/local/bin/docker ]; then
    DOCKER_CMD="/usr/local/bin/docker"
fi

if [ -z "$DOCKER_CMD" ]; then
    echo "Error: docker command not found"
    exit 1
fi

DOCKER_COMPOSE="$DOCKER_CMD compose"

# If no arguments, show all logs with follow and timestamps
if [ $# -eq 0 ]; then
    $DOCKER_COMPOSE logs -f --tail=100 --timestamps
else
    # Pass all arguments to docker compose logs
    $DOCKER_COMPOSE logs "$@"
fi
