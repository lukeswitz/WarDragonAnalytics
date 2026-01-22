#!/bin/bash
################################################################################
# backup.sh - Backup TimescaleDB data to compressed archive
#
# Description:
#   Creates a timestamped backup of the TimescaleDB database.
#   Outputs a compressed .sql.gz file to the backups/ directory.
#
# Usage:
#   ./scripts/backup.sh [output_directory]
#
# Examples:
#   ./scripts/backup.sh                    # Backup to ./backups/
#   ./scripts/backup.sh /mnt/usb/backups   # Backup to custom location
#
# Prerequisites:
#   - Database container must be running
#   - Sufficient disk space for backup
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

echo -e "${BLUE}WarDragon Analytics - Database Backup${NC}"
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

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Source .env to get DB_PASSWORD
export $(grep -v '^#' .env | xargs)

# Check if database container is running
if ! $DOCKER_COMPOSE ps | grep -q "timescaledb.*Up"; then
    echo -e "${RED}Error: TimescaleDB container is not running${NC}"
    echo "Start services first: ./scripts/start.sh"
    exit 1
fi

# Determine backup directory
BACKUP_DIR="${1:-$PROJECT_DIR/backups}"
mkdir -p "$BACKUP_DIR"

# Generate timestamp for backup filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/wardragon_analytics_${TIMESTAMP}.sql.gz"

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
echo "Output: $BACKUP_FILE"
echo ""

# Use pg_dump through docker exec, compress on the fly
$DOCKER_COMPOSE exec -T timescaledb pg_dump -U wardragon -d wardragon --clean --if-exists | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ] && [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo ""
    echo -e "${GREEN}Backup completed successfully!${NC}"
    echo ""
    echo "Backup file: $BACKUP_FILE"
    echo "Size: $BACKUP_SIZE"
    echo ""
    echo "To restore this backup:"
    echo "  gunzip -c $BACKUP_FILE | docker compose exec -T timescaledb psql -U wardragon -d wardragon"
    echo ""
else
    echo -e "${RED}Backup failed!${NC}"
    exit 1
fi

# Optional: Clean up old backups (keep last 7 days)
echo -e "${YELLOW}Checking for old backups...${NC}"
find "$BACKUP_DIR" -name "wardragon_analytics_*.sql.gz" -type f -mtime +7 -print | while read OLD_BACKUP; do
    echo "Removing old backup: $(basename "$OLD_BACKUP")"
    rm "$OLD_BACKUP"
done

echo -e "${GREEN}Done!${NC}"
