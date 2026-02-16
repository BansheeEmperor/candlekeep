# Candlekeep Architecture

## Overview

Candlekeep is a RAG (Retrieval-Augmented Generation) knowledge base server that provides semantic search and document management via the Model Context Protocol (MCP). It connects to ChromaDB for vector storage and uses bge-small-en-v1.5 embeddings with a 2-path adaptive search router.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   MCP Client (AI Agent)                 │
│                                                         │
│  • Picks query_type (simple/hybrid/precise)             │
│  • Decomposes complex queries into multiple searches    │
│  • Synthesizes results across searches                  │
└────────────────────────────┬────────────────────────────┘
                             │ MCP Protocol (stdio or HTTP)
┌────────────────────────────▼────────────────────────────┐
│                  Candlekeep MCP Server                  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Read Tools              Write Tools             │   │
│  │  • search              • ingest (+ quality gate) │   │
│  │  • list_documents      • delete_document         │   │
│  │  • get_stats           • repopulate_database     │   │
│  │  • critique_document                             │   │
│  │  • generate_documentation                        │   │
│  └──────────────────────────┬───────────────────────┘   │
└─────────────────────────────┼───────────────────────────┘
                              │
                    [ SEARCH ROUTER DECISION ]
                    (simple | hybrid | precise)
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              RAG Pipeline (Processing)                  │
│                                                         │
│  Ingestion:                                             │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐          │
│  │ Quality  │→ │ Processor │→ │    Bardic    │          │
│  │ Gate     │  │ (chunking)│  │  Knowledge   │          │
│  └──────────┘  └───────────┘  └──────────────┘          │
│                                                         │
│  Retrieval:                                             │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐          │
│  │ Vector   │→ │  Arcane   │→ │    Divine    │          │
│  │ Search   │  │  Recall   │  │    Insight   │          │
│  └──────────┘  └───────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│           Database Layer (Storage)                      │
│  ┌────────────────┐  ┌────────────────────────┐         │
│  │ ChromaVectorDB │  │ EmbeddingManager       │         │
│  │ • search       │  │ • bge-small-en-v1.5    │         │
│  │ • CRUD ops     │  │ • model detection      │         │
│  └────────────────┘  └────────────────────────┘         │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│              ChromaDB (local or remote)                 │
│  • HNSW cosine similarity index                         │
│  • Collection metadata stores embedding_model           │
└─────────────────────────────────────────────────────────┘
```

### Search Pipeline Components

The library routes queries to the optimal technique stack:
*   **simple** → [Arcane Recall](GLOSSARY.md#arcane-recall) (Fast Path)
*   **hybrid** → [Wild Magic](GLOSSARY.md#lexical-matching-bm25) (Lexical + Vector). BM25 uses stop-word-filtered tokenization with a regex that preserves technical identifiers (e.g., `bge-small`, `v3.4.1`).
*   **precise** → [Arcane Recall](GLOSSARY.md#arcane-recall) + [Divine Insight](GLOSSARY.md#cross-encoder-reranking) (Precise Path)
*   **Negation preprocessing** applied to all paths.
*   **[The Relevance Ward](GLOSSARY.md#the-relevance-ward)** filters low-confidence matches.
*   **[Bardic Knowledge](GLOSSARY.md#bardic-knowledge)**: Ingestion-time context enrichment.
*   **[Quality Gate](#1-quality-gate)**: Strict validation of incoming documentation.

## The [Three Roads](#the-three-roads)

Candlekeep provides three distinct search paths through the library, allowing the agent to choose between speed, lexical precision, and semantic depth.

```
            [ INPUT QUERY ]
                   │
         ┌─────────▼─────────┐
         │ Negation Removal  │
         └─────────┬─────────┘
                   │
         SEARCH ROUTER DECISION
         ┌─────────┼─────────┐
         │         │         │
  [ ROAD 1 ]    [ ROAD 2 ]    [ ROAD 3 ]
  [ SIMPLE ]    [ HYBRID ]    [ PRECISE ]
  (Fast Path)   (Lexical)     (Semantic)
     │             │             │
┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│ Vector  │   │ Vector  │   │ Vector  │
│ Search  │   │   +     │   │ Search  │
└────┬────┘   │ BM25    │   └────┬────┘
     │        └────┬────┘        │
     │             ▼             │
     │        ┌─────────┐        │
     │        │  Rank   │        │
     │        │ Fusion  │        │
     │        └────┬────┘        │
     │             │             │
┌────▼─────────────▼─────────────▼────┐
│            Arcane Recall            │
│        (Weighted Expansion)         │
└────┬─────────────┬─────────────┬────┘
     │             │             │
┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│ Relevance│  │Relevance│   │  Divine │
│   Ward   │  │  Ward   │   │ Insight │
└────┬────┘   └────┬────┘   └────┬────┘
     │             │             │
     └─────────────┼─────────────┘
                   ▼
            [ FINAL RESULTS ]
```

### [Arcane Recall](GLOSSARY.md#arcane-recall) (Similarity-Weighted Expansion)
Every search result undergoes a contextual ritual to expand its vision. Instead of a fixed window, Arcane Recall now uses [**The Scholar's Discernment**](GLOSSARY.md#the-scholars-discernment) and [**Arcane Coalescence**](GLOSSARY.md#arcane-coalescence) to provide context without bloat.

```
DOCUMENT SOURCE
┌───────────────────────────────────────────────────────────────────────────┐
│ [C0]  [C1]  [C2]  [C3]  [C4]  [C5]  [C6]  [C7]  [C8]  [C9]  [C10] [C11] ...
└───────────────────────────────────────────────────────────────────────────┘
          │           │                       │
    MATCH #2 (C1)     MATCH #1 (C3)           MATCH #3 (C8)
          ▼           ▼                       ▼
    ┌───────────┐┌───────────┐          ┌───────────┐
    │  Chunk 1  ││  Chunk 3  │          │  Chunk 8  │
    └───────────┘└───────────┘          └───────────┘
          │           │                       │
          │     ARCANE COALESCENCE      SCHOLAR'S DISCERNMENT
          ▼           ▼                       ▼
    ┌───────────────────────┐          ┌─────────────┐
    │    DIVINE WINDOW      │          │ PRUNED WIN  │
    │ [C0][C1][C2][C3][C4]  │          │ [C7][C8]    │ (C9 rejected:
    └───────────────────────┘          └─────────────┘  low similarity)
                │                             │
                └──────────────┬──────────────┘
                               ▼
                      [ FINAL RESULTS ]
               (Exactly n_results sections)
