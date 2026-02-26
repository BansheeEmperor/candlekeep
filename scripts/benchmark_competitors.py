#!/usr/bin/env python3
"""Competitive benchmark runner.

Runs all competitors against the Centurion Set on the primary corpus,
produces per-query results, and saves a JSON report for analysis.

Usage:
    python scripts/benchmark_competitors.py [--runs 5] [--competitors naive,naive-rerank,candlekeep-simple]
"""
import sys
import os
import json
import argparse
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any

# Force CPU for consistent benchmarking
os.environ["CANDLEKEEP_DEVICE"] = "cpu"
# Suppress model loading progress bars and warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import logging
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from candlekeep.eval.metrics import (
    calculate_reciprocal_rank,
    calculate_ndcg,
    calculate_ndcg_graded,
    calculate_hit_rate,
    calculate_precision_at_k,
)
from candlekeep.eval.statistics import bootstrap_ci
from scripts.competitors.base import Competitor, timed_search


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class QueryResult:
    competitor: str
    run: int
    query: str
    category: str
    difficulty: str
    retrieved_sources: list[str]
    rr: float
    ndcg_5: float
    hit_rate_1: float
    hit_rate_5: float
    precision_5: float
    content_match: float
    latency_ms: float
    tokens: int
    ndcg_5_graded: float = -1.0


@dataclass
class EvalQuery:
    query: str
    expected_sources: list[str]
    category: str
    difficulty: str
    expected_content: list[str]
    graded_relevance: dict[str, int] | None = None


# ── Competitor registry ─────────────────────────────────────────────

def build_competitor(name: str) -> Competitor:
    """Instantiate a competitor by name."""
    from scripts.competitors.naive import NaiveVectorSearch
    from scripts.competitors.naive_rerank import NaiveRerank
    from scripts.competitors.candlekeep_configs import (
        make_candlekeep_simple,
        make_candlekeep_hybrid,
        make_candlekeep_precise,
        make_ablation_no_bardic,
        make_ablation_no_arcane,
        make_ablation_no_ward,
        make_ablation_no_negation,
        make_bk_all_simple,
        make_bk_all_hybrid,
        make_bk_none_simple,
        make_bk_none_hybrid,
        make_bk_first_simple,
        make_bk_first_hybrid,
        make_bk_title_simple,
        make_bk_title_hybrid,
        make_bk_skip_simple,
        make_bk_skip_hybrid,
    )

    from scripts.competitors.langchain_rag import LangChainRAG
    from scripts.competitors.ragatouille_colbert import RAGatouilleCompetitor
    from scripts.competitors.colbert_hybrid import ColBERTHybrid
    from scripts.competitors.colbert_replace import ColBERTReplaceBM25, ColBERTReplaceDense
    from scripts.competitors.llamaindex_rag import LlamaIndexRAG
    from scripts.competitors.haystack_rag import HaystackRAG

    registry = {
        "naive": NaiveVectorSearch,
        "naive-rerank": NaiveRerank,
        "langchain": lambda: LangChainRAG(use_mmr=False),
        "langchain-mmr": lambda: LangChainRAG(use_mmr=True),
        "ragatouille": RAGatouilleCompetitor,
        "colbert-hybrid": ColBERTHybrid,
        "colbert-replace-bm25": ColBERTReplaceBM25,
        "colbert-replace-vector": ColBERTReplaceDense,
        "llamaindex": lambda: LlamaIndexRAG(use_window=False),
        "llamaindex-window": lambda: LlamaIndexRAG(use_window=True),
        "llamaindex-arcane": lambda: __import__('scripts.competitors.llamaindex_rag', fromlist=['LlamaIndexArcaneRecall']).LlamaIndexArcaneRecall(),
        "llamaindex-bk-arcane": lambda: __import__('scripts.competitors.llamaindex_rag', fromlist=['LlamaIndexBKArcane']).LlamaIndexBKArcane(),
        "haystack": HaystackRAG,
        "candlekeep-simple": make_candlekeep_simple,
        "candlekeep-hybrid": make_candlekeep_hybrid,
        "candlekeep-precise": make_candlekeep_precise,
        "ablation-no-bardic-knowledge": make_ablation_no_bardic,
        "ablation-no-arcane-recall": make_ablation_no_arcane,
        "ablation-no-relevance-ward": make_ablation_no_ward,
        "ablation-no-negation-preprocessing": make_ablation_no_negation,
        "bk-all-simple": make_bk_all_simple,
        "bk-all-hybrid": make_bk_all_hybrid,
        "bk-none-simple": make_bk_none_simple,
        "bk-none-hybrid": make_bk_none_hybrid,
        "bk-first-simple": make_bk_first_simple,
        "bk-first-hybrid": make_bk_first_hybrid,
        "bk-title-simple": make_bk_title_simple,
        "bk-title-hybrid": make_bk_title_hybrid,
        "bk-skip-simple": make_bk_skip_simple,
        "bk-skip-hybrid": make_bk_skip_hybrid,
    }

    if name not in registry:
        raise ValueError(f"Unknown competitor: {name}. Available: {list(registry.keys())}")
    return registry[name]()


