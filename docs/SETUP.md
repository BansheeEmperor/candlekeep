# Candlekeep Setup Guide

## Prerequisites

- Python 3.10 or higher
- ChromaDB (local or remote)
- 2GB disk space for embedding models

## Local Development Setup

### 1. Clone and Install

```bash
cd /path/to/candlekeep
python3.10 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

pip install -e .
```

### 2. Run Setup

```bash
./scripts/setup.sh
```

This downloads:
- Embedding models (bge-small by default, ~130MB)
- spaCy language model (en_core_web_sm, ~15MB)

### 3. Configure

```bash
./scripts/configure.sh
```

Choose "Local development" mode for no authentication.

### 4. Start ChromaDB

```bash
./scripts/start_chroma.sh
```

Starts ChromaDB server on `localhost:8000`.

### 5. Run Candlekeep

```bash
candlekeep
```

The MCP server will start and verify database connectivity.

## Remote ChromaDB Setup

### On Remote Server

1. **Launch a server** (Ubuntu 22.04 or similar)

2. **Install dependencies:**
```bash
sudo apt update
sudo apt install python3-pip
pip3 install chromadb
```

3. **Create authentication token:**
```bash
sudo mkdir -p /etc/chroma
openssl rand -hex 32 | sudo tee /etc/chroma/tokens.txt
sudo chmod 600 /etc/chroma/tokens.txt
```

4. **Start ChromaDB with authentication:**
```bash
chroma run \
  --path /data/chroma \
  --host 0.0.0.0 \
  --port 8000 \
  --auth-provider token \
  --auth-token-file /etc/chroma/tokens.txt
```

5. **Configure security group:**
- Allow inbound TCP 8000 from your IP address
- Recommended: Use VPN or SSH tunnel for production

### On Local Machine

1. **Configure candlekeep:**
```bash
./scripts/configure.sh
```

Choose "Remote ChromaDB" and enter:
- URL: `http://your-server-hostname:8000`
- Token: (from `/etc/chroma/tokens.txt` on server)

2. **Test connection:**
```bash
candlekeep
```

Should show: `✓ Connected to http://your-server...`

## MCP Client Integration

HTTP mode is the recommended transport, even for single-agent local use. The server loads models once at startup (~6s), then every agent connection gets immediate access (~230ms first query). It also shares memory (one copy of models vs N copies in stdio), the BM25 cache, and the ChromaDB connection across all agents.

### HTTP mode (recommended)

A single Candlekeep process serves one or more agents. The operator starts the server; agents connect over HTTP.

**Start the server:**

```bash
# Localhost, no auth
CANDLEKEEP_TRANSPORT=http CANDLEKEEP_HTTP_PORT=8111 candlekeep

# With auth (recommended for non-localhost)
CANDLEKEEP_TRANSPORT=http CANDLEKEEP_MCP_TOKEN=your-token CANDLEKEEP_HTTP_PORT=8111 candlekeep
```

**Generate a token:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Agent-side config (no auth):**

```json
{
  "mcpServers": {
    "candlekeep": {
      "url": "http://localhost:8111/mcp"
    }
  }
}
```

**Agent-side config (with auth):**

```json
{
  "mcpServers": {
    "candlekeep": {
      "url": "http://localhost:8111/mcp",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

**Production (ASGI):**

```bash
CANDLEKEEP_MCP_TOKEN=your-token uvicorn candlekeep.mcp.server:app --host 0.0.0.0 --port 8111
```

FastMCP does not support HTTPS natively. For deployments where the server is not on the same host as the agents, TLS termination via a reverse proxy is the accepted approach. Configuration of the reverse proxy is out of scope for Candlekeep.

### stdio mode

Each agent spawns its own Candlekeep process. Simpler setup (no server to manage), but each agent pays ~6s cold-start and loads its own copy of the models into memory.

```json
{
  "mcpServers": {
    "candlekeep": {
      "command": "/path/to/candlekeep/.venv/bin/candlekeep",
      "args": [],
      "env": {
        "CANDLEKEEP_SPICE": "true"
      }
    }
  }
}
```

**Optional environment variables:**
- `CANDLEKEEP_SPICE`: Set to `"true"` for wizard sage persona (Elminster-style), or omit for professional mode

Restart your MCP client to load the server.

## Troubleshooting

### ChromaDB won't start
- Check if port 8000 is already in use: `lsof -i:8000`
- Check logs: `cat /tmp/candlekeep_chroma.log`

### Authentication failed
- Verify CHROMA_URL is correct in `.env`
- Verify CHROMA_AUTH_TOKEN matches server token
- Check firewall allows your IP

### Models not downloading
- Models must be downloaded before first run via `./scripts/setup.sh`
- Candlekeep will **not** download models at startup — it exits with an error if models are missing
- Check disk space: `df -h`
- To download manually: `python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"`

### Embedding model mismatch
- When connecting to a remote ChromaDB, Candlekeep auto-detects if the database was populated with a different embedding model
- It will override your local setting and log: `⚠ Remote DB uses 'X' embeddings, overriding local 'Y'`
- To re-ingest with a different model, use `repopulate_database` first

### Import errors
- Ensure virtual environment is activated
- Reinstall: `pip install -e .`
- Check Python version: `python3 --version` (must be >=3.10)

## Next Steps

- [Authentication Guide](AUTHENTICATION.md) - Configure auth tokens
- [Architecture](ARCHITECTURE.md) - Understand system design
- [README](../README.md) - MCP tools reference
