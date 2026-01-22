#!/bin/bash
################################################################################
# stop.sh - Stop WarDragon Analytics services gracefully
#
# Description:
#   Stops all Docker containers gracefully, preserving data volumes.
#   Does NOT remove data - use cleanup.sh for that.
#
# Usage:
#   ./scripts/stop.sh
#
################################################################################

set -e  # Exit on error

# Color output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo -e "${BLUE}WarDragon Analytics - Stopping Services${NC}"
echo "=========================================="
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
    echo -e "${RED}Error: docker command not found${NC}"
    exit 1
fi

DOCKER_COMPOSE="$DOCKER_CMD compose"

# Stop containers gracefully
echo -e "${YELLOW}Stopping containers (this may take a few seconds)...${NC}"
$DOCKER_COMPOSE stop

echo ""
echo -e "${GREEN}All services stopped.${NC}"
echo ""
echo "Data volumes preserved. To start again:"
echo "  ./scripts/start.sh"
echo ""
echo "To remove containers completely (but keep data):"
echo "  docker compose down"
echo ""
echo "To remove everything including data:"
echo "  ./scripts/cleanup.sh"
echo ""
