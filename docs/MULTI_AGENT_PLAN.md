# Multi-Agent Shared Server: Design Plan

## 1. Problem Statement

Candlekeep runs one MCP server process per agent (stdio transport). Each process loads its own embedding model (~400MB), cross-encoder (~80MB), and BM25 cache (full corpus in memory). N agents = N× memory for identical models.

A shared server mode (HTTP transport) lets multiple agents connect to a single Candlekeep process, sharing models, caches, and the ChromaDB connection.

## 2. Goals

1. Add HTTP transport mode where one Candlekeep process serves multiple agents concurrently.
2. Keep stdio mode as the default. User chooses which mode to run.
3. Handle concurrent reads safely (parallel searches from different agents).
4. Serialize writes to prevent data corruption and BM25 cache races.
5. Support optional bearer token auth for HTTP mode.
6. Document agent-side `mcp.json` configuration for both modes.
7. Benchmark cross-encoder behavior under concurrent load before adding throttling.
8. Minimal changes to existing code — RAG pipeline, database layer, and tool logic stay the same.

## 3. Non-Goals

- Per-agent document isolation / multi-tenancy (all agents see the full corpus).
- Per-agent permission levels (single shared token).
- Horizontal scaling across multiple Candlekeep processes.
- OAuth / OIDC / external identity providers.

## 4. Current Architecture (Relevant Parts)

### 4.1 Transport

`FastMCP("candlekeep")` with `mcp.run()` → stdio. One agent, one process.

FastMCP supports `mcp.run(transport="http", host=..., port=...)` for Streamable HTTP, which handles multiple concurrent clients natively.

### 4.2 Shared Mutable State

| State | Location | Concurrency Risk |
|-------|----------|-----------------|
| `_store` (ChromaVectorStore) | `server.py` global | ChromaDB HttpClient handles its own locking. Reads safe. Writes need app-level serialization. |
| `_processor` (DocumentProcessor) | `server.py` global | Stateless per call. Safe. |
| `_bm25_cache` (BM25Searcher) | `hybrid.py` global | Has `threading.Lock()`. Write-then-read race possible but acceptable (see §5.5). |
| `EmbeddingManager._model` | `embeddings.py` class var | Singleton. `SentenceTransformer.encode()` is thread-safe. |
| `_cross_encoder` | `reranker.py` global | Singleton. PyTorch inference — needs benchmarking under concurrent load (see §5.4). |
| `_loading`, `_read_access`, `_write_access` | `server.py` globals | Set once during init, read-only after. Safe. |
| `metrics.json` | `vector_store.py` | File read/write without locking. Race condition under concurrent queries. Replace with in-memory counter (see §5.6). |

## 5. Proposed Design

### 5.1 Dual-Mode Entry Point

User picks mode via environment variable. Both modes use the same `mcp` instance and tool functions.

```
CANDLEKEEP_TRANSPORT=stdio   → current behavior (default)
CANDLEKEEP_TRANSPORT=http    → shared server mode
CANDLEKEEP_HTTP_HOST=0.0.0.0 → bind address (default: 127.0.0.1)
CANDLEKEEP_HTTP_PORT=8111    → port (default: 8111)
CANDLEKEEP_MCP_TOKEN=<token> → bearer token for HTTP auth (optional)
```

Implementation in `server.py`:

```python
def main():
    transport = os.getenv("CANDLEKEEP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.getenv("CANDLEKEEP_HTTP_HOST", "127.0.0.1")
        port = int(os.getenv("CANDLEKEEP_HTTP_PORT", "8111"))
        print(f"[candlekeep] Starting HTTP server on {host}:{port}", file=sys.stderr)
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()  # stdio
```

### 5.2 Server Lifecycle

**stdio mode (unchanged):** The MCP client (agent host) spawns Candlekeep as a subprocess. Agent lifecycle manages server lifecycle. Server dies when the agent disconnects.

**HTTP mode:** The server is a long-running process started independently by an operator — like any web service. Agents connect and disconnect freely. The operator is responsible for starting, stopping, and monitoring the process.

