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

| Metric | Simple Path | Hybrid Path ([Wild Magic](GLOSSARY.md#lexical-matching-bm25)) | Precise Path |
|--------|------------:|-------------------------:|-------------:|
| **Overall MRR** | 0.5054 | **0.5424** (+7%) | 0.5046 |
| **nDCG@5** | 0.5117 | **0.5511** (+8%) | 0.5058 |
| **Hit Rate@5** | 0.6296 | 0.5741 | 0.6019 |
| **Avg Latency** | **437ms** | 704ms | 1144ms |

*\* Note: Latency includes [Arcane Recall's](GLOSSARY.md#arcane-recall) similarity-weighted pruning (~400ms), which reduces downstream LLM costs by 22%.*

### Domain Performance (MRR / nDCG)

| Category | Simple (Vector) | Hybrid (BM25+Vector) | Note |
|----------|-----------------|----------------------|------|
| **Lexical** (Identifiers) | 0.42 / 0.44 | **0.53 / 0.55 (+26%)** | Fixing "Keyword Blindness" |
| **Semantic** (Concepts) | 0.87 / 0.87 | **0.89 / 0.90 (+2%)** | Stable semantic depth |
| **Adversarial** (Noise) | 1.00 (Block Rate) | 1.00 (Block Rate) | Fully warded |

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

**Implementation:** Initial candidates are filtered by `MIN_RELEVANCE_SCORE` (0.75), then re-scored by a cross-encoder (`ms-marco-MiniLM-L-6-v2`).
**Analysis:** Optimizes for semantic relevance. [**Arcane Attunement**](GLOSSARY.md#arcane-attunement) makes this high-precision road viable for real-time use.

### [The Relevance Ward](GLOSSARY.md#the-relevance-ward) (Thresholding)
**Threshold:** `0.75`
**Analysis:** Filters out out-of-domain "noise". Successfully blocked adversarial technical queries (e.g., "quantum photosynthesis") while preserving all legitimate technical matches (>0.84).

---

## Agentic Workflows: Decomposition
Multi-part queries (e.g., "authentication + caching + microservices") are designed to be decomposed.

1. **The Mock**: The benchmark simulates an agent breaking a hard query into 3-4 specific sub-queries.
2. **The Result**: 100% Recall. The agent successfully gathers all necessary documentation by performing multiple targeted searches.
3. **Recommendation**: Agents should prioritize `simple` path searches in parallel over a single `precise` search for complex tasks.

---

## Legacy Benchmarks (Historical Reference)

### 15-Query Baseline (Retired)
The legacy suite achieved 97% precision on a simpler, 15-query set. This has been replaced by the more rigorous 23-query suite which includes adversarial and multi-part checks.

| Metric | Baseline (15-Q) | Bardic (15-Q) | Divine (15-Q) |
|--------|----------------:|--------------:|--------------:|
| **Precision** | 83.3% | 97.3% | 98.7% |
| **Latency (CPU)** | 18.3ms | 17.4ms | 1499.6ms |
