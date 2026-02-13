# Candlekeep Architecture

## Overview

Candlekeep is a RAG (Retrieval-Augmented Generation) knowledge base server that provides semantic search and document management via the Model Context Protocol (MCP). It connects to ChromaDB for vector storage and uses bge-small-en-v1.5 embeddings with a 2-path adaptive search router.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   MCP Client (AI Agent)                  │
│                                                          │
│  • Picks query_type (simple/precise)                     │
│  • Decomposes complex queries into multiple searches     │
│  • Synthesizes results across searches                   │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol (stdio)
┌────────────────────▼────────────────────────────────────┐
│                  Candlekeep MCP Server                   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Read Tools              Write Tools             │  │
│  │  • search              • ingest (+ quality gate)  │  │
│  │  • list_documents      • delete_document          │  │
│  │  • get_stats           • repopulate_database      │  │
│  │  • critique_document                              │  │
│  │  • generate_documentation                         │  │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────▼───────────────────────────────┐   │
│  │                Search Router                      │   │
│  │                                                   │   │
│  │  query_type="simple"  → Arcane Recall (~23ms)     │   │
│  │  query_type="precise" → Arcane Recall + Divine    │   │
│  │                         Insight reranking (~1.5s)  │   │
│  │                                                   │   │
│  │  Negation preprocessing on all paths              │   │
│  │  Relevance threshold (0.65) filters garbage       │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────▼───────────────────────────────┐   │
│  │              RAG Pipeline                         │   │
│  │                                                   │   │
│  │  Ingestion:                                       │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │   │
│  │  │ Quality  │→ │ Processor │→ │  Bardic      │  │   │
│  │  │ Gate     │  │ (chunk at │  │  Knowledge   │  │   │
│  │  │          │  │  512 char)│  │  (context    │  │   │
│  │  │          │  │           │  │   prefix)    │  │   │
│  │  └──────────┘  └───────────┘  └──────────────┘  │   │
│  │                                                   │   │
│  │  Retrieval:                                       │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │   │
│  │  │ Vector   │→ │ Arcane    │→ │ Divine       │  │   │
│  │  │ Search   │  │ Recall    │  │ Insight      │  │   │
│  │  │ (bi-enc) │  │ (±2 chunk │  │ (cross-enc   │  │   │
│  │  │          │  │  expand)  │  │  rerank)     │  │   │
│  │  └──────────┘  └───────────┘  └──────────────┘  │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────▼───────────────────────────────┐   │
│  │           Database Layer                          │   │
│  │  ┌────────────────┐  ┌────────────────────────┐  │   │
│  │  │ ChromaVectorDB │  │ EmbeddingManager       │  │   │
│  │  │ • search       │  │ • bge-small-en-v1.5    │  │   │
│  │  │ • get_chunks_  │  │ • local_files_only     │  │   │
│  │  │   by_source    │  │ • model mismatch       │  │   │
│  │  │ • add/delete   │  │   detection            │  │   │
│  │  └────────────────┘  └────────────────────────┘  │   │
│  └──────────────────┬───────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP + Bearer Token
┌─────────────────────▼───────────────────────────────────┐
│              ChromaDB (local or remote)                   │
│  • HNSW cosine similarity index                          │
│  • Collection metadata stores embedding_model            │
└─────────────────────────────────────────────────────────┘
```

## Search Pipeline

### 1. Negation Preprocessing
All queries pass through negation removal before search. Clauses with "without", "not", "except", "excluding" are stripped to prevent embedding model confusion.

`"caching strategies without Redis"` → `"caching strategies"`

### 2. Vector Search (bi-encoder)
ChromaDB HNSW index finds candidate chunks using cosine similarity against bge-small-en-v1.5 embeddings (384 dimensions). Metadata boosting adds score for title and keyword matches.

### 3. Arcane Recall (chunk expansion)
Every search result is expanded with ±2 adjacent chunks from the same document. This provides full section context instead of isolated fragments. Uses per-document lookup (`get_chunks_by_source`) instead of full DB scan.

```
DOCUMENT SOURCE
┌───────────────────────────────────────────────────────────┐
│ [Chunk 0] [Chunk 1] [Chunk 2] [Chunk 3] [Chunk 4] [Chunk 5] ...
└───────────────────────────────────────────────────────────┘
                          │
                   VECTOR SEARCH MATCH
                          ▼
                    ┌───────────┐
                    │  Chunk 3  │ (Matched Fragment)
                    └───────────┘
                          │
                  ARCANE RECALL LOOKUP
             (±2 Neighboring Chunks)
             ┌────────────┴────────────┐
             ▼                         ▼