```bash
# Operator starts the server (localhost, no auth)
CANDLEKEEP_TRANSPORT=http \
CANDLEKEEP_HTTP_PORT=8111 \
  candlekeep

# With auth (recommended for non-localhost)
CANDLEKEEP_TRANSPORT=http \
CANDLEKEEP_MCP_TOKEN=my-secret-token \
CANDLEKEEP_HTTP_PORT=8111 \
  candlekeep

# Production with uvicorn (ASGI mode)
CANDLEKEEP_MCP_TOKEN=my-secret-token \
  uvicorn candlekeep.mcp.server:app --host 0.0.0.0 --port 8111
```

The ASGI entrypoint (`app = mcp.http_app()`) will be exposed from `server.py` for production deployments with uvicorn/gunicorn.

### 5.3 Authentication & TLS

**FastMCP does not support HTTPS natively.** For deployments where the server is not on the same host as the agents, TLS termination via a reverse proxy is the accepted approach. Configuration of the reverse proxy is out of scope for Candlekeep.

**Implication for auth:** On localhost, a bearer token over plaintext HTTP is fine — the token never hits the network. Over a network without TLS, the token is exposed. Rather than force auth on all users (including localhost-only setups), auth is optional.

**stdio mode:** No auth. The agent and server share a process boundary.

**HTTP mode:** Bearer token auth, optional. If `CANDLEKEEP_MCP_TOKEN` is set, auth is enforced. If not, the server starts without auth.

```python
from fastmcp.server.auth import StaticTokenVerifier

token = os.getenv("CANDLEKEEP_MCP_TOKEN")
if transport == "http":
    if token:
        auth = StaticTokenVerifier(tokens={token: {"sub": "candlekeep-agent"}})
        mcp = FastMCP("candlekeep", instructions=instructions, auth=auth)
        print("[candlekeep] Bearer token auth enabled", file=sys.stderr)
    else:
        mcp = FastMCP("candlekeep", instructions=instructions)
        print("[candlekeep] No auth configured (set CANDLEKEEP_MCP_TOKEN to enable)", file=sys.stderr)
```

**When to use auth:**

| Deployment | Auth needed? | TLS needed? |
|------------|:---:|:---:|
| Localhost, all agents on same machine | No | No |
| Local network, trusted agents | Recommended | No |
| Over the internet / untrusted network | Yes | Yes (reverse proxy, out of scope) |

**Token provisioning flow (when auth is enabled):**

1. Operator generates a token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Operator sets `CANDLEKEEP_MCP_TOKEN=<token>` in the server's `.env`.
3. Operator distributes the token to each agent's `mcp.json` config (see §5.8).
4. Server validates the token on every HTTP request. Invalid/missing token → 401.

### 5.4 Cross-Encoder Concurrency

The cross-encoder (`ms-marco-MiniLM-L-6-v2`) runs PyTorch inference on the precise path.

**Benchmark host:** Apple M2 Pro, 10 cores, 32 GB RAM, macOS. Corpus: 2,770 chunks, 80 documents. Warm model (post-startup).

**Pipeline stage breakdown (single request, MPS):**

| Stage | CPU | MPS |
|-------|----:|----:|
| Query embedding (bge-small) | 23ms | 20ms |
| ChromaDB vector search | 23ms | 18ms |
| Arcane Recall (expansion + stored embeddings) | 99ms | 88ms |
| Cross-encoder (15 candidates) | 326ms | 142ms |
| Full precise pipeline | 433ms | 232ms |

The cross-encoder is the largest single cost (75% on CPU, 61% on MPS), but Arcane Recall is also significant. Both stages are CPU/GPU-bound and contend for the GIL under concurrent load.

**Concurrent throughput (direct calls, no HTTP overhead, MPS):**

