# Candlekeep Design Document

## 1. Problem Statement

AI agents need access to domain-specific knowledge that isn't in their training data. Existing solutions either require full document context (expensive, hits token limits) or use naive keyword search (misses semantic meaning). Candlekeep provides a RAG knowledge base that an AI agent can query via MCP, getting relevant document fragments with full section context in ~23ms.

## 2. Design Goals

1. **Fast default path** — Sub-50ms search latency for interactive agent use
2. **High content match** — Return text that actually contains the answer, not just related text
3. **Agent-native** — The agent controls search strategy, decomposes complex queries, synthesizes results
4. **Quality enforcement** — Reject poorly structured documents at ingestion time
5. **Safe remote access** — Embedding model mismatch detection, conditional write tools, token auth

## 3. Design Decisions

### 3.1 Two Search Paths, Not Six

Early designs proposed 6 query types (simple, broad, complex, abstract, context, keyword). Through benchmarking, we found:
- `context` was identical to `simple` (±3 expansion gave only +1.3% content over ±2)
- `complex` was better handled by the agent making multiple searches (55% → 92.5% content)
- `broad`, `abstract`, `keyword` didn't justify separate paths

**Decision:** Two paths — `simple` (23ms) and `precise` (1.5s). The agent picks.

### 3.2 Agent Decomposes, Tool Searches

We implemented and tested LLM-based query decomposition (Flurry of Blows) inside the search tool. It added 1.1s latency and required LLM API credentials. Meanwhile, the calling agent — already a frontier LLM — can decompose queries better and for free.

**Decision:** Remove query decomposition from the tool. Tell the agent to make multiple searches. Benchmarked: agent decomposition achieves 92.5% content match vs 55% for single search.

### 3.3 Arcane Recall as Universal Default

Chunk expansion (returning ±2 adjacent chunks around each match) improved content match by +17% with only +6ms latency and zero precision loss. No reason not to apply it to every search.

**Decision:** Every search path uses Arcane Recall. Optimized with per-document chunk lookup instead of full DB scan (49% latency reduction).

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
| Embedding model | minilm, bge-small, nomic | bge-small | Best content (87.3%), good speed (23ms) |
| Relevance threshold | 0.5–0.75 range | 0.65 | Clean gap between adversarial (0.56) and legitimate (0.75) |

## 6. Threat Model

| Threat | Mitigation |
|--------|-----------|
| Unauthorized DB access | Bearer token auth, IP-restricted security group |
| Wrong embedding model on remote | Auto-detection + override from collection metadata |
| Garbage query results | Relevance threshold (0.65) filters irrelevant results |
| Bad document quality | Quality gate rejects docs without frontmatter/structure |
| Model download at startup | Exit immediately if model not cached locally |
| Write to remote DB accidentally | Write tools hidden unless explicitly opted in |

## 7. Limitations

- **Single embedding model per collection** — Switching models requires full re-ingestion
- **Cross-encoder latency** — Precise path is 65x slower than simple; only for high-value queries
- **No incremental ingestion** — Re-ingesting a file replaces all its chunks (by design, prevents duplicates)
- **Agent-dependent decomposition** — Multi-doc query quality depends on the agent splitting queries correctly

## 8. Future Work

- HTTPS with ACM certificate when a domain is available
- Faster cross-encoder or distilled reranking model
- Caching reranked results for repeated queries
- Streaming search results for lower perceived latency
