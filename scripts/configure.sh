#!/usr/bin/env bash
# Interactive configuration script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

echo "=== Candlekeep Configuration ==="
echo

# Check if .env exists
if [ -f "$ENV_FILE" ]; then
    echo "Found existing .env file"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing configuration"
        exit 0
    fi
fi

# Deployment mode
echo
echo "Select deployment mode:"
echo "1) Local development (no authentication)"
echo "2) Remote ChromaDB (with authentication)"
read -p "Choice (1-2): " MODE

if [ "$MODE" = "1" ]; then
    # Local mode
    CHROMA_URL="http://localhost:8000"
    CHROMA_AUTH_TOKEN=""
    echo
    echo "Local mode selected"
else
    # Remote mode
    echo
    read -p "ChromaDB URL (e.g., https://your-server:8000): " CHROMA_URL
    read -p "Authentication token: " CHROMA_AUTH_TOKEN
fi

# Embedding model
echo
echo "Select embedding model:"
echo "1) bge-small (recommended, 130MB, best accuracy)"
echo "2) minilm (fast, 80MB)"
echo "3) nomic (large, 270MB, 8192 token context)"
read -p "Choice (1-3, default 1): " MODEL_CHOICE

case "$MODEL_CHOICE" in
    2) EMBEDDING="minilm" ;;
    3) EMBEDDING="nomic" ;;
    *) EMBEDDING="bge-small" ;;
esac

# Write .env file
cat > "$ENV_FILE" << EOF
# ChromaDB Connection
CHROMA_URL=$CHROMA_URL
CHROMA_AUTH_TOKEN=$CHROMA_AUTH_TOKEN

# Embedding Model (minilm, bge-small, nomic)
CANDLEKEEP_EMBEDDING=$EMBEDDING

# Document Processing
CANDLEKEEP_CHUNK_SIZE=512
CANDLEKEEP_CHUNK_OVERLAP=50
EOF

echo
echo "✓ Configuration saved to .env"
echo
echo "Settings:"
echo "  CHROMA_URL: $CHROMA_URL"
echo "  Embedding: $EMBEDDING"
echo
echo "Next steps:"
if [ "$MODE" = "1" ]; then
    echo "1. Start ChromaDB: ./scripts/start_chroma.sh"
    echo "2. Run candlekeep: candlekeep"
else
    echo "1. Ensure ChromaDB is running on remote server"
    echo "2. Run candlekeep: candlekeep"
fi