| Concurrency | p50 | p95 | Throughput | Ratio vs baseline |
|:-:|:-:|:-:|:-:|:-:|
| 1 | 240ms | 240ms | 4.2 qps | 1.0x |
| 2 | 168ms | 239ms | 8.4 qps | 1.0x |
| 3 | 253ms | 298ms | 10.1 qps | 1.3x |
| 5 | 972ms | 1204ms | 4.2 qps | 5.2x |
| 8 | 1438ms | 1642ms | 4.9 qps | 7.1x |
| 10 | 1854ms | 1910ms | 5.2 qps | 8.2x |

**End-to-end HTTP benchmark (includes session setup + serialization):**

CPU:

| Concurrency | p50 | p95 | Throughput | Ratio vs baseline |
|:-:|:-:|:-:|:-:|:-:|
| 1 | 471ms | 471ms | 2.1 qps | 1.0x |
| 2 | 622ms | 623ms | 3.2 qps | 1.3x |
| 3 | 811ms | 811ms | 3.7 qps | 1.7x |
| 5 | 1551ms | 1552ms | 3.2 qps | 3.3x |

MPS:

| Concurrency | p50 | p95 | Throughput | Ratio vs baseline |
|:-:|:-:|:-:|:-:|:-:|
| 1 | 277ms | 277ms | 3.6 qps | 1.0x |
| 2 | 373ms | 374ms | 5.3 qps | 1.3x |
| 3 | 567ms | 570ms | 5.3 qps | 2.1x |
| 5 | 1088ms | 1090ms | 4.6 qps | 3.9x |
| 10 | 2070ms | 2076ms | 4.8 qps | 7.5x |

**Why Semaphore(3):**

Throughput peaks at N=3 (10.1 qps direct, 5.3 qps over HTTP) on both CPU and MPS. At N=3, threads interleave naturally: one does I/O-bound ChromaDB calls while another does CPU/GPU-bound inference. At N=5, the CPU-bound stages (PyTorch inference, numpy cosine similarity in Arcane Recall) fight for the GIL and throughput collapses. The jump from N=3 to N=5 is a 4× latency increase with no throughput gain.

MPS does not help with concurrency — it's 2.3× faster per cross-encoder call but does not parallelize concurrent inference. The GIL is the ceiling, not the device.

`Semaphore(3)` caps precise-path concurrency at the throughput-optimal level. Requests beyond 3 queue instead of degrading all in-flight requests. Simple and hybrid paths are unaffected.

Note: this value was tuned on Apple M2 Pro (10 cores). On hosts with fewer cores, `Semaphore(2)` may be more appropriate. On hosts with more cores or CUDA GPUs, the optimal value may be higher. Re-run `scripts/benchmark_concurrent.py` on the target hardware to calibrate.

### 5.5 Write Serialization

A single `threading.Lock` serializes all write operations (`ingest`, `delete_document`, `repopulate_database`). Prevents:

- Two agents ingesting simultaneously (ChromaDB upsert race).
- Ingest overlapping with delete (BM25 cache invalidation race).

```python
_write_lock = threading.Lock()
```

Write tools acquire `_write_lock`. Read tools do not — ChromaDB handles read consistency internally, and the BM25 cache has its own lock.

**BM25 cache staleness:** After a write, the BM25 cache is invalidated. The next hybrid query rebuilds it. If agent A writes while agent B runs a hybrid query, B may use a stale cache. This is acceptable — the vector search component (primary retrieval) always reflects the latest state. BM25 is a supplementary signal. Same behavior as rapid ingest-then-search in single-agent mode.

### 5.6 Metrics: In-Memory Counter

The current `metrics.json` file tracks a single `total_queries` counter for the `get_stats` tool's "tokens saved" estimate. File-based read-modify-write is a race condition under concurrent queries.

**Replace with `threading` atomic counter:**

```python
import threading

class _QueryCounter:
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._count += 1

    @property
    def count(self):
        return self._count
```

The counter resets on server restart. For a vanity metric ("tokens saved this session"), this is fine. Remove the file-based `_load_metrics` / `_save_metrics` methods.

In stdio mode, the counter still works (uncontended lock, no overhead). Backward-compatible.

### 5.7 Configuration Changes

