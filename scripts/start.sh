#!/bin/bash
################################################################################
# start.sh - Start WarDragon Analytics services
#
# Description:
#   Starts all Docker containers in detached mode.
#   Runs pre-flight checks to ensure configuration is ready.
#
# Usage:
#   ./scripts/start.sh
#
# Prerequisites:
#   - .env file configured
#   - config/kits.yaml configured (if exists)
#   - Docker and Docker Compose installed
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

echo -e "${BLUE}WarDragon Analytics - Starting Services${NC}"
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
    echo "Please install Docker first."
    exit 1
fi

# Use modern 'docker compose' syntax
DOCKER_COMPOSE="$DOCKER_CMD compose"

# Check for docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found${NC}"
    echo "Make sure you're running this from the WarDragonAnalytics directory."
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    if [ -f ".env.example" ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo -e "${YELLOW}IMPORTANT: Edit .env and set your passwords!${NC}"
        exit 1
    else
        echo -e "${RED}Error: No .env.example found${NC}"
        exit 1
    fi
fi

# Check for kits.yaml (optional, warn if missing)
if [ ! -f "config/kits.yaml" ]; then
    echo -e "${YELLOW}Warning: config/kits.yaml not found${NC}"
    if [ -f "config/kits.yaml.example" ]; then
        echo "Consider creating config/kits.yaml from example:"
        echo "  cp config/kits.yaml.example config/kits.yaml"
        echo ""
        echo "Continuing anyway (collector will use defaults)..."
    fi
fi

# Pull latest images (optional, can comment out for offline use)
echo -e "${BLUE}Pulling latest Docker images...${NC}"
$DOCKER_COMPOSE pull || echo -e "${YELLOW}Warning: Could not pull images, using cached versions${NC}"

# Build custom images
echo -e "${BLUE}Building application images...${NC}"
$DOCKER_COMPOSE build

# Start services
echo -e "${BLUE}Starting containers...${NC}"
$DOCKER_COMPOSE up -d

# Wait for services to be healthy
echo ""
echo -e "${BLUE}Waiting for services to start...${NC}"
sleep 5

# Check container status
echo ""
echo -e "${GREEN}Container Status:${NC}"
$DOCKER_COMPOSE ps

# Display access information
echo ""
echo -e "${GREEN}=========================================="
echo "WarDragon Analytics is running!"
echo "==========================================${NC}"
echo ""
echo "Access the services at:"
echo -e "  ${BLUE}Web UI:${NC}  http://localhost:8090"
echo -e "  ${BLUE}Grafana:${NC} http://localhost:3000"
echo ""
echo "Default Grafana credentials:"
echo "  Username: admin"
echo "  Password: (set in .env file)"
echo ""
echo "View logs:"
echo "  ./scripts/logs.sh"
echo ""
echo "Stop services:"
echo "  ./scripts/stop.sh"
echo ""
