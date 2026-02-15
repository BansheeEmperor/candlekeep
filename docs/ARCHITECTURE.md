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
                             │ MCP Protocol (stdio)
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

Candlekeep uses MCP's **stdio transport**: each AI agent spawns its own MCP server process. This means every server instance handles exactly one agent — there is no concurrent request handling within a single process.

**Implications of the single-agent model:**

1. The simple and hybrid paths are stateless per-request. No concurrency guard is needed because only one request is in flight at a time.
2. The precise path runs PyTorch inference through a singleton cross-encoder. It is single-threaded by design — no concurrency guard is needed in the current stdio deployment.
3. Write operations (`ingest`, `delete`, `repopulate`) invalidate the BM25 cache and modify the ChromaDB collection. The BM25 index is rebuilt synchronously on the next hybrid query — this is intentional in single-agent mode, ensuring freshly ingested documents are immediately searchable via the hybrid path. ChromaDB handles its own collection-level locking; the quality gate and chunking pipeline run outside that lock but are safe because only one agent drives the process.
4. Multiple agents each get their own server process. They share the underlying ChromaDB instance, which handles concurrent access internally.

> **Shared-server deployments (future):** If Candlekeep moves to HTTP/SSE transport serving multiple agents from a single process, add a request queue or semaphore in front of the precise path to prevent cross-encoder serialization from stalling concurrent requests. Write operations would also need explicit serialization at the application layer.

### Security Boundary

| Threat | Mitigation |
|--------|-----------|
| Unauthorized MCP client | Not applicable — stdio transport binds one agent to one server process. ChromaDB bearer token is the auth boundary. For shared-server deployments, add per-agent auth at the gateway layer. |

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
| CHROMA_AUTH_TOKEN | (empty) | Bearer token for auth |
| CANDLEKEEP_EMBEDDING | bge-small | Embedding model (minilm, bge-small, nomic) |
| CANDLEKEEP_CHUNK_SIZE | 512 | Chunk size in characters |
| CANDLEKEEP_CHUNK_OVERLAP | 50 | Overlap between chunks |
| CANDLEKEEP_SPICE | false | Wizard persona mode |
| CANDLEKEEP_REMOTE_WRITE | false | Allow writes on remote DB |

## Performance Characteristics

| Metric | Target Value |
|--------|-------|
| Simple search latency (local) | < 100ms (~57ms measured) |
| Simple search latency (remote) | ~400ms |
| Precise search latency | ~175ms (Centurion Set, warm model, Relevance Ward pre-filtering active) |
| Content match (decomposed) | > 90% (legacy 23-query suite, Diary Entry 20) |
| Precision (simple) | > 85% |
| Scale tested | 2,770 chunks, 80 docs |

*Earlier Research Diary entries (12, 15) report precise-path latency of 1.5–1.7s. Those measurements predate the Relevance Ward pre-filtering optimization (Entry 16), which reduces the number of candidates scored by the cross-encoder.*

## Future Work

- **Multi-Agent Shared Server** — Evaluate whether a single MCP server serving multiple agents (via HTTP/SSE transport) is desirable. Tradeoffs: resource sharing and cache efficiency vs cross-encoder serialization, write contention, and operational complexity of per-agent isolation.
- **Incremental BM25 Updates** — The hybrid path's BM25 index is rebuilt from scratch after every write. At current corpus scale (~2,770 chunks) this is fast, but it scales linearly. Evaluate incremental add/remove operations on the BM25 index instead of full rebuild, or switch to a library that supports it natively (e.g., `whoosh`, `tantivy`). At current corpus scale (~2,770 chunks) the full rebuild is sub-second. At 50k+ chunks, the linear rebuild cost may introduce perceptible latency on the first hybrid query after a write. Measure rebuild time at target corpus size before deploying.

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