```

- [**Arcane Coalescence**](GLOSSARY.md#arcane-coalescence): If multiple results come from the same section of a document, they are merged into a single cohesive Divine Window, preventing redundant text and saving tokens.
- [**The Scholar's Discernment**](GLOSSARY.md#the-scholars-discernment): Neighboring chunks are only included if they are semantically related to thy query (based on a similarity threshold) or contain continuation markers (like Markdown lists).
- **Global Capping**: The library ensures exactly `n_results` merged sections are returned, backfilling from the candidate pool as needed.

**Impact:**
- Content match: significantly improved over raw search
- Token efficiency: reduced context size vs fixed expansion
- Latency overhead: minimal (due to batched similarity checks)

### 4. [Divine Insight](GLOSSARY.md#cross-encoder-reranking) (cross-encoder reranking) — precise path only
Cross-encoder (`ms-marco-MiniLM-L-6-v2`) rescores all candidates by examining query-document pairs individually. Higher precision but trades content match and adds latency.

### 5. [The Relevance Ward](GLOSSARY.md#the-relevance-ward) (Filtering)
Results below a configured similarity threshold (see [Tuned Parameters](#tuned-parameters-reference)) are filtered to prevent the AI agent from hallucinating based on low-confidence "junk" matches.

- **Adversarial queries:** Score significantly lower than legitimate ones.
- **Status:** Zero false negatives on baseline benchmarks (no legitimate query returns empty results). Adversarial queries are fully filtered on the hybrid path (Hit Rate@5 = 0.0). On simple and precise paths, adversarial queries may return low-relevance results that score above the vector threshold — see BENCHMARK_RESULTS.md footnote 1 for per-path adversarial Hit Rate.

## Tuned Parameters (Reference)

These values represent the optimal configuration identified through the Centurion Set audit.

| Parameter | Current Value | Purpose |
|-----------|---------------|---------|
| `MIN_RELEVANCE_SCORE` | 0.75 | The Relevance Ward threshold (vector) |
| `HYBRID_RELEVANCE_THRESHOLD` | 0.03 | The Relevance Ward threshold (hybrid RRF) |
| `EXPANSION_SIMILARITY_THRESHOLD` | 0.92 | Scholar's Discernment (8% similarity gap) |
| `CHUNK_SIZE` | 512 | Target character count per fragment |
| `CHUNK_OVERLAP` | 50 | Character overlap between fragments |

Chunk size, overlap, and expansion parameter sweeps were conducted on the current corpus (~2,770 chunks from ~89 technical documentation files). Performance surfaces were flat across tested ranges (Diary Entries 21, 28, 29), indicating these defaults are robust for similar corpora. For corpora with substantially different document length, structure, or domain, re-run parameter sweeps before deploying. See [Threshold Calibration](#threshold-calibration) for Relevance Ward recalibration guidance.

### Threshold Calibration

The Relevance Ward thresholds are corpus-dependent heuristics. When deploying against a new corpus, recalibrate as follows:

1. Run the Centurion benchmark (or equivalent adversarial + legitimate query set) against the new corpus.
2. Record the score distribution for adversarial vs legitimate queries. For the vector path, examine raw cosine similarity scores. For the hybrid path, examine RRF fusion scores.
3. Set `MIN_RELEVANCE_SCORE` at the midpoint of the gap between the lowest legitimate score and the highest adversarial score. The original calibration (Research Diary, Entry 16) found a clean statistical separation at 0.75.
4. Set `HYBRID_RELEVANCE_THRESHOLD` based on the RRF score distribution of adversarial queries. The hybrid path's BM25 component naturally suppresses out-of-domain noise, so this threshold is typically much lower than the vector threshold.
5. If the gap between adversarial and legitimate scores is narrow (< 0.05 for vector, < 0.01 for hybrid), consider increasing the corpus quality or adding domain-specific negative examples to the benchmark set.

## Scalability

Candlekeep is designed for sub-linear scaling, ensuring that search performance remains stable even as the knowledge base grows by orders of magnitude.

### Performance at Scale
Benchmark results demonstrate that the `simple` search path is highly resilient to corpus growth:
- **Small Corpus (9 docs, ~178 chunks):** ~30ms avg latency
- **Medium Corpus (89 docs, ~2,770 chunks):** ~57ms avg latency
- **Scaling Efficiency:** A 15× increase in data resulted in less than 2× increase in latency.

*Latency measured on CPU with warm model, similarity-weighted expansion (Scholar's Discernment) active, using stored embeddings from ChromaDB.*

This efficiency is achieved through the $O(\log N)$ search complexity of ChromaDB's HNSW index and Candlekeep's optimized Arcane Recall phase, which performs direct per-document lookups instead of full database scans.

### Stable Precise Path
The `precise` path latency remains stable regardless of corpus size, as the cross-encoder reranking bottleneck is constrained to a fixed number of top candidates.

### Concurrency Model

Candlekeep supports two transport modes. HTTP mode is recommended even for single-agent local use:

- Cold-start: the server loads models once (~6s), then every agent gets immediate access (~230ms first query). In stdio mode, each agent pays the full ~6s cold-start.
- Memory: stdio with N agents loads N copies of the embedding model (~400MB) and cross-encoder (~80MB). HTTP mode loads one copy.
- BM25 cache: each stdio process rebuilds the BM25 index from scratch on the first hybrid query. HTTP mode builds it once, shared across agents.
- ChromaDB connections: N stdio processes = N persistent connections. HTTP mode = 1.

**HTTP mode (recommended):** A single Candlekeep process serves one or more agents via `mcp.run(transport="http")`. The operator starts the server independently; agents connect over HTTP. Models, caches, and the ChromaDB connection are shared across all agents.

**stdio mode:** Each AI agent spawns its own MCP server process via `mcp.run()`. One agent per process. All concurrency guards are uncontended. Each process loads its own models and pays cold-start latency independently.

```
stdio mode:                          HTTP mode:
┌─────────┐   ┌──────────────┐       ┌─────────┐
│ Agent A │──▶│ Candlekeep A │       │ Agent A │──┐
└─────────┘   └──────────────┘       └─────────┘  │
┌─────────┐   ┌──────────────┐       ┌─────────┐  │  ┌──────────────┐
│ Agent B │──▶│ Candlekeep B │       │ Agent B │──┼─▶│ Candlekeep   │
└─────────┘   └──────────────┘       └─────────┘  │  │ (shared)     │
┌─────────┐   ┌──────────────┐       ┌─────────┐  │  └──────────────┘
│ Agent C │──▶│ Candlekeep C │       │ Agent C │──┘
└─────────┘   └──────────────┘       └─────────┘
  3 processes, 3× model memory         1 process, 1× model memory
