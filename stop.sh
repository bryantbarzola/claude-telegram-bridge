#!/bin/bash

# stop.sh - Stop the Claude Telegram Bridge bot

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PID_FILE="$PROJECT_DIR/bot.pid"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

if [ ! -f "$PID_FILE" ]; then
    log "No PID file found. Bot does not appear to be running."
    exit 0
fi

BOT_PID=$(cat "$PID_FILE")

if ! kill -0 "$BOT_PID" 2>/dev/null; then
    log "Process $BOT_PID is not running. Cleaning up stale PID file."
    rm -f "$PID_FILE"
    exit 0
fi

log "Stopping bot (PID $BOT_PID)..."

# Send SIGTERM for graceful shutdown
kill "$BOT_PID"

# Wait up to 10 seconds for graceful shutdown
TIMEOUT=10
while [ $TIMEOUT -gt 0 ]; do
    if ! kill -0 "$BOT_PID" 2>/dev/null; then
        break
    fi
    sleep 1
    TIMEOUT=$((TIMEOUT - 1))
done

# Force kill if still running
if kill -0 "$BOT_PID" 2>/dev/null; then
    log "Process did not stop gracefully. Sending SIGKILL..."
    kill -9 "$BOT_PID"
    sleep 1
fi

rm -f "$PID_FILE"
log "Bot stopped."
