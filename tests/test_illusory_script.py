"""Test Illusory Script (HyDE)."""
from candlekeep.rag.illusory_script import search_with_illusory_script
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES


def test_illusory_script(seeded_store):
    """Benchmark Illusory Script technique."""
    def search_fn(query: str, n_results: int):
        return search_with_illusory_script(
            seeded_store,
            query,
            n_results,
            answer_length="medium"
        )
    
    benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
    results = benchmark.run(n_results=5)
    summary = benchmark.summarize(results)
    
    benchmark.print_report(results, summary)
    
    print(f"\n✓ Illusory Script: P={summary['avg_precision']:.1%} "
          f"R={summary['avg_recall']:.1%} F1={summary['f1_score']:.1%} "
          f"Latency={summary['avg_latency_ms']:.0f}ms")
    
    assert summary['avg_precision'] > 0.3
    assert summary['avg_recall'] > 0.3