```

**Concurrency controls in HTTP mode:**

| Control | Scope | Purpose |
|---------|-------|---------|
| `_write_lock` (`threading.Lock`) | Write tools (ingest, delete, repopulate) | Prevents concurrent writes from corrupting ChromaDB state or racing on BM25 cache invalidation. |
| `_reranker_semaphore` (`threading.Semaphore(3)`) | Precise-path search | Caps concurrent cross-encoder inference at the throughput-optimal level. See [Precise Path Concurrency](#precise-path-concurrency) for benchmark data. |
| BM25 `_cache_lock` (`threading.Lock`) | Hybrid-path BM25 cache | Existing lock, protects cache reads/rebuilds. |

Read operations (simple search, hybrid search, list_documents, get_stats) run without locks against ChromaDB, which handles its own collection-level consistency.

**BM25 cache staleness:** After a write, the BM25 cache is invalidated. The next hybrid query rebuilds it. Under concurrent load, an agent may briefly use a stale BM25 cache if another agent writes between cache invalidation and rebuild. This is acceptable — the vector search component (primary retrieval) always reflects the latest state. BM25 is a supplementary signal.

### Precise Path Concurrency

The precise path runs the full pipeline (embedding → vector search → Arcane Recall → Relevance Ward → cross-encoder) in a single thread. Under concurrent load, GIL contention between CPU-bound stages (PyTorch inference, numpy cosine similarity) limits throughput.

**Benchmark host:** Apple M2 Pro, 10 cores, 32 GB RAM. Corpus: 2,770 chunks, 80 documents.

**Pipeline stage breakdown (single request):**

| Stage | CPU | MPS |
|-------|----:|----:|
| Query embedding (bge-small) | 23ms | 20ms |
| ChromaDB vector search | 23ms | 18ms |
| Arcane Recall (expansion + stored embeddings) | 99ms | 88ms |
| Cross-encoder (15 candidates) | 326ms | 142ms |
| Full precise pipeline | 433ms | 232ms |

**Concurrent throughput (direct calls, MPS):**

| Concurrency | p50 | p95 | Throughput |
|:-:|:-:|:-:|:-:|
| 1 | 240ms | 240ms | 4.2 qps |
| 2 | 168ms | 239ms | 8.4 qps |
| 3 | 253ms | 298ms | 10.1 qps |
| 5 | 972ms | 1204ms | 4.2 qps |
| 8 | 1438ms | 1642ms | 4.9 qps |
| 10 | 1854ms | 1910ms | 5.2 qps |

Throughput peaks at N=3 (10.1 qps). At N=5, CPU-bound stages fight for the GIL and throughput collapses. `Semaphore(3)` caps precise-path concurrency at the optimal level. Requests beyond 3 queue instead of degrading all in-flight requests.

This value was tuned on Apple M2 Pro (10 cores). On hosts with fewer cores, `Semaphore(2)` may be more appropriate. Re-run `scripts/benchmark_concurrent.py` on the target hardware to calibrate.

### Security Boundary

| Threat | Mitigation |
|--------|-----------|
| Unauthorized MCP client (stdio) | Not applicable — stdio transport binds one agent to one server process. |
| Unauthorized MCP client (HTTP) | Optional bearer token auth via `CANDLEKEEP_MCP_TOKEN`. If set, agents must present the token in the `Authorization` header. |
| Bearer token over plaintext HTTP | Acceptable on localhost. For non-localhost deployments, TLS via reverse proxy is the operator's responsibility. |
| Unauthorized ChromaDB access | Bearer token auth via `CHROMA_AUTH_TOKEN`. |

## Ingestion Pipeline

### 1. Quality Gate
Documents are validated before ingestion:
- YAML frontmatter required (title, description, keywords)
- At least 2 markdown headers
- Between 100 and 10,000 words
- No unclosed code blocks

Rejected documents get specific error messages. Agent can fix and retry.

### 2. Document Processing
- Text extraction (markdown, PDF, plain text)
- YAML frontmatter parsing
- Markdown header-aware chunking (splits at `##` boundaries, falls back to 512-char fixed chunks)

