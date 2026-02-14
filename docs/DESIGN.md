# Candlekeep Design Document

## 1. Problem Statement

AI agents need access to domain-specific knowledge that isn't in their training data. Existing solutions either require full document context (expensive, hits token limits) or use naive keyword search (misses semantic meaning). Candlekeep provides a RAG knowledge base that an AI agent can query via MCP, getting relevant document fragments with full section context in 22–36ms (typically ~26ms on a warm model).

## 2. Design Goals

1. **Fast default path** — Sub-50ms search latency for interactive agent use
2. **High content match** — Return text that actually contains the answer, not just related text
3. **Agent-native** — The agent controls search strategy, decomposes complex queries, synthesizes results
4. **Quality enforcement** — Reject poorly structured documents at ingestion time
5. **Safe remote access** — Embedding model mismatch detection, conditional write tools, token auth

## 3. Design Decisions

### 3.1 Two Search Paths, Not Six

Early designs proposed 6 query types (simple, broad, complex, abstract, context, keyword). Benchmarking showed:
- `context` was identical to `simple` (±3 expansion gave only +1.3% content over ±2)
- `complex` was better handled by the agent making multiple searches (55% → 92.5% content)
- `broad`, `abstract`, `keyword` didn't justify separate paths

**Decision:** Two paths — `simple` (22–36ms, typically ~26ms) and `precise` (~1.5s). The agent picks.

```
The Two Roads Through Candlekeep
═════════════════════════════════

Query arrives
     │
     ▼
┌─────────────────────────────────────────────────┐
│  Agent chooses path based on query complexity   │
└─────────────────────────────────────────────────┘
     │
     ├──────────────────────┬──────────────────────┐
     │                      │                      │
     ▼                      ▼                      ▼
┌─────────┐          ┌─────────┐          ┌─────────┐
│ SIMPLE  │          │ PRECISE │          │ AGENT   │
│  PATH   │          │  PATH   │          │ DECOMP  │
└─────────┘          └─────────┘          └─────────┘
     │                      │                      │
     │                      │                      │
  ~26ms                  ~1.5s              Multiple
     │                      │               simple
     │                      │               searches
     ▼                      ▼                      │
┌─────────┐          ┌─────────┐                  │
│ Vector  │          │ Vector  │                  │
│ Search  │          │ Search  │                  │
└─────────┘          └─────────┘                  │
     │                      │                      │
     ▼                      ▼                      │
┌─────────┐          ┌─────────┐                  │
│ Arcane  │          │ Arcane  │                  │
│ Recall  │          │ Recall  │                  │
│  (±2)   │          │  (±2)   │                  │
└─────────┘          └─────────┘                  │
     │                      │                      │
     │                      ▼                      │
     │               ┌─────────┐                  │
     │               │ Divine  │                  │
     │               │ Insight │                  │
     │               │ Rerank  │                  │
     │               └─────────┘                  │
     │                      │                      │
     ▼                      ▼                      ▼
┌──────────────────────────────────────────────────┐
│         Relevance Ward (threshold 0.65)          │
└──────────────────────────────────────────────────┘
     │
     ▼
  Results to agent

Use cases:
- Simple: "What's the API endpoint for search?"
- Precise: "Compare authentication methods and recommend one"
- Agent decomp: "How do I set up, configure, and deploy?"
```

### 3.2 Agent Decomposes, Tool Searches

LLM-based query decomposition (Flurry of Blows) was implemented and tested inside the search tool. It added 1.1s latency and required LLM API credentials. Meanwhile, the calling agent — already a frontier LLM — can decompose queries better and for free.

**Decision:** Remove query decomposition from the tool. Tell the agent to make multiple searches. Benchmarked: agent decomposition achieves 92.5% content match vs 55% for single search.

### 3.3 Arcane Recall as Universal Default

Chunk expansion (returning ±2 adjacent chunks around each match) improved content match by +17% with only +6ms latency and zero precision loss. No reason not to apply it to every search.

**Decision:** Every search path uses Arcane Recall. Optimized with per-document chunk lookup instead of full DB scan (49% latency reduction).

