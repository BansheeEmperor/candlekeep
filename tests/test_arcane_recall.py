"""Test Arcane Recall (Parent Document Retrieval)."""
from candlekeep.rag.arcane_recall import search_with_arcane_recall
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES


def test_arcane_recall(seeded_store):
    """Benchmark Arcane Recall technique."""
    def search_fn(query: str, n_results: int):
        return search_with_arcane_recall(
            seeded_store,
            query,
            n_results,
            expansion_chunks=2
        )
    
    benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
    results = benchmark.run(n_results=5)
    summary = benchmark.summarize(results)
    
    benchmark.print_report(results, summary)
    
    print(f"\n✓ Arcane Recall: P={summary['avg_precision']:.1%} "
          f"R={summary['avg_recall']:.1%} F1={summary['f1_score']:.1%} "
          f"Latency={summary['avg_latency_ms']:.0f}ms")
    
    assert summary['avg_precision'] > 0.3
    assert summary['avg_recall'] > 0.3
