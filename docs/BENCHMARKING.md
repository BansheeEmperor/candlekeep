# Benchmarking Infrastructure

Candlekeep utilizes a tiered benchmarking strategy to evaluate retrieval quality and performance, ranging from internal parameter sweeps to comparative framework assessments using RAGAS.

## Flagship Scientific Benchmark (`benchmark_ragas.py`)

The primary tool for cross-framework evaluation is `scripts/benchmark_ragas.py`. This suite implements a controlled methodology to ensure statistically significant results when comparing Candlekeep against LlamaIndex and LangChain.

### Methodology
1.  **Deterministic Sandbox**: Competing frameworks are evaluated against an identical 300-document subset of the **NFCorpus** (Medical IR) dataset.
2.  **Controlled Document Inclusion**: Documents required to resolve test queries are explicitly included in the search pool to ensure Recall measures retrieval effectiveness rather than corpus coverage.
3.  **Standardised Evaluator**: Uses **Claude 4.5 Sonnet** as a consistent reasoning judge to evaluate semantic metrics (Faithfulness, Relevancy, and Recall).
4.  **Full Context Evaluation**: No truncation is applied to retrieved results, ensuring the evaluator sees the complete context as provided by each framework.

### Flagship Comparison Results (RAGAS)

Evaluation performed on the **NFCorpus** dataset (High-jargon Medical IR). All frameworks configured with Advanced Hybrid + Reranking using **Claude 4.5 Sonnet** as the reasoning judge.

| Framework | Faithfulness | Answer Relevancy | Context Recall | Avg Latency |
| :--- | :--- | :--- | :--- | :--- |
| **Candlekeep (Hybrid)** | 0.8649 | 0.5904 | 0.4815 | 107.8ms |
| **LangChain (Advanced)** | 0.8767 | 0.4375 | 0.4957 | 183.0ms |
| **LlamaIndex (Advanced)** | 0.8838 | 0.5636 | 0.4366 | 284.2ms |

*Results averaged over a 15-query flagship run.*

### Findings
- **Latency Efficiency**: Candlekeep demonstrated a measured latency advantage, operating at sub-150ms while competitors required 180ms–285ms under identical hardware and model warmth conditions.
- **Intent Alignment**: The evaluation showed higher Answer Relevancy for Candlekeep (0.59) and LlamaIndex (0.56) compared to LangChain (0.43), suggesting more precise alignment between retrieved context and user intent in this domain.
- **Recall Stability**: All three frameworks achieved similar Recall scores (0.43–0.49), indicating that the primary differentiator in this specific medical IR task is retrieval speed and intent-matching rather than raw document discovery.

## Legacy and Specialised Benchmarks

Specialized benchmarks used for internal parameter tuning are maintained in the `scripts/` directory (e.g., `benchmark_chunk_size.py`, `sweep_hnsw.py`). 

Benchmarks that have been superseded by the RAGAS suite for general framework comparison have been moved to `scripts/archive/`:
- `benchmark_competitors.py`
- `benchmark_baseline.py`
- `run_eval.py`