### 3. Bardic Knowledge (contextual embeddings)
Before embedding, each chunk is prefixed with document metadata:
`"Document: {title}. Description: {description}.\n\n{chunk text}"`

This is an ingestion-time technique — the context is baked into the stored embeddings. It improved precision significantly with zero latency cost.

## Tool Registration

All 8 tools (5 read-only, 3 write) are registered at startup. Database permissions (e.g., Bearer tokens for ChromaDB) determine whether write operations succeed.

| Category | Tools |
|-----------|-----------|
| Read Tools | search, list_documents, get_stats, critique_document, generate_documentation |
| Write Tools | ingest, delete_document, repopulate_database |

## Embedding Model Protection

### Mismatch Detection
On connection, the collection metadata is checked for `embedding_model`. If the remote DB was populated with a different model than the local config, the local setting is overridden and a warning is logged. This prevents silent quality degradation from incompatible vector spaces.

### No Download at Startup
The embedding model must exist in the local cache before startup. If missing, the server exits immediately with a clear error instead of downloading large models and blocking the MCP client.

## Agent Decomposition Pattern

Complex multi-document queries are the agent's responsibility to decompose. The search tool description instructs the agent:

> "For complex multi-part questions, make multiple simple searches (one per sub-question) and synthesize the results yourself."

Benchmarked: Agent decomposition achieves significantly higher content match on multi-doc queries compared to a single search (simulated benchmark, Entry 20; see Entry 25 for qualitative production validation). The agent fires searches in parallel and synthesizes across results.

This pattern assumes the calling agent is a frontier-class LLM (e.g., Claude, GPT-4) capable of identifying multi-part queries and issuing parallel searches. For weaker models, integrators should add explicit decomposition instructions to the agent's system prompt or implement a thin wrapper that pre-splits compound queries before calling the search tool.

## Known Failure Modes

### Agent Misrouting

The agent selects the search path (`simple`, `hybrid`, or `precise`) based on its interpretation of the query. If the agent selects `simple` for a query containing exact technical identifiers where `hybrid` would be more appropriate, retrieval quality degrades silently.

**Measured impact:** On the Centurion Set, lexical queries (containing version numbers, error codes, technical identifiers) show MRR of 0.42 on the simple path vs 0.53 on the hybrid path — a 26% gap. Semantic queries show no meaningful difference between paths.

**When to prefer hybrid:** Queries containing exact identifiers (`bge-small`, `v3.4.1`), error codes (`0xEF`, `ECONNREFUSED`), version strings, or technical terms that must match literally rather than semantically.