ALL_COMPETITORS = [
    "naive",
    "naive-rerank",
    "langchain",
    "langchain-mmr",
    "candlekeep-simple",
    "candlekeep-hybrid",
    "candlekeep-precise",
    "ablation-no-bardic-knowledge",
    "ablation-no-arcane-recall",
    "ablation-no-relevance-ward",
    "ablation-no-negation-preprocessing",
]


# ── Corpus loading ──────────────────────────────────────────────────

def get_corpus_paths() -> list[Path]:
    """Get all document paths for the primary corpus."""
    fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
    paths = []
    for subdir in ["sample_docs", "scale_docs"]:
        d = fixtures / subdir
        if d.exists():
            paths.extend(p for p in d.glob("*") if p.is_file())
    return sorted(paths)


def load_eval_suite() -> list[EvalQuery]:
    """Load the Centurion Set."""
    suite_path = Path(__file__).parent.parent / "tests" / "fixtures" / "eval_suite_100.json"
    with open(suite_path) as f:
        data = json.load(f)
    return [
        EvalQuery(
            query=q["query"],
            expected_sources=q["expected_sources"],
            category=q["category"],
            difficulty=q["difficulty"],
            expected_content=q.get("expected_content", []),
            graded_relevance=q.get("graded_relevance"),
        )
        for q in data["queries"]
    ]


# ── Evaluation ──────────────────────────────────────────────────────

def evaluate_query(
    competitor: Competitor,
    query: EvalQuery,
    run_idx: int,
    k: int = 5,
) -> QueryResult:
    """Run a single query against a competitor and compute metrics."""
    results, latency_ms = timed_search(competitor, query.query, k)

    retrieved_sources = []
    retrieved_chunk_ids = []
    for r in results:
        source = r.metadata.get("source", "")
        if "tests/fixtures" in source:
            source = source[source.index("tests/fixtures"):]
        retrieved_sources.append(source)
        chunk_idx = r.metadata.get("chunk_index", 0)
        retrieved_chunk_ids.append(f"{source}:{chunk_idx}")

    ground_truth = set(query.expected_sources)
    total_chars = sum(len(r.text) for r in results)

    # Content match: fraction of expected keywords found in retrieved text
    cm = -1.0
    if query.expected_content:
        combined = " ".join(r.text for r in results).lower()
        hits = sum(1 for kw in query.expected_content if kw.lower() in combined)
        cm = hits / len(query.expected_content)

    # Graded nDCG
    ndcg_g = -1.0
    if query.graded_relevance:
        ndcg_g = calculate_ndcg_graded(retrieved_chunk_ids, query.graded_relevance, k)

    return QueryResult(
        competitor=competitor.name,
        run=run_idx,
        query=query.query,
        category=query.category,
        difficulty=query.difficulty,
        retrieved_sources=retrieved_sources,
        rr=calculate_reciprocal_rank(retrieved_sources, ground_truth),
        ndcg_5=calculate_ndcg(retrieved_sources, ground_truth, 5),
        hit_rate_1=calculate_hit_rate(retrieved_sources, ground_truth, 1),
        hit_rate_5=calculate_hit_rate(retrieved_sources, ground_truth, 5),
        precision_5=calculate_precision_at_k(retrieved_sources, ground_truth, 5),
        content_match=cm,
        latency_ms=latency_ms,
        tokens=total_chars // 4,
        ndcg_5_graded=ndcg_g,
    )


# ── Summarization ──────────────────────────────────────────────────

