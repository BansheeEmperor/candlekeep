# Stage 1: Build the wheel
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir hatchling

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Build the wheel
RUN python -m pip wheel . --no-deps --wheel-dir /build/dist

# Stage 2: Final image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the wheel from builder
COPY --from=builder /build/dist/*.whl .
RUN pip install --no-cache-dir *.whl && rm *.whl

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Set environment variables for build and runtime
ENV XDG_DATA_HOME=/app/data
ENV CANDLEKEEP_TRANSPORT=http
ENV CANDLEKEEP_HTTP_HOST=0.0.0.0
ENV CANDLEKEEP_HTTP_PORT=8111
ENV CANDLEKEEP_DEVICE=cpu

# Create data directory
RUN mkdir -p /app/data

# Pre-download embedding models
COPY scripts/download_models.py /app/scripts/download_models.py
RUN python /app/scripts/download_models.py

# Expose the MCP server port
EXPOSE 8111

# The 'candlekeep' command is provided by the entry_point in pyproject.toml
ENTRYPOINT ["candlekeep"]
