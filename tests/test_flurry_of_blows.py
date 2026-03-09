"""Test Flurry of Blows (Query Decomposition)."""
import pytest
# Skip if module is missing (experimental)
flurry = pytest.importorskip("candlekeep.rag.flurry_of_blows")
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES

pytestmark = [pytest.mark.experimental]


def test_flurry_of_blows(seeded_store):
    """Benchmark Flurry of Blows technique."""
    def search_fn(query: str, n_results: int):
        return flurry.search_with_flurry_of_blows(
            seeded_store,
            query,
            n_results,
            max_sub_questions=3,
            fetch_per_question=5
        )
    
    benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
    results = benchmark.run(n_results=5)
    summary = benchmark.summarize(results)
    
    benchmark.print_report(results, summary)
    
    print(f"\n✓ Flurry of Blows: P={summary['avg_precision']:.1%} "
          f"R={summary['avg_recall']:.1%} F1={summary['f1_score']:.1%} "
          f"Latency={summary['avg_latency_ms']:.0f}ms")
    
    assert summary['avg_precision'] > 0.3
    assert summary['avg_recall'] > 0.3