def summarize_competitor(results: list[QueryResult]) -> dict[str, Any]:
    """Aggregate metrics for a single competitor across all runs."""
    if not results:
        return {}

    mrr_scores = [r.rr for r in results]
    ndcg_scores = [r.ndcg_5 for r in results]
    hr5_scores = [r.hit_rate_5 for r in results]
    hr1_scores = [r.hit_rate_1 for r in results]
    p5_scores = [r.precision_5 for r in results]
    latencies = [r.latency_ms for r in results]
    token_counts = [r.tokens for r in results]

    mrr_mean, mrr_lo, mrr_hi = bootstrap_ci(mrr_scores)
    ndcg_mean, ndcg_lo, ndcg_hi = bootstrap_ci(ndcg_scores)
    hr5_mean, hr5_lo, hr5_hi = bootstrap_ci(hr5_scores)

    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    summary = {
        "competitor": results[0].competitor,
        "total_queries": len(results),
        "runs": max(r.run for r in results) + 1,
        "mrr": mrr_mean,
        "mrr_ci": [mrr_lo, mrr_hi],
        "ndcg_5": ndcg_mean,
        "ndcg_5_ci": [ndcg_lo, ndcg_hi],
        "hit_rate_1": sum(hr1_scores) / len(hr1_scores),
        "hit_rate_5": hr5_mean,
        "hit_rate_5_ci": [hr5_lo, hr5_hi],
        "precision_5": sum(p5_scores) / len(p5_scores),
        "content_match": (
            sum(r.content_match for r in results if r.content_match >= 0)
            / max(1, sum(1 for r in results if r.content_match >= 0))
        ),
        "latency_p50": latencies_sorted[n // 2] if n else 0,
        "latency_p95": latencies_sorted[int(n * 0.95)] if n else 0,
        "latency_p99": latencies_sorted[int(n * 0.99)] if n else 0,
        "avg_tokens": sum(token_counts) / len(token_counts) if token_counts else 0,
        "by_category": {},
    }

    # Graded nDCG (when annotations are present)
    graded_scores = [r.ndcg_5_graded for r in results if r.ndcg_5_graded >= 0]
    if graded_scores:
        g_mean, g_lo, g_hi = bootstrap_ci(graded_scores)
        summary["ndcg_5_graded"] = g_mean
        summary["ndcg_5_graded_ci"] = [g_lo, g_hi]

    categories = set(r.category for r in results)
    for cat in sorted(categories):
        cat_results = [r for r in results if r.category == cat]
        cat_mrr, cat_mrr_lo, cat_mrr_hi = bootstrap_ci([r.rr for r in cat_results])
        cat_hr5, cat_hr5_lo, cat_hr5_hi = bootstrap_ci([r.hit_rate_5 for r in cat_results])
        cat_summary = {
            "mrr": cat_mrr,
            "mrr_ci": [cat_mrr_lo, cat_mrr_hi],
            "hit_rate_5": cat_hr5,
            "hit_rate_5_ci": [cat_hr5_lo, cat_hr5_hi],
            "ndcg_5": sum(r.ndcg_5 for r in cat_results) / len(cat_results),
            "precision_5": sum(r.precision_5 for r in cat_results) / len(cat_results),
            "count": len(cat_results),
        }
        cat_graded = [r.ndcg_5_graded for r in cat_results if r.ndcg_5_graded >= 0]
        if cat_graded:
            cat_summary["ndcg_5_graded"] = sum(cat_graded) / len(cat_graded)
        summary["by_category"][cat] = cat_summary

    return summary


# ── Main ────────────────────────────────────────────────────────────

def run_benchmark(
    competitor_names: list[str] | None = None,
    n_runs: int = 5,
    k: int = 5,
    warmup_queries: int = 5,
) -> dict[str, Any]:
    """Run the full competitive benchmark."""
    competitor_names = competitor_names or ALL_COMPETITORS
    corpus_paths = get_corpus_paths()
    queries = load_eval_suite()

    print(f"Corpus: {len(corpus_paths)} documents")
    print(f"Queries: {len(queries)} (Centurion Set)")
    print(f"Competitors: {len(competitor_names)}")
    print(f"Runs: {n_runs}")
    print(f"Total evaluations: {len(competitor_names) * n_runs * len(queries)}")
    print()

    all_results: dict[str, list[QueryResult]] = {}

    for comp_name in competitor_names:
        print(f"{'='*60}")
        print(f"  {comp_name}")
        print(f"{'='*60}")

        competitor = build_competitor(comp_name)
        comp_results = []

        for run_idx in range(n_runs):
            print(f"  Run {run_idx + 1}/{n_runs}: ", end="", flush=True)
            run_start = time.time()

            competitor.reset()
            chunk_count = competitor.ingest(corpus_paths)

            # Warm-up (not scored)
            for q in queries[:warmup_queries]:
                competitor.search(q.query, k)

            # Scored queries
            for q in queries:
                result = evaluate_query(competitor, q, run_idx, k)
                comp_results.append(result)

            elapsed = time.time() - run_start
            run_results = [r for r in comp_results if r.run == run_idx]
            run_mrr = sum(r.rr for r in run_results) / len(run_results)
            print(f"{chunk_count} chunks, MRR={run_mrr:.4f}, {elapsed:.1f}s")

        all_results[comp_name] = comp_results

        # Cleanup temp dirs for Candlekeep competitors
        if hasattr(competitor, "cleanup"):
            competitor.cleanup()

    # Summarize
    summaries = {}
    for comp_name, results in all_results.items():
        summaries[comp_name] = summarize_competitor(results)

    return {
        "metadata": {
            "corpus_docs": len(corpus_paths),
            "query_count": len(queries),
            "runs": n_runs,
            "k": k,
            "warmup_queries": warmup_queries,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "summaries": summaries,
        "details": {
            comp_name: [asdict(r) for r in results]
            for comp_name, results in all_results.items()
        },
    }


def print_summary_table(report: dict[str, Any]) -> None:
    """Print a formatted summary table."""
    summaries = report["summaries"]

    header = f"{'Competitor':<35} {'MRR':>7} {'nDCG@5':>7} {'gNDCG':>7} {'HR@5':>7} {'HR@1':>7} {'P@5':>7} {'CM':>7} {'p50ms':>7} {'Tokens':>7}"
    print()
    print(header)
    print("-" * len(header))

    for name, s in summaries.items():
        gndcg = s.get('ndcg_5_graded', -1)
        gndcg_str = f"{gndcg:>7.4f}" if gndcg >= 0 else f"{'N/A':>7}"
        print(
            f"{name:<35} "
            f"{s['mrr']:>7.4f} "
            f"{s['ndcg_5']:>7.4f} "
            f"{gndcg_str} "
            f"{s['hit_rate_5']:>7.4f} "
            f"{s['hit_rate_1']:>7.4f} "
            f"{s['precision_5']:>7.4f} "
            f"{s.get('content_match', 0):>7.4f} "
            f"{s['latency_p50']:>7.1f} "
            f"{s['avg_tokens']:>7.0f}"
        )

    # Per-category breakdown
    categories = set()
    for s in summaries.values():
        categories.update(s.get("by_category", {}).keys())

    for cat in sorted(categories):
        print(f"\n  Category: {cat}")
        cat_header = f"  {'Competitor':<33} {'MRR':>7} {'HR@5':>7} {'nDCG@5':>7} {'gNDCG':>7} {'n':>5}"
        print(cat_header)
        print("  " + "-" * (len(cat_header) - 2))
        for name, s in summaries.items():
            cat_data = s.get("by_category", {}).get(cat)
            if cat_data:
                gndcg = cat_data.get('ndcg_5_graded', -1)
                gndcg_str = f"{gndcg:>7.4f}" if gndcg >= 0 else f"{'N/A':>7}"
                print(
                    f"  {name:<33} "
                    f"{cat_data['mrr']:>7.4f} "
                    f"{cat_data['hit_rate_5']:>7.4f} "
                    f"{cat_data['ndcg_5']:>7.4f} "
                    f"{gndcg_str} "
                    f"{cat_data['count']:>5}"
                )


def main():
    parser = argparse.ArgumentParser(description="Competitive RAG benchmark")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs per competitor")
    parser.add_argument(
        "--competitors",
        type=str,
        default=None,
        help="Comma-separated competitor names (default: all)",
    )
    parser.add_argument("--k", type=int, default=5, help="Top-k results")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    competitor_names = args.competitors.split(",") if args.competitors else None

    report = run_benchmark(
        competitor_names=competitor_names,
        n_runs=args.runs,
        k=args.k,
    )

    print_summary_table(report)

    # Save report
    output_dir = Path(__file__).parent.parent / "tests" / "results"
    output_dir.mkdir(exist_ok=True)
    output_path = args.output or str(output_dir / "competitive_benchmark.json")
    Path(output_path).write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    main()
