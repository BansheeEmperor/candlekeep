"""Benchmark for the search router (hybrid, precise, explore)."""
import pytest
from pathlib import Path

from candlekeep.rag.router import search_with_routing
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES

pytestmark = [pytest.mark.benchmark]


class TestRouterBenchmark:
    """Benchmark quality and latency for both router paths."""
    
    @pytest.mark.parametrize("query_type", ["hybrid", "precise", "explore"])
    def test_router_quality(self, seeded_store, query_type):
        """Run quality benchmark for a specific router path."""
        print(f"\n🚀 Benchmarking Path: {query_type.upper()}")
        
        # Create search function using the router
        def search_fn(query: str, n_results: int):
            return search_with_routing(seeded_store, query, n_results=n_results, query_type=query_type)
        
        # Run benchmark
        benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
        results = benchmark.run(n_results=5)
        summary = benchmark.summarize(results)
        
        # Print report
        benchmark.print_report(results, summary)
        
        # Save results
        output_path = Path(__file__).parent / "results" / f"router_{query_type}_benchmark.json"
        output_path.parent.mkdir(exist_ok=True)
        benchmark.save_results(results, summary, str(output_path))
        
        # ASSERTION LOGIC:
        # 1. We assert on Overall Precision.
        # 2. Adversarial queries (0 expected) now score 100% if they return 0 results.
        # 3. Agent queries (multi-part) are included in the average to ensure the engine 
        #    at least finds *some* relevant context, though 100% is only expected 
        #    via agent-side decomposition.
        if query_type == "hybrid":
            assert summary['avg_precision'] > 0.6, f"Hybrid overall precision ({summary['avg_precision']:.1%}) dropped below 60%"
            assert summary['avg_latency_ms'] < 200, "Hybrid path latency too high"
        elif query_type == "explore":
            assert summary['avg_precision'] > 0.6, f"Explore overall precision ({summary['avg_precision']:.1%}) dropped below 60%"
            assert summary['avg_latency_ms'] < 200, "Explore path latency too high"
        else:
            assert summary['avg_precision'] > 0.6, f"Precise overall precision ({summary['avg_precision']:.1%}) dropped below 60%"
            assert summary['avg_latency_ms'] < 5000, "Precise path latency too high"
