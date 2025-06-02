#!/bin/bash
# FocusQuest Service Runner
# Run the file watcher service with proper environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Set environment variables
export PYTHONPATH="$PROJECT_ROOT"
export CLAUDE_AUTO_ACCEPT=true
export CLAUDE_AUTO_APPROVE_PATHS="/home/puncher"

# Create required directories
mkdir -p "$PROJECT_ROOT/inbox"
mkdir -p "$PROJECT_ROOT/processed"
mkdir -p "$PROJECT_ROOT/data"
mkdir -p "$PROJECT_ROOT/analysis_sessions"
mkdir -p "$PROJECT_ROOT/logs"

# Run with logging
echo "Starting FocusQuest PDF Processing Service..."
echo "Logs: $PROJECT_ROOT/logs/service.log"

# Run the service
exec python -m src.core.enhanced_file_watcher "$@" 2>&1 | tee -a "$PROJECT_ROOT/logs/service.log"