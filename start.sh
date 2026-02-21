#!/bin/bash

# start.sh - Start the Claude Telegram Bridge bot
# Uses the project venv and runs bot.py in the background with PID tracking.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
PID_FILE="$PROJECT_DIR/bot.pid"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/bot.log"
BOT_SCRIPT="$PROJECT_DIR/bot.py"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
    log "ERROR: $1" >&2
    exit 1
}

# Check if bot is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log "Bot is already running (PID $OLD_PID). Use stop.sh first."
        exit 1
    else
        log "Stale PID file found (PID $OLD_PID not running). Cleaning up."
        rm -f "$PID_FILE"
    fi
fi

# Auto-create venv if it does not exist
if [ ! -f "$VENV_PYTHON" ]; then
    log "Virtual environment not found. Creating..."
    python3 -m venv "$VENV_DIR" || error_exit "Failed to create virtual environment"
    log "Upgrading pip..."
    "$VENV_PYTHON" -m pip install --upgrade pip --quiet || error_exit "Failed to upgrade pip"
    log "Installing dependencies..."
    "$VENV_PYTHON" -m pip install -r "$PROJECT_DIR/requirements.txt" --quiet || error_exit "Failed to install dependencies"
    log "Virtual environment ready."
else
    log "Virtual environment found at $VENV_DIR"
fi

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Verify bot.py exists
[ -f "$BOT_SCRIPT" ] || error_exit "bot.py not found at $BOT_SCRIPT"

# Verify .env exists
[ -f "$PROJECT_DIR/.env" ] || error_exit ".env file not found. Copy .env.example and configure it."

# Start the bot in the background
log "Starting Claude Telegram Bridge..."
nohup "$VENV_PYTHON" -u "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1 &
BOT_PID=$!

# Write PID file
echo "$BOT_PID" > "$PID_FILE"

# Brief pause to check if process survived startup
sleep 2
if kill -0 "$BOT_PID" 2>/dev/null; then
    log "Bot started successfully (PID $BOT_PID)"
    log "Logs: $LOG_FILE"
    log "Stop with: $PROJECT_DIR/stop.sh"
else
    log "ERROR: Bot process died immediately. Check logs:" >&2
    tail -20 "$LOG_FILE" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 1
fi
