"""Measure HNSW non-determinism across fresh re-ingestions.

Drops the collection, re-ingests the full corpus, and runs the Centurion
Set N times. Reports mean and standard deviation for each metric to
quantify the variance introduced by ChromaDB's non-deterministic HNSW
index construction.

Usage:
    python scripts/reproducibility_test.py [--runs 5] [--query-type simple]
"""
import sys
import os
import json
import argparse
import tempfile
import shutil
from pathlib import Path

os.environ["CANDLEKEEP_DEVICE"] = "cpu"

sys.path.append(str(Path(__file__).parent.parent / "src"))

import numpy as np
from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery


def run_single(query_type: str) -> dict:
    """Run one full ingest + eval cycle in a fresh temp DB."""
    temp_dir = tempfile.mkdtemp(prefix="candlekeep_repro_")
    try:
        settings = Settings.from_env()
        settings.chroma_path = temp_dir
        store = ChromaVectorStore(settings)
        processor = DocumentProcessor(settings)

        fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
        for doc in list((fixtures / "sample_docs").glob("*")) + list((fixtures / "scale_docs").glob("*")):
            if doc.is_file():
                store.add_documents(processor.process(str(doc)).chunks)

        suite_path = fixtures / "eval_suite_100.json"
        with open(suite_path) as f:
            suite_data = json.load(f)
        queries = [
            EvalQuery(query=q["query"], expected_sources=q["expected_sources"],
                      category=q["category"], difficulty=q["difficulty"])
            for q in suite_data["queries"]
        ]

        def search_fn(query, k):
            return search_with_routing(store, query, n_results=k, query_type=query_type)

        runner = BenchmarkRunner(search_fn)
        results = runner.run_suite(queries, k=5)
        return runner.summarize(results)
    finally:
        shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(description="HNSW reproducibility test")
    parser.add_argument("--runs", type=int, default=5, help="Number of fresh ingestion cycles")
    parser.add_argument("--query-type", default="hybrid", help="Search path to test")
    args = parser.parse_args()

    metrics_keys = ["mrr", "avg_ndcg_5", "avg_hit_rate_5", "avg_latency_ms", "avg_tokens"]
    all_runs = []

    for i in range(args.runs):
        print(f"\n{'='*40}")
        print(f"RUN {i+1}/{args.runs}")
        print(f"{'='*40}")
        summary = run_single(args.query_type)
        all_runs.append(summary)
        for k in metrics_keys:
            print(f"  {k}: {summary[k]:.4f}")

    print(f"\n{'='*40}")
    print(f"REPRODUCIBILITY SUMMARY ({args.runs} runs, {args.query_type} path)")
    print(f"{'='*40}")
    for k in metrics_keys:
        values = [r[k] for r in all_runs]
        mean = np.mean(values)
        std = np.std(values, ddof=1) if len(values) > 1 else 0.0
        print(f"  {k:20s}: {mean:.4f} ± {std:.4f}")

    # Save raw results
    output_dir = Path(__file__).parent.parent / "tests" / "results"
    output_dir.mkdir(exist_ok=True)
    report = {
        "runs": args.runs,
        "query_type": args.query_type,
        "per_run": [{k: r[k] for k in metrics_keys} for r in all_runs],
        "summary": {
            k: {"mean": float(np.mean([r[k] for r in all_runs])),
                "std": float(np.std([r[k] for r in all_runs], ddof=1)) if args.runs > 1 else 0.0}
            for k in metrics_keys
        }
    }
    report_path = output_dir / f"reproducibility_{args.query_type}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
