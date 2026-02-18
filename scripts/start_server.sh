#!/usr/bin/env bash
# Start Candlekeep HTTP server via uvicorn.
#
# Usage:
#   scripts/start_server.sh              # 1 worker (default)
#   scripts/start_server.sh 4            # 4 workers
#   scripts/start_server.sh --stop       # stop running server
#
# Loads .env from the project root. Requires ChromaDB to be running.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PIDFILE="/tmp/candlekeep_server.pid"
LOGFILE="/tmp/candlekeep_server.log"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Force HTTP transport
export CANDLEKEEP_TRANSPORT=http

HOST="${CANDLEKEEP_HTTP_HOST:-127.0.0.1}"
PORT="${CANDLEKEEP_HTTP_PORT:-8111}"

# Resolve uvicorn
if [ -d "$PROJECT_DIR/.venv" ]; then
    UVICORN="$PROJECT_DIR/.venv/bin/uvicorn"
else
    UVICORN="uvicorn"
fi

# ── Stop ─────────────────────────────────────────────────────────────

stop_server() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping Candlekeep server (PID $PID)..."
            kill "$PID"
            # Wait for clean shutdown
            for i in {1..10}; do
                kill -0 "$PID" 2>/dev/null || break
                sleep 0.5
            done
            if kill -0 "$PID" 2>/dev/null; then
                echo "Force killing..."
                kill -9 "$PID" 2>/dev/null
            fi
            rm -f "$PIDFILE"
            echo "Stopped."
            return 0
        fi
        rm -f "$PIDFILE"
    fi
    echo "No running server found."
    return 0
}

if [ "$1" = "--stop" ] || [ "$1" = "stop" ]; then
    stop_server
    exit 0
fi

# ── Parse workers ────────────────────────────────────────────────────

WORKERS="${1:-1}"

if ! [[ "$WORKERS" =~ ^[0-9]+$ ]]; then
    echo "Error: workers must be a positive integer, got '$WORKERS'"
    echo "Usage: $0 [WORKERS]    e.g. $0 4"
    exit 1
fi

if [ "$WORKERS" -lt 1 ] || [ "$WORKERS" -gt 32 ]; then
    echo "Error: workers must be between 1 and 32, got $WORKERS"
    exit 1
fi

# ── Preflight checks ────────────────────────────────────────────────

# Check uvicorn exists
if ! command -v "$UVICORN" &>/dev/null; then
    echo "Error: uvicorn not found. Install with: pip install uvicorn"
    exit 1
fi

# Check ChromaDB is reachable
CHROMA_URL="${CHROMA_URL:-http://localhost:8000}"
if ! curl -s "${CHROMA_URL}/api/v2/heartbeat" >/dev/null 2>&1; then
    echo "Error: ChromaDB not reachable at $CHROMA_URL"
    echo "Start it with: scripts/start_chroma.sh"
    exit 1
fi

# Check port is free (or we own it)
if lsof -i ":$PORT" >/dev/null 2>&1; then
    if [ -f "$PIDFILE" ]; then
        OLD_PID=$(cat "$PIDFILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "Candlekeep already running on port $PORT (PID $OLD_PID)."
            echo "Stop it first: $0 --stop"
            exit 1
        fi
        rm -f "$PIDFILE"
    fi
    echo "Error: port $PORT is already in use by another process."
    echo "Check with: lsof -i :$PORT"
    exit 1
fi

# Estimate memory
MODEL_MB=480  # bge-small (~400MB) + cross-encoder (~80MB)
TOTAL_MB=$((WORKERS * MODEL_MB))
echo "Starting Candlekeep: $WORKERS worker(s) on $HOST:$PORT"
echo "  ChromaDB: $CHROMA_URL"
echo "  Estimated model memory: ~${TOTAL_MB}MB ($WORKERS × ${MODEL_MB}MB)"
echo "  Log: $LOGFILE"

# ── Start ────────────────────────────────────────────────────────────

nohup "$UVICORN" candlekeep.mcp.server:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level warning \
    > "$LOGFILE" 2>&1 &

SERVER_PID=$!
echo "$SERVER_PID" > "$PIDFILE"

# Wait for the server to respond
echo -n "Waiting for server"
for i in {1..30}; do
    # Try an MCP-level health check via a simple HTTP request
    if curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$PORT/" 2>/dev/null | grep -qE "200|404|405"; then
        echo ""
        echo "Candlekeep server ready (PID $SERVER_PID, $WORKERS worker(s))"
        echo ""
        echo "  MCP endpoint: http://$HOST:$PORT/mcp"
        echo "  Stop with:    $0 --stop"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "Warning: server started but not responding after 30s."
echo "Check logs: tail -50 $LOGFILE"
echo "PID: $SERVER_PID"
exit 1
