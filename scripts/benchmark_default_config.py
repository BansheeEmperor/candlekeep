#!/usr/bin/env python3
"""Default-config competitive benchmark.

Compares Candlekeep out-of-the-box vs LangChain out-of-the-box.
Each system uses its own recommended defaults — embedding model,
chunking strategy, and retrieval method.

This answers: "If a team picks LangChain vs Candlekeep, which
system produces better results end-to-end?"

The forced-equal benchmark (benchmark_competitors.py) isolates
retrieval strategy. This benchmark tests the full stack.

Usage:
    python scripts/benchmark_default_config.py [--runs 3]
"""
import sys
import os
import json
import argparse
import time
from pathlib import Path

os.environ["CANDLEKEEP_DEVICE"] = "cpu"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import logging
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmark_competitors import (
    build_competitor,
    get_corpus_paths,
    load_eval_suite,
    evaluate_query,
    summarize_competitor,
    print_summary_table,
    QueryResult,
)
from scripts.competitors.base import timed_search


COMPETITORS = [
    "langchain-defaults",   # LangChain out-of-the-box (mpnet, 1000/200)
    "langchain",            # LangChain forced-equal (bge-small, 512/50)
    "candlekeep-hybrid",    # Candlekeep default path
    "candlekeep-simple",    # Candlekeep simple path
    "naive",                # Baseline: raw vector search (bge-small, 512/50)
]


def main():
    parser = argparse.ArgumentParser(description="Default-config competitive benchmark")
    parser.add_argument("--runs", type=int, default=3, help="Runs per competitor")
    parser.add_argument("--k", type=int, default=5, help="Top-k results")
    args = parser.parse_args()

    corpus_paths = get_corpus_paths()
    queries = load_eval_suite()

    print("=" * 60)
    print("  DEFAULT-CONFIG COMPETITIVE BENCHMARK")
    print("=" * 60)
    print()
    print(f"Corpus: {len(corpus_paths)} documents")
    print(f"Queries: {len(queries)} (Centurion Set)")
    print(f"Runs: {args.runs}")
    print()
    print("Competitors:")
    print("  langchain-defaults  — mpnet-base-v2, 1000/200 chunks, similarity search")
    print("  langchain           — bge-small, 512/50 chunks (forced-equal control)")
    print("  candlekeep-hybrid   — bge-small, md-header chunks, hybrid path")
    print("  candlekeep-simple   — bge-small, md-header chunks, simple path")
    print("  naive               — bge-small, 512/50 chunks (baseline)")
    print()

    all_results = {}

    for comp_name in COMPETITORS:
        print(f"{'='*60}")
        print(f"  {comp_name}")
        print(f"{'='*60}")

        competitor = build_competitor(comp_name)
        comp_results = []

        for run_idx in range(args.runs):
            print(f"  Run {run_idx + 1}/{args.runs}: ", end="", flush=True)
            run_start = time.time()

            competitor.reset()
            chunk_count = competitor.ingest(corpus_paths)

            # Warm-up
            for q in queries[:5]:
                competitor.search(q.query, args.k)

            # Scored
            for q in queries:
                result = evaluate_query(competitor, q, run_idx, args.k)
                comp_results.append(result)

            elapsed = time.time() - run_start
            run_results = [r for r in comp_results if r.run == run_idx]
            run_mrr = sum(r.rr for r in run_results) / len(run_results)
            print(f"{chunk_count} chunks, MRR={run_mrr:.4f}, {elapsed:.1f}s")

        all_results[comp_name] = comp_results

        if hasattr(competitor, "cleanup"):
            competitor.cleanup()

    # Summarize
    summaries = {}
    for comp_name, results in all_results.items():
        summaries[comp_name] = summarize_competitor(results)

    report = {
        "metadata": {
            "benchmark": "default-config-competitive",
            "corpus_docs": len(corpus_paths),
            "query_count": len(queries),
            "runs": args.runs,
            "k": args.k,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "configs": {
                "langchain-defaults": {
                    "embedding": "sentence-transformers/all-mpnet-base-v2 (109M, 768d)",
                    "chunking": "RecursiveCharacterTextSplitter(1000, 200)",
                    "retrieval": "Chroma similarity_search",
                },
                "langchain": {
                    "embedding": "BAAI/bge-small-en-v1.5 (33M, 384d)",
                    "chunking": "RecursiveCharacterTextSplitter(512, 50) forced-equal",
                    "retrieval": "Chroma similarity_search",
                },
                "candlekeep-hybrid": {
                    "embedding": "BAAI/bge-small-en-v1.5 (33M, 384d)",
                    "chunking": "markdown-header-aware (512, 50)",
                    "retrieval": "vector + BM25 + RRF + Arcane Recall + Relevance Ward",
                },
                "candlekeep-simple": {
                    "embedding": "BAAI/bge-small-en-v1.5 (33M, 384d)",
                    "chunking": "markdown-header-aware (512, 50)",
                    "retrieval": "vector + Arcane Recall + Relevance Ward",
                },
                "naive": {
                    "embedding": "BAAI/bge-small-en-v1.5 (33M, 384d)",
                    "chunking": "fixed-size (512, 50)",
                    "retrieval": "raw cosine similarity top-k",
                },
            },
        },
        "summaries": summaries,
        "details": {
            comp_name: [
                {
                    "competitor": r.competitor,
                    "run": r.run,
                    "query": r.query,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "retrieved_sources": r.retrieved_sources,
                    "rr": r.rr,
                    "ndcg_5": r.ndcg_5,
                    "hit_rate_1": r.hit_rate_1,
                    "hit_rate_5": r.hit_rate_5,
                    "precision_5": r.precision_5,
                    "content_match": r.content_match,
                    "latency_ms": r.latency_ms,
                    "tokens": r.tokens,
                }
                for r in results
            ]
            for comp_name, results in all_results.items()
        },
    }

    print_summary_table(report)

    # Comparison table
    print()
    print("=" * 60)
    print("  OUT-OF-THE-BOX COMPARISON")
    print("=" * 60)
    lc_def = summaries.get("langchain-defaults", {})
    ck_hyb = summaries.get("candlekeep-hybrid", {})
    if lc_def and ck_hyb:
        metrics = ["mrr", "ndcg_5", "hit_rate_5", "hit_rate_1", "precision_5", "latency_p50", "avg_tokens"]
        labels = ["MRR", "nDCG@5", "HR@5", "HR@1", "P@5", "p50 (ms)", "Tokens"]
        fmt = {"mrr": ".4f", "ndcg_5": ".4f", "hit_rate_5": ".4f", "hit_rate_1": ".4f",
               "precision_5": ".4f", "latency_p50": ".1f", "avg_tokens": ".0f"}
        print(f"  {'Metric':<12} {'LangChain':>12} {'Candlekeep':>12} {'Delta':>12}")
        print(f"  {'-'*48}")
        for metric, label in zip(metrics, labels):
            lc_val = lc_def.get(metric, 0)
            ck_val = ck_hyb.get(metric, 0)
            delta = ck_val - lc_val
            f = fmt[metric]
            sign = "+" if delta > 0 else ""
            print(f"  {label:<12} {lc_val:>12{f}} {ck_val:>12{f}} {sign}{delta:>11{f}}")

    # Save
    output_dir = Path(__file__).parent.parent / "tests" / "results"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "default_config_benchmark.json"
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    main()
