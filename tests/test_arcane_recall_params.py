"""Test Arcane Recall with different expansion sizes."""
import pytest
from candlekeep.rag.arcane_recall import search_with_arcane_recall
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES


@pytest.mark.parametrize("expansion_chunks", [1, 2, 3, 4])
def test_arcane_recall_expansion_sizes(seeded_store, expansion_chunks):
    """Benchmark Arcane Recall with different expansion sizes."""
    def search_fn(query: str, n_results: int):
        return search_with_arcane_recall(
            seeded_store,
            query,
            n_results,
            expansion_chunks=expansion_chunks
        )
    
    benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
    results = benchmark.run(n_results=5)
    summary = benchmark.summarize(results)
    
    print(f"\n✓ Arcane Recall (±{expansion_chunks} chunks): "
          f"P={summary['avg_precision']:.1%} "
          f"R={summary['avg_recall']:.1%} "
          f"Content={summary['content_match_rate']:.1%} "
          f"Latency={summary['avg_latency_ms']:.0f}ms")
    
    assert summary['avg_precision'] > 0.3
    assert summary['avg_recall'] > 0.3
