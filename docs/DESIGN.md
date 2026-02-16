# Candlekeep Design Document

## 1. Problem Statement

AI agents need access to domain-specific knowledge that isn't in their training data. Existing solutions either require full document context (expensive, hits token limits) or use naive keyword search (misses semantic meaning). Candlekeep provides a RAG knowledge base that an AI agent can query via MCP, getting relevant document fragments with full section context in sub-100ms (typically ~57ms on a warm model with similarity-weighted expansion).

## 2. Design Goals

1. **Fast default path** — Sub-100ms search latency for interactive agent use (typically ~57ms with similarity-weighted expansion)
2. **High content match** — Return text that actually contains the answer, not just related text
3. **Agent-native** — The agent controls search strategy, decomposes complex queries, synthesizes results
4. **Quality enforcement** — Reject poorly structured documents at ingestion time
5. **Safe remote access** — Embedding model mismatch detection, conditional write tools, token auth

## 3. Design Decisions

### 3.1 Three [Search Paths](ARCHITECTURE.md#the-three-roads), Not Two

Early designs proposed 2 query types (simple and precise). Benchmarking on the Centurion Set showed that "Keyword Blindness" was a significant issue for exact technical identifiers.

**Decision:** Three paths — `simple`, `hybrid`, and `precise`. The agent picks.

```
═══════════════════════════════════
The Three Roads Through Candlekeep
═══════════════════════════════════

Query arrives
     │
     ▼
┌─────────────────────────────────────────────────┐
│  Agent chooses path based on query complexity   │
└─────────────────────────────────────────────────┘
     │
     ├──────────────────────┼──────────────────────┬──────────────────────┐
     │                      │                      │                      │
     ▼                      ▼                      ▼                      ▼
┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
│ SIMPLE  │          │ HYBRID  │          │ PRECISE │          │ AGENT   │
│  PATH   │          │ (WILD)  │          │  PATH   │          │ DECOMP  │
└─────────┘          └─────────┘          └─────────┘          └─────────┘
     │                      │                      │                      │
     │                      │                      │                      │
  (Fast)                 (Lexical)              (Precise)          Multiple
     │                      │                      │                simple
     │               ┌──────┴──────┐               │               searches
     ▼               ▼             ▼               ▼                      │
┌─────────┐     ┌─────────┐   ┌─────────┐     ┌─────────┐                  │
│ Vector  │     │ Vector  │   │  BM25   │     │ Vector  │                  │
│ Search  │     │ Search  │   │ Lexical │     │ Search  │                  │
└─────────┘     └─────────┘   └─────────┘     └─────────┘                  │
     │               │             │               │                      │
     │               └──────┬──────┘               │                      │
     │                      ▼                      │                      │
     │               ┌─────────┐                  │                      │
     │               │  Rank   │                  │                      │
     │               │ Fusion  │                  │                      │
     │               └─────────┘                  │                      │
     │                      │                      │                      │
     ▼                      ▼                      ▼                      │
┌─────────┐          ┌─────────┐          ┌─────────┐                  │
│ Arcane  │          │ Arcane  │          │ Arcane  │                  │
│ Recall  │          │ Recall  │          │ Recall  │                  │
│         │          │         │          │         │                  │
└─────────┘          └─────────┘          └─────────┘                  │
     │                      │                      │                      │
     │                      │                      ▼                      │
     │                      │               ┌─────────┐                  │
     │                      │               │ Divine  │                  │
     │                      │               │ Insight │                  │
     │                      │               │ Rerank  │                  │
     │                      │               └─────────┘                  │
     │                      │                      │                      │
     ▼                      ▼                      ▼                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│      The Relevance Ward (simple/hybrid only)                             │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
  Results to agent
```

