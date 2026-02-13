#!/usr/bin/env bash
# Stop ChromaDB HTTP server
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load config
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Parse CHROMA_URL or use default
CHROMA_URL="${CHROMA_URL:-http://localhost:8000}"
PORT=$(echo "$CHROMA_URL" | sed -E 's|https?://[^:]+:([0-9]+).*|\1|')
[ "$PORT" = "$CHROMA_URL" ] && PORT="8000"

# Find and kill chroma process on port
PID=$(lsof -ti:$PORT 2>/dev/null || true)

if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null && echo "Stopped ChromaDB server (PID: $PID)" || echo "Failed to stop"
else
    echo "ChromaDB server not running on port $PORT"
fi
