# RAG Quality Benchmark Results

## Methodology

- **Embedding Model**: bge-small-en-v1.5
- **Test Queries**: **23 queries** (5 easy, 9 medium, 9 hard/adversarial)
- **Test Documents**: 9 documents + 80 scale documents for latency testing
- **Agent Mocking**: Complex queries utilize `sub_queries` to simulate agent decomposition.
- **Metrics**:
  - **Precision**: % of retrieved chunks that belong to relevant documents.
  - **Recall**: % of expected documents found (at least one chunk).
  - **Latency**: Average query response time (ms).

## The Centurion Set (The High Audit)

To ensure the library remains a reliable source of wisdom, we have transitioned to **The Centurion Set** — a statistically significant audit of 108 queries across three domains of arcane inquiry.

### Arcane Metrics Explained

- [**The Success of the Scry (Hit Rate@5)**](GLOSSARY.md#the-success-of-the-scry-hit-ratek): The probability that the answer thou seekest lies within the first five scrolls returned by the library.
- [**The Oracle's Promptness (MRR)**](GLOSSARY.md#the-oracles-promptness-mrr): Measures how close to the top the most relevant scroll appears. If the Oracle speaks the truth immediately (rank 1), the score is perfect (1.0).
- [**The Quality of the Arrangement (nDCG@5)**](GLOSSARY.md#the-quality-of-the-tomes-arrangement-ndcgk): Evaluates not just if the truth was found, but if the most relevant scrolls were placed before the less relevant ones.

### Comparative Audit Results

*Results from a single representative run. See [Reproducibility](#reproducibility) for 5-run variance analysis (MRR and nDCG@5 perfectly stable; Hit Rate@5 ±0.5%).*

| Metric | Simple Path | Hybrid Path ([Wild Magic](GLOSSARY.md#lexical-matching-bm25)) | Precise Path |
|--------|------------:|-------------------------:|-------------:|
| **Overall MRR** | 0.4776 (±0.10) | 0.4722 (±0.09) | 0.4691 (±0.10) |
| **nDCG@5** | 0.4851 (±0.10) | 0.4746 (±0.09) | 0.4746 (±0.10) |
| **Hit Rate@5** | 0.6019 (±0.09) | 0.7130 (±0.08) | 0.5463 (±0.10) |
| **Avg Latency** | **57ms** | 82ms | 175ms |

*95% bootstrap confidence intervals (n=1000, seed=42) shown as ±half-width. Latency measured on CPU with warm model.*

*MRR and nDCG@5 differences between paths fall within the 95% confidence intervals and are not statistically significant (e.g., simple MRR 0.4776 vs hybrid 0.4722, delta 0.0054 within ±0.10). Hit Rate@5 is the primary metric for path selection: the hybrid path's advantage (0.7130 vs 0.6019, delta 0.1111) exceeds the 2σ reproducibility threshold (±1.0%).*

### Domain Performance (MRR / nDCG)

| Category | Simple (Vector) | Hybrid (BM25+Vector) | Precise (Reranked) | Note |
|----------|-----------------|----------------------|--------------------|------|
| **Lexical** (Identifiers) | 0.42 / 0.44 | **0.53 / 0.55 (+26%)** | 0.42 / 0.42 | Fixing "Keyword Blindness" |
| **Semantic** (Concepts) | 0.87 / 0.87 | **0.89 / 0.90 (+2%)** | 0.87 / 0.87 | Stable semantic depth |
| **Adversarial** (Noise) | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | Warded ¹ |

¹ MRR of 0.0 means no adversarial query surfaced a relevant result in the top position. The hybrid path fully filters adversarial queries via the RRF threshold (Hit Rate@5 = 0.0); simple and precise paths may still return low-relevance results that score above the vector threshold (Hit Rate@5 = 0.40 and 0.33 respectively).

---

## Core Techniques

### [Bardic Knowledge](GLOSSARY.md#bardic-knowledge): Contextual Chunk Embeddings
> *"Bards weave context and lore into their knowledge, enriching every tale with the wisdom of what came before."*

**Implementation:** Document title and description are prefixed to every chunk during ingestion.
**Analysis:** Provides high precision for isolated chunks by baking global document context into the local embedding.

### [Arcane Recall](GLOSSARY.md#arcane-recall): Chunk Expansion
> *"The search finds the spark; the expansion brings the flame."*

**Implementation:** Automatically retrieves ±2 adjacent chunks for every search result using [**Arcane Coalescence**](GLOSSARY.md#arcane-coalescence) and [**Scholar's Discernment**](GLOSSARY.md#the-scholars-discernment).
**Analysis:** Increases content match rate by 17% while reducing context size by 22%.

### [Divine Insight](GLOSSARY.md#cross-encoder-reranking): Precise Reranking
> *"Through divine magic, clerics perceive the true nature of all things."*

**Implementation:** Initial candidates are filtered by the [configured relevance threshold](ARCHITECTURE.md#tuned-parameters-reference), then re-scored by a cross-encoder (`ms-marco-MiniLM-L-6-v2`).
**Analysis:** Optimizes for semantic relevance. [**Arcane Attunement**](GLOSSARY.md#arcane-attunement) makes this high-precision road viable for real-time use.

### [The Relevance Ward](GLOSSARY.md#the-relevance-ward) (Thresholding)
**Implementation:** A score-based filter applied to all retrieval results (see [Tuned Parameters](ARCHITECTURE.md#tuned-parameters-reference)).
**Analysis:** Filters out out-of-domain "noise". No adversarial query surfaced a relevant result in the top position (MRR=0.0 across all paths). The hybrid path fully filters adversarial queries; simple and precise paths may still return low-relevance results that score above the vector threshold.

Threshold values and calibration procedure: [ARCHITECTURE.md](ARCHITECTURE.md#tuned-parameters-reference).

---

## Agentic Workflows: Decomposition
Multi-part queries (e.g., "authentication + caching + microservices") are designed to be decomposed.

1. **The Mock**: The benchmark simulates an agent breaking a hard query into specific sub-queries.
2. **The Result**: High Recall. The agent successfully gathers all necessary documentation by performing multiple targeted searches.
3. **Recommendation**: Agents should prioritize `simple` path searches in parallel over a single `precise` search for complex tasks.

*Note: Sub-queries are pre-defined splits simulating ideal agent decomposition, not generated by a real agent. Entry 25 (Production Validation) provides qualitative confirmation that real agents decompose queries as expected, but no quantitative metrics from real agent runs exist.*

---

## Legacy Benchmarks (Historical Reference)

### 15-Query Baseline (Retired)
The legacy suite achieved 97% precision on a simpler, 15-query set. This has been replaced by the more rigorous 23-query suite which includes adversarial and multi-part checks.

| Metric | Baseline (15-Q) | Bardic (15-Q) | Divine (15-Q) |
|--------|----------------:|--------------:|--------------:|
| **Precision** | 83.3% | 97.3% | 98.7% |
| **Latency (CPU)** | 18.3ms | 17.4ms | 1499.6ms |

*Note on legacy "Recall" metric: The 15-query suite used a non-standard Recall definition — (total chunks retrieved from relevant documents / number of expected documents) × 100%. This produces values exceeding 100% (e.g., R=470%) when multiple chunks per document are retrieved. This metric has been retired in favor of [Hit Rate@5](GLOSSARY.md#the-success-of-the-scry-hit-ratek) in the Centurion Set.*

---

## Reproducibility

ChromaDB's HNSW index construction is non-deterministic — the same corpus ingested into a fresh collection can produce slightly different nearest-neighbor graphs. To quantify this variance, the Centurion Set was run 5 times with fresh re-ingestions of the full corpus (89 docs, ~2,770 chunks).

| Metric | Mean | Std Dev | Notes |
|--------|-----:|--------:|-------|
| **MRR** | 0.4776 | 0.0000 | Perfectly stable across runs |
| **nDCG@5** | 0.4851 | 0.0000 | Perfectly stable across runs |
| **Hit Rate@5** | 0.6074 | 0.0051 | 2 of 5 runs at 0.6019, 3 at 0.6111 |
| **Avg Latency** | 64.8ms | 1.7ms | Consistent |

At the current corpus scale, HNSW non-determinism has negligible impact on ranking metrics. Only Hit Rate@5 shows minor variance (±0.5%), affecting at most 1 query out of 108 per run. MRR and nDCG@5 are perfectly reproducible.

Benchmark comparisons should exceed 2σ (±1.0% for Hit Rate@5) to be considered significant. For MRR and nDCG@5, any observed difference is meaningful at this corpus scale.

*Measured with `scripts/reproducibility_test.py --runs 5`. Raw data in `tests/results/reproducibility_simple.json`.*

---

## Cold-Start Latency

Cold-start latency measures the time from the initial process spawn until the first search result is returned. This includes Python interpreter startup, module imports (including heavy libraries like PyTorch and SentenceTransformers), database connection, and model loading.

| Metric | Measured Value |
|--------|----------------|
| **Avg Cold-Start (Total)** | **5,825 ms** (±41ms) |
| **Avg Cold-Start (Internal)** | **4,534 ms** (±25ms) |

**Methodology:**
- **Iterations:** 7
- **Process:** Parent process spawns a fresh Python process for each iteration.
- **Query:** Simple search path against a seeded collection (89 docs).
- **Environment:** CPU-only mode (`CANDLEKEEP_DEVICE=cpu`) to ensure consistency.
- **Hardware:** AMD Ryzen 7 7800X3D (8-Core), 32GB RAM, Linux (Arch 6.18).
- **Python:** 3.11.14

*Note: The ~1.3s delta between "Total" and "Internal" represents the overhead of the Python interpreter startup and initial module discovery before the application's timing loop begins.*
