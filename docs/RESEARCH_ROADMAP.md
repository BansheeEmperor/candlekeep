# Candlekeep Engineering: Remediation & Research Roadmap

**Version:** 1.1 (Internal Audit Refinement)  
**Subject:** Transitioning from Heuristic-Based RAG to Statistical Retrieval Engineering  
**Lead Engineer:** Senior Retrieval Auditor

---

## I. Workstream: Statistical Ground Truth (Evaluation Infrastructure)
**Problem:** The current 23-query benchmark is statistically insignificant. Decisions are being made based on noise rather than trend.

### Tasks & Source Code Changes
1.  **Metric Implementation (`src/candlekeep/eval/metrics.py`):**
    *   Implement **nDCG@5** (Normalized Discounted Cumulative Gain) to measure ranking quality.
    *   Implement **MRR** (Mean Reciprocal Rank) to measure how quickly the first relevant result appears.
    *   Implement **Hit Rate@K** to track retrieval success across the corpus.
2.  **Dataset Expansion (`tests/fixtures/eval_suite_100.json`):**
    *   Construct a **Centurion Set** (100+ queries).
    *   **Segment 1: Lexical Hard (30%)** – Queries containing specific version numbers, hex codes, or unique function names (e.g., `v3.4.1`, `0xEF`, `handle_auth_callback`).
    *   **Segment 2: Semantic Soft (40%)** – High-level conceptual questions.
    *   **Segment 3: Adversarial (30%)** – Out-of-domain technical gibberish to test The Relevance Ward.

### Benchmarking Strategy
*   **Run Baseline vs. Expansion:** Compare performance on the baseline set vs. the expanded set to identify "Overfitting" on small samples.
*   **Threshold Sensitivity Curve:** Plot `Precision` and `Recall` for different [Relevance Ward values](ARCHITECTURE.md#tuned-parameters-reference) to find the actual statistical "elbow" for filtering.

---

## II. Workstream: Lexical Hybridization (The "Keyword Blindness" Fix)
**Problem:** Vector embeddings often fail on exact technical identifiers (UUIDs, error codes, niche library names).

### Tasks & Source Code Changes
1.  **Hybrid Pipeline (`src/candlekeep/rag/hybrid.py`):**
    *   Integrate **BM25** (using `rank_bm25` or ChromaDB's native full-text search capabilities).
    *   Implement **RRF (Reciprocal Rank Fusion)** to merge Vector and BM25 results.
2.  **Router Update:** Add a `hybrid` flag to the `search` tool and `router.py` to allow the agent to opt-in to lexical-heavy search.

### Benchmarking Strategy
*   **The Identifier Test:** Run the "Lexical Hard" segment of the evaluation suite.
*   **Success Metric:** Target a significant increase in Hit Rate for queries involving specific version strings or unique identifiers.

---

## III. Workstream: Contextual Pruning (The "Arcane Recall" Refactor)
**Problem:** Fixed expansion is a token-dumping liability. It returns noise that dilutes LLM focus and wastes context window.

### Tasks & Source Code Changes
1.  **Dynamic Expansion Logic (`src/candlekeep/rag/arcane_recall.py`):**
    *   Replace fixed expansion with **Similarity-Weighted Expansion**.
    *   Calculate similarity between the "Matched Chunk" and its neighbors. Only expand if the neighbor’s similarity to the *query* is within a configured threshold of the match, OR if it contains a continuation marker (e.g., Markdown sub-bullets).
2.  **Window Merging:** Implement a merging algorithm so that if multiple adjacent chunks are retrieved, they share a single merged window rather than creating overlapping, redundant context blocks.

### Benchmarking Strategy
*   **Token Efficiency Metric:** Calculate **Recall-per-Token**.
*   **Goal:** Maintain current `Content Match` while significantly reducing the average returned token count.

---

## IV. Workstream: Latency & Reranking Optimization
**Problem:** High latency for reranking candidates is unacceptable for real-time agent loops.

### Tasks & Source Code Changes
1.  **Reranker Lifecycle (`src/candlekeep/rag/reranker.py`):**
    *   Implement a **Singleton Pattern** or a persistent `InferenceWorker`.
    *   Introduce **Batch Inference**: Score candidates in a single tensor operation rather than a loop.
2.  **Quantization:** Convert the cross-encoder to optimized formats to utilize CPU vector instructions.

### Benchmarking Strategy
*   **Latency Profiling:** Measure `P50` and `P99` for the `Precise` path under concurrent load.
*   **Success Criteria:** Significant reduction in reranking latency on standard CPU hardware.

---

## V. Workstream: Structural Integrity (The "Bardic Knowledge" Audit)
**Problem:** Prefixing metadata (Bardic Knowledge) "smears" the vector space, reducing the semantic distinction between different sections of the same document.

### Tasks & Source Code Changes
1.  **Field-Based Search:**
    *   Remove text-prefixing from `processor.py`.
    *   Store `title` and `description` as explicit metadata fields in ChromaDB.
    *   Use **Metadata Boosting** during retrieval (where ChromaDB filters by metadata first or applies a secondary score weight to matches in title/description).
2.  **Document Centroids:** Experiment with storing a single "Summary Vector" per document. Retrieval becomes a two-step process: (1) Find the best document via summary, (2) Search only within that document's specific chunks.

### Benchmarking Strategy
*   **Discrimination Test:** Ingest 5 documents that discuss the same topic (e.g., "Authentication") but for different platforms (iOS, Android, Web).
*   **Success Metric:** Ensure the system retrieves chunks from the *correct* platform's document without "bleeding" into others due to shared headers/prefixes.

---

## Projected Deliverables
1.  **`candlekeep-bench` CLI:** A standalone tool to run the 100-query eval suite and output a detailed quality report.
2.  **Hybrid Router:** A production-ready search path that survives specific technical identifier queries.
3.  **Quantized Reranker:** A fast, CPU-optimized cross-encoder implementation.

**Final Verdict Objective:** Transition Candlekeep from a "Wizard Sage" prototype into a high-precision, low-latency retrieval engine capable of handling 1M+ chunks without statistical drift.
