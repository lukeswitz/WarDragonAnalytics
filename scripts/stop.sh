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

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker-compose or docker command not found${NC}"
    exit 1
fi

# Determine docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

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
echo "  docker-compose down"
echo ""
echo "To remove everything including data:"
echo "  ./scripts/cleanup.sh"
echo ""