See [The Relevance Ward](GLOSSARY.md#the-relevance-ward) ([configured threshold](ARCHITECTURE.md#tuned-parameters-reference)).

Use cases:
- Simple: "What's the API endpoint for search?"
- Hybrid: "How do I fix error 0xEF or version mismatch?"
- Precise: "Compare authentication methods and recommend one"
- Agent decomp: "How do I set up, configure, and deploy?"

### 3.2 Agent Decomposes, Tool Searches

LLM-based query decomposition (Flurry of Blows) was implemented and tested inside the search tool. It added significant latency and required LLM API credentials. Meanwhile, the calling agent — already a frontier LLM — can decompose queries better and for free.

**Decision:** Remove query decomposition from the tool. Tell the agent to make multiple searches. Benchmarked: agent decomposition achieves significantly higher content match vs single search.

### 3.3 [Arcane Recall](GLOSSARY.md#arcane-recall) as Universal Default

Chunk expansion (returning adjacent chunks around each match) improved content match by +17% (15-query legacy suite; see Research Diary Entry 2) with minimal latency and zero precision loss. No reason not to apply it to every search.

**Decision:** Every search path uses Arcane Recall. Optimized with per-document chunk lookup instead of full DB scan.

```
Without [Arcane Recall](GLOSSARY.md#arcane-recall) (fragmented):
┌─────────────────────────────────────────┐
│ Document: "Authentication Guide"       │
├─────────────────────────────────────────┤
│ Chunk 0: Introduction...                │
│ Chunk 1: Prerequisites...               │
│ Chunk 2: Token generation requires...   │ ← Match (returned alone)
│ Chunk 3: Store tokens in environment... │
│ Chunk 4: Example usage...               │
└─────────────────────────────────────────┘
         ↓
   Agent receives incomplete context


With [Arcane Recall](GLOSSARY.md#arcane-recall):
┌─────────────────────────────────────────┐
│ Document: "Authentication Guide"       │
├─────────────────────────────────────────┤
│ Chunk 0: Introduction...                │ ← Included (context)
│ Chunk 1: Prerequisites...               │ ← Included (context)
│ Chunk 2: Token generation requires...   │ ← Match (original result)
│ Chunk 3: Store tokens in environment... │ ← Included (context)
│ Chunk 4: Example usage...               │ ← Included (context)
└─────────────────────────────────────────┘
         ↓
   Agent receives full section with setup + usage
```

### 3.4 [Bardic Knowledge](GLOSSARY.md#bardic-knowledge) at Ingestion Time

Prepending document title and description to each chunk before embedding improved precision significantly. This is an ingestion-time technique — the context is baked into the stored vectors. It cannot be toggled at query time.

**Decision:** Always active. Documents without frontmatter get no benefit, which is why the quality gate requires frontmatter.

### 3.5 Quality Gate on Ingestion

The `ingest` tool validates documents before accepting them. This ensures [Bardic Knowledge](GLOSSARY.md#bardic-knowledge) has metadata to work with and that chunks have semantic structure (markdown headers) for proper splitting.

**Decision:** Reject documents missing frontmatter, headers, or with extreme lengths. The agent gets specific error messages and can fix the document.

### 3.6 Conditional Tool Registration

Write tools (ingest, delete, repopulate) are destructive. On remote databases, they're hidden from the agent entirely — not just permission-denied at runtime, but invisible in the tool list.

**Decision:** Local DB = all 8 tools. Remote DB = 5 read-only tools. Override with `CANDLEKEEP_REMOTE_WRITE=true` for explicit opt-in.

### 3.7 Embedding Model Mismatch Protection

If a remote ChromaDB was populated with model A and the local config says model B, searches return silently wrong results. No error, just bad quality.

**Decision:** Store model name in collection metadata. On connect, detect mismatch, override local config, log warning. Also: refuse to download models at startup (exit immediately if not cached locally).

## 4. Techniques Evaluated

| Technique | Result | Status |
|-----------|--------|--------|
| [Bardic Knowledge](GLOSSARY.md#bardic-knowledge) (contextual embeddings) | Improved precision | ✅ Default |
| [Bardic Inspiration](GLOSSARY.md#bardic-inspiration) (metadata boosting) | Larger confidence gap | ✅ Default |
| [Arcane Recall](GLOSSARY.md#arcane-recall) ([Scholar's Discernment](GLOSSARY.md#the-scholars-discernment)) | Improved content, fewer tokens | ✅ Default |
| [Divine Insight](GLOSSARY.md#cross-encoder-reranking) (cross-encoder reranking) | Higher precision | ✅ Precise path |
| Flurry of Blows (LLM query decomposition) | High precision, high latency | ❌ Agent does this better |
| Mirror Image (LLM query expansion) | Degraded all metrics | ❌ Rejected |
| Illusory Script (HyDE) | Unacceptable latency | ❌ Too slow |
| [Wild Magic](GLOSSARY.md#lexical-matching-bm25) (BM25 hybrid) | Higher lexical quality | ✅ Hybrid path |
| Scrying Window (sentence splitting) | Precision collapse | ❌ Rejected |

*Note: The "Result" column references metrics from the retired 15-query legacy suite (Research Diary Entries 1–8). The current evaluation standard is the [Centurion Set](BENCHMARK_RESULTS.md) (108 queries) which uses MRR, nDCG@5, and Hit Rate@5.*

### 4.1 Techniques Not Evaluated

The following retrieval techniques were out of scope for the initial research phase. Both are infrastructure-level changes to Candlekeep's retrieval pipeline.

- **ColBERT / late-interaction models** — Occupies the middle ground between bi-encoder speed and cross-encoder precision. Could reduce precise-path latency while retaining most reranking quality. Not evaluated because ChromaDB does not natively support ColBERT's token-level index, and the current bi-encoder + cross-encoder split already covers the fast/precise tradeoff. Revisit if precise-path latency becomes a deployment blocker.

- **SPLADE / learned sparse retrieval** — Replaces naive BM25 tokenization with learned term weights, improving vocabulary coverage for technical identifiers. Not evaluated because the hybrid path's BM25 + RRF fusion already resolved "Keyword Blindness" (+26% MRR on lexical queries in the Centurion Set), and SPLADE requires a separate model and index. The strongest candidate for improving the hybrid path if the naive tokenizer becomes a limitation at scale.

- **LLM-generated chunk summaries (Contextual Retrieval)** — Generates a per-chunk context summary via LLM at ingestion time, prepended to each chunk before embedding. Similar to Bardic Knowledge but with richer, LLM-generated context instead of document-level metadata. Not evaluated because the ingestion cost is significant (one LLM call per chunk; ~2,770 calls at current corpus scale) and Bardic Knowledge already provides document-level context enrichment at zero cost. Revisit if content match on the Centurion Set plateaus and ingestion latency is not a constraint.

*Note: Embedding model fine-tuning is a user-side optimization for specific corpora, not an infrastructure change to Candlekeep. Users deploying against specialized domains should consider fine-tuning bge-small on their own query-document pairs. See [SETUP.md](SETUP.md) for embedding model configuration.*

## 5. [Tuned Parameters](ARCHITECTURE.md#tuned-parameters-reference) Validated

| Parameter | Tested Values | Optimal | Rationale |
|-----------|--------------|---------|-----------|
| Chunk size | 256, 512, 768, 1024 | 512 | Best content match on 23-query suite (Entry 21); [Arcane Recall](GLOSSARY.md#arcane-recall) compensates for size |
| Chunk overlap | 0, 25, 50, 100 | 50 | Benchmarked on Centurion Set (Entry 29). Overlap=25 marginally better (+1.3% MRR) but within noise. 50 retained as standard. |
| Expansion size | ±1, ±2, ±3, ±4 | ±2 | Re-validated on Centurion Set (108 queries, Entry 28). ±3 no benefit, ±4 hurts precision. |
| Embedding model | minilm, bge-small, nomic | bge-small | Best content match on 23-query suite (Entry 22), good speed |
| [The Relevance Ward](GLOSSARY.md#the-relevance-ward) | Configured range | Technical Reference | Clean statistical separation between adversarial and legitimate (Entry 16, validated on Centurion Set) |

## 6. Scalability

### 6.1 Sub-linear Scaling

The simple search path maintains consistent performance as the knowledge base grows. Testing with a significant increase in data showed only minimal latency increase.

All latency numbers measured on a warm model (after initial inference) using `bge-small` (`BAAI/bge-small-en-v1.5`), the recommended embedding model. Cold-start adds overhead to the first few queries as the embedding model warms its inference path. Latency varies by query length: short keyword queries hit lower latencies, while full sentences reach slightly higher due to tokenization overhead.

**Why it scales:**
- Per-document chunk lookup for [Arcane Recall](GLOSSARY.md#arcane-recall) expansion (doesn't scan full DB)
- Vector search complexity grows logarithmically with HNSW index
- No full-text search or sequential scans in the critical path

**Implication:** Users can grow their documentation from dozens to thousands of documents without degrading search performance.

### 6.2 [The Relevance Ward](GLOSSARY.md#the-relevance-ward)

The Relevance Ward filters low-confidence results based on a [configured threshold](ARCHITECTURE.md#tuned-parameters-reference). This prevents the agent from receiving irrelevant matches that could lead to hallucinated answers.

**Threshold validation:**
- Legitimate queries score consistently higher than adversarial ones
- Clear separation with zero false negatives in benchmark testing

**Behavior:** Queries below the threshold return empty results. The library says "I don't know" instead of guessing.

The Ward prevents false negatives (legitimate queries returning empty). It does not guarantee zero results for adversarial queries on the vector-only paths. The hybrid path's BM25 component provides stronger adversarial filtering — see [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md) for per-path adversarial Hit Rate.

See [Tuned Parameters](ARCHITECTURE.md#tuned-parameters-reference) for threshold values and [Threshold Calibration](ARCHITECTURE.md#threshold-calibration) for the recalibration procedure when deploying against a new corpus.

## 7. Threat Model

| Threat | Mitigation |
|--------|-----------|
| Unauthorized DB access | Bearer token auth, IP-restricted security group |
| Wrong embedding model on remote | Auto-detection + override from collection metadata |
| Garbage query results | [The Relevance Ward](GLOSSARY.md#the-relevance-ward) filters irrelevant results |
| Bad document quality | [Quality Gate](ARCHITECTURE.md#1-quality-gate) rejects docs without frontmatter/structure |
| Model download at startup | Exit immediately if model not cached locally |
| Write to remote DB accidentally | Write tools hidden unless explicitly opted in |
| Unauthorized MCP client | stdio: not applicable (one agent per process). HTTP: optional bearer token auth via `CANDLEKEEP_MCP_TOKEN`. TLS via reverse proxy is the operator's responsibility for non-localhost deployments. |
| Prompt injection via ingested documents | Not mitigated — trusted corpus assumption. The quality gate validates document structure but does not scan for adversarial prompt content. Revisit if Candlekeep ingests untrusted user-submitted documents. |
| Ingestion rate limiting | stdio: not applicable (single agent). HTTP: write operations serialized via `_write_lock`. |
| Per-document access control | Not applicable — all agents see the full corpus. Revisit if multi-tenant access is required. |

## 8. Limitations

- **Single embedding model per collection** — Switching models requires full re-ingestion
- **Cross-encoder latency** — Precise path is CPU-bound, capped by host hardware.
- **No incremental ingestion** — Re-ingesting a file replaces all its chunks (by design, prevents duplicates)
- **Agent-dependent decomposition** — Multi-doc query quality depends on the agent splitting queries correctly

## 9. Future Work

- Caching reranked results for repeated queries
- Streaming search results for lower perceived latency
- **Per-agent auth** — Map different tokens to agent IDs for fine-grained access control in HTTP mode.

### 9.1 Hardware-Accelerated Inference

The precise path latency is capped by the host environment, not by the tool. The simple path runs fast on any hardware because vector lookup dominates. The [cross-encoder](GLOSSARY.md#cross-encoder-reranking), however, runs inference through PyTorch, and its latency scales directly with available compute.

**Current architecture:**
- `src/candlekeep/database/embeddings.py` — `SentenceTransformer` loads models on the best available device (`cuda`, `mps`, or `cpu`).
- `src/candlekeep/rag/reranker.py` — `CrossEncoder` uses a **Singleton Pattern** (cached instance) and batch inference to minimize overhead.
- `src/candlekeep/mcp/server.py` — Performs [**Arcane Attunement**](GLOSSARY.md#arcane-attunement) (startup model loading) so the first query does not suffer from cold-start latency.