New fields in `Settings` dataclass (`config.py`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CANDLEKEEP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `CANDLEKEEP_HTTP_HOST` | `127.0.0.1` | HTTP bind address |
| `CANDLEKEEP_HTTP_PORT` | `8111` | HTTP port |
| `CANDLEKEEP_MCP_TOKEN` | (empty) | Bearer token for HTTP auth. Optional. If unset, HTTP mode runs without auth. |

### 5.8 Agent-Side Configuration (`mcp.json`)

Agents configure their MCP client to connect to Candlekeep. The config differs by mode.

**stdio mode (current, unchanged):**

```json
{
  "mcpServers": {
    "candlekeep": {
      "command": "candlekeep",
      "args": [],
      "env": {
        "CHROMA_URL": "http://localhost:8000",
        "CHROMA_AUTH_TOKEN": "your-chroma-token"
      }
    }
  }
}
```

Each agent spawns its own Candlekeep process. No shared state between agents.

**HTTP mode (localhost, no auth):**

```json
{
  "mcpServers": {
    "candlekeep": {
      "url": "http://localhost:8111/mcp"
    }
  }
}
```

**HTTP mode (with auth):**

```json
{
  "mcpServers": {
    "candlekeep": {
      "url": "http://localhost:8111/mcp",
      "headers": {
        "Authorization": "Bearer your-mcp-token-here"
      }
    }
  }
}
```

All agents point to the same URL. The server is already running (started by the operator). If `CANDLEKEEP_MCP_TOKEN` is set on the server, the bearer token in `headers` must match.

**Remote server (with TLS):**

```json
{
  "mcpServers": {
    "candlekeep": {
      "url": "https://candlekeep.internal.example.com/mcp",
      "headers": {
        "Authorization": "Bearer your-mcp-token-here"
      }
    }
  }
}
```

Same config, different URL.

### 5.9 Lock Interaction Matrix

| Operation | `_write_lock` | `_reranker_semaphore` | BM25 `_cache_lock` |
|-----------|:---:|:---:|:---:|
| `search` (simple) | — | — | — |
| `search` (hybrid) | — | — | ✓ (read) |
| `search` (precise) | — | ✓ | — |
| `ingest` | ✓ | — | ✓ (invalidate) |
| `delete_document` | ✓ | — | ✓ (invalidate) |
| `repopulate_database` | ✓ | — | ✓ (invalidate) |
| `list_documents` | — | — | — |
| `get_stats` | — | — | — |

No deadlock risk: no tool acquires more than one of `_write_lock` and `_reranker_semaphore`. The BM25 `_cache_lock` is always acquired inside a tool, never held across tools.

## 6. What Does NOT Change

- The RAG pipeline (`router.py`, `arcane_recall.py`, `hybrid.py`, `reranker.py`, `processor.py`).
- The database layer (`vector_store.py`, `embeddings.py`, `interface.py`) — except removing the file-based metrics.
- Tool function signatures and return values.
- The quality gate logic.
- ChromaDB connection setup.
- Embedding model loading (singleton, loaded once, shared by all agents).

The locks wrap existing tool functions at the `server.py` level. Everything below `server.py` is unaware of multi-agent mode.

## 7. Implementation Plan

### Phase 1: Dual-Mode Transport + Auth

Files: `server.py`, `config.py`

1. Add `transport`, `http_host`, `http_port`, `mcp_token` to `Settings`.
2. Modify `main()` to branch on transport mode.
3. Add `StaticTokenVerifier` when transport=http and token is set. No token = no auth.
4. Expose `app = mcp.http_app()` for ASGI deployments.
5. Log whether auth is enabled or not on startup.

Test: start HTTP mode with token, verify 401 without correct token. Start without token, verify open access.

### Phase 2: Write Serialization + Metrics

Files: `server.py`, `vector_store.py`

1. Add `_write_lock = threading.Lock()`.
2. Wrap `ingest`, `delete_document`, `repopulate_database` with `_write_lock`.
3. Replace file-based metrics with in-memory `_QueryCounter`.
4. Remove `_load_metrics`, `_save_metrics`, `metrics.json` dependency.

Test: two concurrent ingest calls succeed without corruption. Concurrent searches during ingest return results.

### Phase 3: Tests + Cross-Encoder Benchmark

Files: new `tests/test_multi_agent.py`, new `scripts/benchmark_concurrent.py`

1. Write tests covering the testing strategy from §9:
   - Smoke test: HTTP mode, one client, all 8 tools.
   - Auth enabled: 401 without token, 401 with wrong token, success with correct token.
   - Auth disabled: open access without token.
   - Concurrent reads: 5 parallel `search` calls (simple path).
   - Write contention: 2 parallel `ingest` calls, no corruption.
   - Read-during-write: ingest + search in parallel.
   - Stdio regression: existing stdio mode works identically.
2. Write cross-encoder benchmark script: N concurrent precise-path queries via HTTP.
3. Run on CPU with warm model, measure latency distribution.
4. Document results.
5. If degradation exceeds threshold (§5.4), add `threading.Semaphore` in a follow-up commit.

### Phase 4: Documentation

Files: `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/SETUP.md`, `.env.example`, `README.md`

1. Document HTTP mode startup and operator responsibilities.
2. Add `mcp.json` examples for both stdio and HTTP modes (with and without auth).
3. Update concurrency model section in ARCHITECTURE.md.
4. Update threat model in DESIGN.md (optional auth, TLS via reverse proxy).
5. Add new env vars to `.env.example`.
6. Document token generation and distribution workflow.
7. Note that TLS requires a reverse proxy when the server is not on the same host as the agents. Configuration of the reverse proxy is out of scope for Candlekeep.
8. Document the Semaphore(3) rationale in ARCHITECTURE.md: benchmark host specs (Apple M2 Pro, 10 cores, 32 GB), pipeline stage breakdown, concurrent throughput data, why N=3 is the GIL-optimal cap, and how to recalibrate on different hardware using `scripts/benchmark_concurrent.py`.

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cross-encoder stalls concurrent requests (CPU) | Confirmed at N=5 | Medium | `Semaphore(3)` caps precise-path concurrency at throughput-optimal level. |
| BM25 cache stale after concurrent write | Medium | Low | Vector search always fresh. BM25 is supplementary. Document as known behavior. |
| Bearer token leaked over plaintext HTTP | Medium (if used over network without TLS) | High | Auth is optional. TLS is the operator's responsibility for non-localhost deployments. |
| No auth on localhost | Low | Low | Localhost-only traffic. Acceptable for dev/single-machine setups. |
| Memory pressure from many agents | Low | Medium | Models shared. Per-request allocations are small and short-lived. |
| FastMCP HTTP transport bugs | Low | High | Pin FastMCP version. Test with multiple concurrent clients. |

## 9. Testing Strategy

1. **Smoke test**: Start HTTP mode without token, connect one client, run all 8 tools.
2. **Auth enabled**: Start with token, verify 401 without token, verify 401 with wrong token, verify success with correct token.
3. **Auth disabled**: Start without token, verify open access works.
3. **Concurrent reads**: 5 parallel `search` calls (simple path). All return correct results.
4. **Write contention**: 2 parallel `ingest` calls. Both succeed, no duplicate chunks.
5. **Read-during-write**: Agent A ingests while Agent B searches. B gets results (possibly stale BM25, fresh vector).
6. **Precise-path benchmark**: Phase 3 benchmark script (§5.4).
7. **Stdio regression**: Existing stdio mode works identically. Locks uncontended, no overhead.

## 10. Future Considerations

- **Per-agent auth**: Map different tokens to agent IDs. Filter tool visibility per agent (read-only agents).
- **Rate limiting**: Prevent a single agent from monopolizing resources.
- **Connection limits**: Cap max concurrent MCP sessions.
- **Token rotation**: Support multiple valid tokens during rotation window.
- **ASGI workers**: For high-throughput deployments, run with `uvicorn --workers N`. Requires `stateless_http=True` in FastMCP (no server-side session state). Write lock would need to be cross-process (e.g., file lock or Redis). Out of scope for single-process mode.