┌───────────┐┌───────────┐       ┌───────────┐┌───────────┐
│  Chunk 1  ││  Chunk 2  │       │  Chunk 4  ││  Chunk 5  │
└───────────┘└───────────┘       └───────────┘└───────────┘
             │           │       │           │
             └───────────┼───────┼───────────┘
                         ▼       ▼
┌───────────────────────────────────────────────────────────┐
│                      FULL CONTEXT                         │
│  [Chunk 1] + [Chunk 2] + [Chunk 3] + [Chunk 4] + [Chunk 5]│
└───────────────────────────────────────────────────────────┘
```

- Content match: +17% over raw search
- Latency overhead: ~6ms
- Optimal expansion: ±2 chunks (±3 no benefit, ±4 hurts precision)

### 4. Divine Insight (cross-encoder reranking) — precise path only
Cross-encoder (`ms-marco-MiniLM-L-6-v2`) rescores all candidates by examining query-document pairs individually. Higher precision (+2.6%) but trades content match (-7.6%) and adds ~1.5s latency.

### 5. Relevance Threshold
Results below score 0.65 are filtered. Based on score distribution analysis: adversarial queries score ~0.56, lowest legitimate query scores 0.75. Zero false negatives on 23-query benchmark.

## Ingestion Pipeline

### 1. Quality Gate
Documents are validated before ingestion:
- YAML frontmatter required (title, description, keywords)
- At least 2 markdown headers
- Between 100 and 10,000 words
- No unclosed code blocks

Rejected documents get specific error messages. Agent can fix and retry.

### 2. Document Processing
- Text extraction (markdown, PDF via pymupdf4llm/pdfplumber, plain text)
- YAML frontmatter parsing
- Markdown header-aware chunking (splits at `##` boundaries, falls back to 512-char fixed chunks with 50-char overlap)

### 3. Bardic Knowledge (contextual embeddings)
Before embedding, each chunk is prefixed with document metadata:
`"Document: {title}. Description: {description}.\n\n{chunk text}"`

This is an ingestion-time technique — the context is baked into the stored embeddings. It improved precision by +14% with zero latency cost.

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
The embedding model must exist in the local cache before startup. If missing, the server exits immediately with a clear error instead of downloading ~130MB and blocking the MCP client.

## Agent Decomposition Pattern

Complex multi-document queries are the agent's responsibility to decompose. The search tool description instructs the agent:

> "For complex multi-part questions, make multiple simple searches (one per sub-question) and synthesize the results yourself."

Benchmarked: single search achieves 55% content match on multi-doc queries. Agent decomposition achieves 92.5%. The agent fires searches in parallel and synthesizes across results.

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

| Metric | Value |
|--------|-------|
| Simple search latency (local) | ~23ms |
| Simple search latency (remote) | ~350-430ms |
| Precise search latency | ~1,550ms |
| Content match (simple) | 87.3% |
| Content match (decomposed) | 92.5% |
| Precision (simple) | 87.8% |
| Precision (precise) | 90.4% |
| Scale tested | 2,770 chunks, 80 docs |
| Relevance threshold | 0.65 (zero false negatives) |

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
│   ├── arcane_recall.py     # Chunk expansion (±2)
│   ├── reranker.py          # Cross-encoder reranking
│   ├── processor.py         # Document chunking + Bardic Knowledge
│   └── extractor.py         # Entity extraction (spaCy)
└── mcp/
    └── server.py            # MCP tools + conditional registration
```
