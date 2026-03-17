#!/usr/bin/env python3
"""Benchmark graph augmentation: Hit Rate@5, latency overhead, entity precision.

Usage:
    python scripts/benchmark_graph_augment.py

Requires a live ChromaDB with the Candlekeep corpus ingested.

Outputs results to tests/results/graph_augment_benchmark.json.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.router import search_with_routing
from tests.entity_relationship_queries import ENTITY_RELATIONSHIP_QUERIES


def hit_rate_at_k(results, expected_sources_contain: list[str], k: int = 5) -> bool:
    """Return True if any top-k result's source contains any expected substring."""
    for r in results[:k]:
        source = r.metadata.get("source", "") + r.metadata.get("filename", "")
        if any(exp.lower() in source.lower() for exp in expected_sources_contain):
            return True
    return False


def run_benchmark():
    settings = Settings.from_env()
    db = ChromaVectorStore(settings)

    results_with = []
    results_without = []
    latencies_graph_step = []

    for item in ENTITY_RELATIONSHIP_QUERIES:
        query = item["query"]
        expected = item["expected_sources_contain"]

        # With graph augmentation
        os.environ["CANDLEKEEP_GRAPH_AUGMENT"] = "true"
        t0 = time.perf_counter()
        hits_with = search_with_routing(db, query, n_results=5, query_type="hybrid")
        t_with = time.perf_counter() - t0

        # Without graph augmentation
        os.environ["CANDLEKEEP_GRAPH_AUGMENT"] = "false"
        t0 = time.perf_counter()
        hits_without = search_with_routing(db, query, n_results=5, query_type="hybrid")
        t_without = time.perf_counter() - t0

        os.environ["CANDLEKEEP_GRAPH_AUGMENT"] = "true"

        hit_w = hit_rate_at_k(hits_with, expected)
        hit_wo = hit_rate_at_k(hits_without, expected)
        latency_overhead_ms = (t_with - t_without) * 1000

        results_with.append(hit_w)
        results_without.append(hit_wo)
        latencies_graph_step.append(latency_overhead_ms)

        print(f"{'✓' if hit_w else '✗'} [graph] {'✓' if hit_wo else '✗'} [base]  "
              f"+{latency_overhead_ms:.1f}ms  {query[:60]}")

    n = len(ENTITY_RELATIONSHIP_QUERIES)
    hr_with = sum(results_with) / n
    hr_without = sum(results_without) / n
    improvement = (hr_with - hr_without) / max(hr_without, 0.001) * 100

    latencies_sorted = sorted(latencies_graph_step)
    p50 = latencies_sorted[len(latencies_sorted) // 2]
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]

    print(f"\n{'='*60}")
    print(f"Hit Rate@5 with graph:    {hr_with:.1%}")
    print(f"Hit Rate@5 without graph: {hr_without:.1%}")
    print(f"Improvement:              {improvement:+.1f}%  (target: ≥25%)")
    print(f"Latency overhead p50:     {p50:.1f}ms  (target: ≤5ms)")
    print(f"Latency overhead p95:     {p95:.1f}ms")

    passed = improvement >= 25 and p50 <= 5
    print(f"\nBenchmark {'PASSED ✓' if passed else 'FAILED ✗'}")

    output = {
        "hit_rate_with_graph": hr_with,
        "hit_rate_without_graph": hr_without,
        "improvement_pct": improvement,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "n_queries": n,
        "passed": passed,
        "per_query": [
            {
                "query": item["query"],
                "hit_with": hw,
                "hit_without": hwo,
                "latency_overhead_ms": lat,
            }
            for item, hw, hwo, lat in zip(
                ENTITY_RELATIONSHIP_QUERIES, results_with, results_without, latencies_graph_step
            )
        ],
    }

    out_path = Path(__file__).parent.parent / "tests/results/graph_augment_benchmark.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults written to {out_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run_benchmark())
