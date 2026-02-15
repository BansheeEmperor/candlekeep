"""Test Mirror Image (Multi-Query Retrieval)."""
from candlekeep.rag.mirror_image import search_with_mirror_image
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES


def test_mirror_image(seeded_store):
    """Benchmark Mirror Image technique."""
    # Create search function with Mirror Image
    def search_fn(query: str, n_results: int):
        return search_with_mirror_image(
            seeded_store, 
            query, 
            n_results,
            num_variations=3,
            fetch_per_query=10
        )
    
    # Run benchmark
    benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
    results = benchmark.run(n_results=5)
    summary = benchmark.summarize(results)
    
    # Print report
    benchmark.print_report(results, summary)
    
    print(f"\n✓ Mirror Image: P={summary['avg_precision']:.1%} "
          f"R={summary['avg_recall']:.1%} F1={summary['f1_score']:.1%} "
          f"Latency={summary['avg_latency_ms']:.0f}ms")
    
    # Validate minimum thresholds
    assert summary['avg_precision'] > 0.3, "Precision too low"
    assert summary['avg_recall'] > 0.3, "Recall too low"

