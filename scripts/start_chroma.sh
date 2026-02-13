#!/usr/bin/env bash
# Start ChromaDB HTTP server for multi-process access
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load config
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Parse CHROMA_URL or use defaults
CHROMA_URL="${CHROMA_URL:-http://localhost:8000}"
HOST=$(echo "$CHROMA_URL" | sed -E 's|https?://([^:/]+).*|\1|')
PORT=$(echo "$CHROMA_URL" | sed -E 's|https?://[^:]+:([0-9]+).*|\1|')
[ "$PORT" = "$CHROMA_URL" ] && PORT="8000"

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/candlekeep/chroma"

# Use venv chroma
if [ -d "$PROJECT_DIR/.venv" ]; then
    CHROMA="$PROJECT_DIR/.venv/bin/chroma"
else
    CHROMA="chroma"
fi

# Check if already running
if curl -s "http://$HOST:$PORT/api/v2/heartbeat" > /dev/null 2>&1; then
    echo "ChromaDB server already running on $HOST:$PORT"
    exit 0
fi

echo "Starting ChromaDB server on $HOST:$PORT..."
echo "Data directory: $DATA_DIR"

# Start server in background
nohup $CHROMA run --host "$HOST" --port "$PORT" --path "$DATA_DIR" > /tmp/candlekeep_chroma.log 2>&1 &

# Wait for startup
for i in {1..10}; do
    if curl -s "http://$HOST:$PORT/api/v2/heartbeat" > /dev/null 2>&1; then
        echo "ChromaDB server started successfully"
        exit 0
    fi
    sleep 0.5
done

echo "Failed to start ChromaDB server. Check /tmp/candlekeep_chroma.log"
exit 1
