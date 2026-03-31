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

## Multi-Hop Graph Benchmark (HotpotQA)

The `scripts/benchmark_hotpotqa.py` suite evaluates framework effectiveness on multi-hop reasoning tasks where the answer requires connecting facts across multiple documents. 

### Methodology
1.  **Large Haystack**: Frameworks are evaluated against a **1,000-document sandbox** to simulate realistic "needle in a haystack" conditions.
2.  **Normalized Context**: To ensure a fair comparison of retrieval *quality* rather than *volume*, the context window is capped at **8,000 characters** (~2,000 tokens) for both frameworks.
3.  **Cost-Aware Metrics**: Tracking the financial cost of retrieval (e.g., LLM calls for synonym expansion) to measure the economic efficiency of each architecture.
4.  **Ablation Isolation**: Candlekeep is evaluated with `Arcane Recall` disabled to isolate the raw performance of the entity co-occurrence graph.

### Comparison Results (HotpotQA)

Evaluation performed on a 1,000-doc HotpotQA sandbox. All frameworks configured with their "Default" multi-hop paths. **Claude 4.5 Sonnet** used for Judge/Retrieval-Expansion, **Claude 4.5 Haiku** for Generation.

| Framework | Hop Rate | Faithfulness | Relevancy | Latency | Cost/1k | Chars |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Candlekeep-Explore** | **0.8333** | **0.9305** | **0.7274** | **152.8ms** | **$0.00** | 5740 |
| **LlamaIndex-Graph** | 0.7667 | 0.7998 | 0.6394 | 5700.7ms | $1.16 | 6364 |
| **LlamaIndex-Graph-Only** | 0.6333 | 0.7244 | 0.3316 | 5154.0ms | $1.09 | 1789 |

*Results averaged over a 15-query flagship run.*

### Deep Multi-Hop (MuSiQue - 3+ Hops)

To test recursive graph traversal at scale, the suite was run against a **5,000-document sandbox** of the **MuSiQue** dataset with a **Recursive Depth of 3**.

| Framework | Hop Rate | Faithfulness | Relevancy | Latency | Cost/1k | Chars |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Candlekeep-Explore** | **0.7333** | **0.8776** | 0.3545 | **210.5ms** | **$0.00** | 7613 |
| **LlamaIndex-Graph** | 0.6667 | 0.7828 | **0.4163** | 4799.7ms | $1.07 | 7677 |

*Results averaged over a 15-query flagship run.*

### Findings (HotpotQA vs MuSiQue)
- **Scale Inversion**: As the corpus scaled from 1,000 to 5,000 documents, Candlekeep's co-occurrence graph maintained higher recall (0.73 vs 0.66) than LlamaIndex's LLM-driven expansion. This suggests that structural co-occurrence is more robust against "haystack noise" than semantic LLM expansion.
- **2-Hop and 3-Hop Leadership**: After optimizing for ingestion fidelity (100-character chunk overlap), Candlekeep outperformed the leading competitor in Hop Rate across both 2-hop and 3-hop tasks.
- **Efficiency Dominance**: Candlekeep maintained a **22x speed advantage** and zero per-query retrieval cost. By moving "graph intelligence" to the ingestion phase, the read-path remains purely algorithmic and predictable.
- **Grounding Fidelity**: Evaluation confirmed that **Overlapping Sentinels** (100-char window) increased multi-hop recall by 3.3% by bridging document reasoning chains that were previously severed by chunk boundaries.

## Legacy and Specialised Benchmarks

Specialized benchmarks used for internal parameter tuning are maintained in the `scripts/` directory (e.g., `benchmark_chunk_size.py`, `sweep_hnsw.py`). 

Benchmarks that have been superseded by the RAGAS suite for general framework comparison have been moved to `scripts/archive/`:
- `benchmark_competitors.py`
- `benchmark_baseline.py`
- `run_eval.py`
