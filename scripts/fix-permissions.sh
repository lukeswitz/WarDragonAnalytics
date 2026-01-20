#!/bin/bash
################################################################################
# fix-permissions.sh - Fix script permissions
#
# Description:
#   Makes all shell scripts in the scripts directory executable.
#   Run this if you get "Permission denied" errors.
#
# Usage:
#   bash scripts/fix-permissions.sh
#
################################################################################

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Fixing script permissions..."

chmod +x "$SCRIPT_DIR/cleanup.sh"
chmod +x "$SCRIPT_DIR/start.sh"
chmod +x "$SCRIPT_DIR/stop.sh"
chmod +x "$SCRIPT_DIR/logs.sh"
chmod +x "$SCRIPT_DIR/reset-db.sh"
chmod +x "$SCRIPT_DIR/backup.sh"
chmod +x "$SCRIPT_DIR/fix-permissions.sh"

echo "Done! All scripts are now executable."
echo ""
echo "You can now run:"
echo "  ./scripts/start.sh"
echo "  ./scripts/stop.sh"
echo "  ./scripts/logs.sh"
echo "  ./scripts/backup.sh"
echo "  ./scripts/reset-db.sh"
echo "  ./scripts/cleanup.sh"
