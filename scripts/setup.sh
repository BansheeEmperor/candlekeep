#!/usr/bin/env bash
# Setup script: Download embedding models and spaCy data
set -e

echo "=== Candlekeep Setup ==="
echo

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Not in a virtual environment"
    echo "Recommended: python3 -m venv .venv && source .venv/bin/activate"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install package
echo
echo "Installing candlekeep..."
pip install -e . -q

# Download spaCy model
echo
echo "Downloading spaCy model (en_core_web_sm)..."
python3 -m spacy download en_core_web_sm

# Download embedding model
echo
echo "Downloading embedding models (this may take a few minutes)..."
python3 << 'EOF'
from candlekeep.config import Settings
from candlekeep.database.embeddings import EmbeddingManager
from sentence_transformers import CrossEncoder

settings = Settings.from_env()
print(f"Bi-Encoder: {settings.embedding_model}")
embedder = EmbeddingManager.get_instance(settings)
embedder.get_model()

print(f"Cross-Encoder: ms-marco-MiniLM-L-6-v2")
# Trigger download of cross-encoder
CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
print("✓ Models downloaded")
EOF

echo
echo "=== Setup Complete ==="
echo
echo "Next steps:"
echo "1. Run: ./scripts/configure.sh"
echo "2. Start ChromaDB: ./scripts/start_chroma.sh"
echo "3. Run candlekeep: candlekeep"
