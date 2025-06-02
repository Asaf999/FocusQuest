#!/bin/bash
# Install FocusQuest systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/focusquest-watcher.service"

echo "Installing FocusQuest PDF Processing Service..."

# Copy service file to systemd directory
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable focusquest-watcher.service

echo "Service installed successfully!"
echo ""
echo "Available commands:"
echo "  Start service:   sudo systemctl start focusquest-watcher"
echo "  Stop service:    sudo systemctl stop focusquest-watcher"
echo "  Check status:    sudo systemctl status focusquest-watcher"
echo "  View logs:       sudo journalctl -u focusquest-watcher -f"
echo ""
echo "Or run manually:  $SCRIPT_DIR/run_service.sh"