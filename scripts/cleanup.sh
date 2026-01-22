#!/bin/bash
################################################################################
# cleanup.sh - Complete cleanup of WarDragon Analytics
#
# Description:
#   Stops all Docker containers, removes volumes, and cleans all data.
#   WARNING: This will permanently delete all collected drone/signal data!
#
# Usage:
#   ./scripts/cleanup.sh [--keep-volumes]
#
# Options:
#   --keep-volumes    Stop containers but preserve database/grafana data
#
################################################################################

set -e  # Exit on error

# Color output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo -e "${YELLOW}WarDragon Analytics - Cleanup${NC}"
echo "=========================================="
echo ""

# Parse arguments
KEEP_VOLUMES=false
if [[ "$1" == "--keep-volumes" ]]; then
    KEEP_VOLUMES=true
fi

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

# Warning prompt
if [ "$KEEP_VOLUMES" = false ]; then
    echo -e "${RED}WARNING: This will permanently delete all data!${NC}"
    echo "  - All drone tracks"
    echo "  - All FPV signal detections"
    echo "  - All system health logs"
    echo "  - Grafana dashboards and settings"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi
fi

# Stop and remove containers
echo -e "${YELLOW}Stopping containers...${NC}"
$DOCKER_COMPOSE down

# Remove volumes if requested
if [ "$KEEP_VOLUMES" = false ]; then
    echo -e "${YELLOW}Removing volumes...${NC}"
    $DOCKER_COMPOSE down -v

    # Also remove named volumes explicitly
    docker volume rm wardragonanalytics_timescale-data 2>/dev/null || true
    docker volume rm wardragonanalytics_grafana-data 2>/dev/null || true

    echo -e "${GREEN}All data removed.${NC}"
else
    echo -e "${GREEN}Containers stopped (data preserved).${NC}"
fi

# Remove any orphaned containers
echo -e "${YELLOW}Cleaning up orphaned containers...${NC}"
docker container prune -f

# Remove any dangling images (optional)
echo -e "${YELLOW}Cleaning up dangling images...${NC}"
docker image prune -f

echo ""
echo -e "${GREEN}Cleanup complete!${NC}"
echo ""

if [ "$KEEP_VOLUMES" = true ]; then
    echo "Data volumes preserved. To remove them manually:"
    echo "  docker volume rm wardragonanalytics_timescale-data"
    echo "  docker volume rm wardragonanalytics_grafana-data"
fi