```
Without Arcane Recall (fragmented):
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


With Arcane Recall (±2 expansion):
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

### 3.4 Bardic Knowledge at Ingestion Time

Prepending document title and description to each chunk before embedding improved precision by +14%. This is an ingestion-time technique — the context is baked into the stored vectors. It cannot be toggled at query time.

**Decision:** Always active. Documents without frontmatter get no benefit, which is why the quality gate requires frontmatter.

### 3.5 Quality Gate on Ingestion

The `ingest` tool validates documents before accepting them. This ensures Bardic Knowledge has metadata to work with and that chunks have semantic structure (markdown headers) for proper splitting.

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
| Bardic Knowledge (contextual embeddings) | +14% precision | ✅ Default |
| Arcane Recall (±2 chunk expansion) | +17% content, +6ms | ✅ Default |
| Divine Insight (cross-encoder reranking) | +2.6% precision, +1.5s | ✅ Precise path |
| Flurry of Blows (LLM query decomposition) | 100% precision, +1.1s | ❌ Agent does this better |
| Mirror Image (LLM query expansion) | Degraded all metrics | ❌ Rejected |
| Illusory Script (HyDE) | 3.9s latency | ❌ Too slow |
| Wild Magic Surge (BM25 hybrid) | Degraded precision | ❌ Rejected |
| Scrying Window (sentence splitting) | 50% precision collapse | ❌ Rejected |

## 5. Parameters Validated

| Parameter | Tested Values | Optimal | Rationale |
|-----------|--------------|---------|-----------|
| Chunk size | 256, 512, 768, 1024 | 512 | Best content match; Arcane Recall compensates for size |
| Chunk overlap | 50 | 50 | Standard, not benchmarked in isolation |
| Expansion size | ±1, ±2, ±3, ±4 | ±2 | ±3 no benefit, ±4 hurts precision by 8% |
| Embedding model | minilm, bge-small, nomic | bge-small | Best content (87.3%), good speed (22–36ms) |
| Relevance threshold | 0.5–0.75 range | 0.65 | Clean gap between adversarial (0.56) and legitimate (0.75) |

## 6. Scalability

### 6.1 Sub-linear Scaling

The simple search path maintains consistent performance as the knowledge base grows. Testing with a 15.5x increase in data (178 → 2770 chunks) showed only a 13% latency increase (23ms → 26ms).

All latency numbers measured on a warm model (after initial inference) using `bge-small` (`BAAI/bge-small-en-v1.5`), the recommended embedding model. Cold-start adds ~10ms to the first few queries as the embedding model warms its inference path. Latency varies by query length: short keyword queries (e.g., "vector database") hit ~22ms, while full sentences reach ~36ms due to tokenization overhead.

**Why it scales:**
- Per-document chunk lookup for Arcane Recall expansion (doesn't scan full DB)
- Vector search complexity grows logarithmically with HNSW index
- No full-text search or sequential scans in the critical path

**Implication:** Users can grow their documentation from dozens to thousands of documents without degrading search performance.

### 6.2 The Relevance Ward

A minimum relevance threshold of **0.65** filters low-confidence results. This prevents the agent from receiving irrelevant matches that could lead to hallucinated answers.

**Threshold validation:**
- Legitimate queries score 0.75–1.22
- Adversarial queries (e.g., "quantum entanglement in photosynthesis" against software docs) score ~0.56
- Clean separation with zero false negatives in benchmark testing

**Behavior:** Queries below threshold return empty results. The library says "I don't know" instead of guessing.

## 7. Threat Model

| Threat | Mitigation |
|--------|-----------|
| Unauthorized DB access | Bearer token auth, IP-restricted security group |
| Wrong embedding model on remote | Auto-detection + override from collection metadata |
| Garbage query results | Relevance threshold (0.65) filters irrelevant results |
| Bad document quality | Quality gate rejects docs without frontmatter/structure |
| Model download at startup | Exit immediately if model not cached locally |
| Write to remote DB accidentally | Write tools hidden unless explicitly opted in |

## 8. Limitations

- **Single embedding model per collection** — Switching models requires full re-ingestion
- **Cross-encoder latency** — Precise path is CPU-bound, capped by host hardware. Benchmarked at ~1.5s on the original test machine, ~3s on Apple Silicon (M-series) running CPU inference. See section 9.1 for acceleration options
- **No incremental ingestion** — Re-ingesting a file replaces all its chunks (by design, prevents duplicates)
- **Agent-dependent decomposition** — Multi-doc query quality depends on the agent splitting queries correctly

## 9. Future Work

- HTTPS with ACM certificate when a domain is available
- Caching reranked results for repeated queries
- Streaming search results for lower perceived latency

### 9.1 Hardware-Accelerated Inference

The precise path latency (~1.5s–3s) is capped by the host environment, not by the tool. The simple path runs at 22–36ms on any hardware because vector lookup dominates. The cross-encoder, however, runs CPU-only inference through PyTorch, and its latency scales directly with available compute. Users on machines without GPU acceleration will see higher precise path latency.

**Current architecture (CPU-only):**
- `src/candlekeep/database/embeddings.py` — `SentenceTransformer` loads PyTorch models, infers on CPU
- `src/candlekeep/rag/reranker.py` — `CrossEncoder` instantiates a new model per call, no caching, CPU-only
- `pyproject.toml` — `sentence-transformers` pulls in `torch` (CPU wheel)

**Required changes:**

1. **`config.py`** — Add `CANDLEKEEP_DEVICE` setting (`auto`, `cpu`, `mps`, `cuda`). `auto` detects available hardware at startup.

2. **`embeddings.py`** — Pass `device` parameter to `SentenceTransformer()` constructor. The library already supports `device="mps"` (Apple Silicon), `device="cuda"` (Nvidia and AMD via ROCm — PyTorch exposes both as the `cuda` device), and `device="cpu"`.

3. **`reranker.py`** — Two changes:
   - Cache the `CrossEncoder` instance (currently re-instantiated every call — this alone would improve latency)
   - Pass `device` parameter to `CrossEncoder()` constructor

4. **`pyproject.toml`** — Add optional dependency groups:
   - `mlx`: `mlx`, `mlx-lm` (Apple Silicon native, bypasses PyTorch entirely)
   - `cuda`: `torch` with CUDA/ROCm index URL (same `device="cuda"` for both Nvidia and AMD)
   - No change needed for MPS — PyTorch already supports it via `device="mps"`

5. **`scripts/setup.sh`** — Detect hardware and suggest the right install command

**MLX path (Apple Silicon):**
MLX requires replacing `SentenceTransformer` with MLX-native model loading. The `mlx-community` HuggingFace org hosts converted models. This is the most invasive change — it needs an abstraction layer over the embedding interface so both PyTorch and MLX backends can be swapped.

**Estimated impact:**
- MPS (PyTorch on Apple GPU): ~2x speedup on cross-encoder, minimal code change
- CUDA (Nvidia/AMD): ~5–10x speedup on cross-encoder, minimal code change
- MLX: ~3–4x speedup, requires embedding abstraction layer

**Lowest-effort win:** Cache the `CrossEncoder` in `reranker.py` and pass `device` from settings. Two files changed, ~10 lines.