**No feedback mechanism:** The system does not signal to the agent whether its path selection was optimal. The agent cannot learn from misroutes within a session. Integrators should include path selection guidance in the agent's system prompt.

## Configuration

All settings via environment variables (`.env` file):

| Variable | Default | Purpose |
|----------|---------|---------|
| CHROMA_URL | http://localhost:8000 | ChromaDB endpoint |
| CHROMA_AUTH_TOKEN | (empty) | Bearer token for ChromaDB auth |
| CANDLEKEEP_EMBEDDING | bge-small | Embedding model (minilm, bge-small, nomic) |
| CANDLEKEEP_CHUNK_SIZE | 512 | Chunk size in characters |
| CANDLEKEEP_CHUNK_OVERLAP | 50 | Overlap between chunks |
| CANDLEKEEP_SPICE | false | Wizard persona mode |
| CANDLEKEEP_REMOTE_WRITE | false | Allow writes on remote DB |
| CANDLEKEEP_TRANSPORT | stdio | Transport mode: `stdio` or `http` |
| CANDLEKEEP_HTTP_HOST | 127.0.0.1 | HTTP bind address (HTTP mode only) |
| CANDLEKEEP_HTTP_PORT | 8111 | HTTP port (HTTP mode only) |
| CANDLEKEEP_MCP_TOKEN | (empty) | Bearer token for MCP auth (HTTP mode, optional) |

## Performance Characteristics

| Metric | Target Value |
|--------|-------|
| Simple search latency (local) | < 100ms (~57ms measured) |
| Simple search latency (remote) | ~400ms |
| Precise search latency | ~175ms (Centurion Set, warm model, Relevance Ward pre-filtering active) |
| Cold-start latency (process spawn to result) | ~5,825ms (CPU, cold model) |
| Content match (decomposed) | > 90% (legacy 23-query suite, Diary Entry 20) |
| Precision (simple) | > 85% |
| Scale tested | 2,770 chunks, 80 docs |

*Earlier Research Diary entries (12, 15) report precise-path latency of 1.5–1.7s. The improvement to the current figure (175ms) reflects two concurrent changes: (1) Relevance Ward pre-filtering (Entry 16), which reduces the number of candidates scored by the cross-encoder, and (2) transition from the 23-query suite to the Centurion Set (different query mix and corpus size). The individual contribution of each factor has not been isolated.*

## Future Work

- **Incremental BM25 Updates** — The hybrid path's BM25 index is rebuilt from scratch after every write. At current corpus scale (~2,770 chunks) this is fast, but it scales linearly. Evaluate incremental add/remove operations on the BM25 index instead of full rebuild, or switch to a library that supports it natively (e.g., `whoosh`, `tantivy`). At current corpus scale (~2,770 chunks) the full rebuild is sub-second. At 50k+ chunks, the linear rebuild cost may introduce perceptible latency on the first hybrid query after a write. Measure rebuild time at target corpus size before deploying.
- **Per-agent auth** — Map different tokens to agent IDs. Filter tool visibility per agent (read-only agents).
- **Rate limiting** — Prevent a single agent from monopolizing the cross-encoder in HTTP mode.

## File Structure

```
src/candlekeep/
├── __init__.py              # Entry point
├── __main__.py              # CLI runner
├── config.py                # Settings from env vars
├── database/
│   ├── interface.py         # Abstract VectorDatabase
│   ├── vector_store.py      # ChromaDB implementation
│   └── embeddings.py        # Model loading + caching
├── rag/
│   ├── router.py            # Adaptive query routing
│   ├── search.py            # Negation preprocessing
│   ├── arcane_recall.py     # Similarity-weighted expansion
│   ├── reranker.py          # Cross-encoder reranking
│   ├── processor.py         # Document chunking + Bardic Knowledge
│   └── extractor.py         # Entity extraction (spaCy)
└── mcp/
    └── server.py            # MCP tools + conditional registration
```
