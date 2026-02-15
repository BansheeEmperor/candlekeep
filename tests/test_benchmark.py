"""Benchmark tests using pytest."""
import pytest
from pathlib import Path

from candlekeep.rag.search import search_with_preprocessing
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES


class TestRAGBenchmark:
    """RAG quality benchmark tests."""
    
    def test_baseline_benchmark(self, seeded_store):
        """Run baseline benchmark and validate metrics."""
        # Create search function
        def search_fn(query: str, n_results: int):
            return search_with_preprocessing(seeded_store, query, n_results)
        
        # Run benchmark
        benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
        results = benchmark.run(n_results=5)
        summary = benchmark.summarize(results)
        
        # Print report
        benchmark.print_report(results, summary)
        
        # Save results
        output_path = Path(__file__).parent / "results" / "baseline.json"
        output_path.parent.mkdir(exist_ok=True)
        benchmark.save_results(results, summary, str(output_path))
        
        # Validate minimum quality thresholds
        assert summary['avg_precision'] > 0.3, "Precision too low"
        assert summary['avg_recall'] > 0.3, "Recall too low"
        assert summary['f1_score'] > 0.3, "F1 score too low"
        assert summary['avg_latency_ms'] < 5000, "Latency too high"
        
        print(f"\n✓ Baseline: P={summary['avg_precision']:.1%} "
              f"R={summary['avg_recall']:.1%} F1={summary['f1_score']:.1%}")
    
    @pytest.mark.parametrize("query_data", BENCHMARK_QUERIES, ids=lambda q: f"{q.difficulty}:{q.query[:30]}")
    def test_individual_queries(self, seeded_store, query_data):
        """Test each query individually for debugging."""
        def search_fn(query: str, n_results: int):
            return search_with_preprocessing(seeded_store, query, n_results)
        
        benchmark = RAGBenchmark(search_fn, [query_data])
        results = benchmark.run(n_results=5)
        
        result = results[0]
        
        # Soft assertions - log failures but don't fail test
        if result.precision < 0.3 or result.recall < 0.3:
            print(f"\n⚠️  Low quality for: {query_data.query}")
            print(f"   P={result.precision:.1%} R={result.recall:.1%}")
            print(f"   Expected: {query_data.expected_sources}")
            print(f"   Got: {result.retrieved_sources}")
