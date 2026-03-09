"""Benchmark HNSW indexing parameters: search_ef, M, and distance metrics."""
import pytest
import json
import tempfile
from pathlib import Path

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES

pytestmark = [pytest.mark.slow]

SAMPLE_DOCS = Path(__file__).parent / "fixtures" / "sample_docs"


def _create_store(hnsw_m=16, hnsw_ef_construction=100, hnsw_ef_search=10, space="cosine"):
    """Create a fresh store with specific HNSW parameters."""
    settings = Settings.from_env()
    settings.chroma_path = tempfile.mkdtemp()
    store = ChromaVectorStore(settings)
    # Replace collection with custom HNSW params
    store.client.delete_collection("candlekeep")
    store.collection = store.client.get_or_create_collection(
        name="candlekeep",
        metadata={
            "hnsw:space": space,
            "hnsw:M": hnsw_m,
            "hnsw:construction_ef": hnsw_ef_construction,
            "hnsw:search_ef": hnsw_ef_search,
            "embedding_model": settings.embedding_model,
        },
    )
    proc = DocumentProcessor(settings)
    for f in SAMPLE_DOCS.glob("*"):
        if f.is_file():
            store.add_documents(proc.process(str(f)))
    return store


def _run_benchmark(store):
    def search_fn(query, n_results):
        return search_with_routing(store, query, n_results, query_type="simple")
    benchmark = RAGBenchmark(search_fn, BENCHMARK_QUERIES)
    results = benchmark.run(n_results=5)
    s = benchmark.summarize(results)
    return {
        "precision": round(s["avg_precision"], 4),
        "recall": round(s["avg_recall"], 4),
        "f1": round(s["f1_score"], 4),
        "content": round(s["content_match_rate"], 4),
        "latency": round(s["avg_latency_ms"], 1),
    }


class TestIndexingBenchmark:
    def test_search_ef_sweep(self):
        """Benchmark different search_ef values."""
        results = {}
        for ef in [10, 25, 50, 100, 200]:
            store = _create_store(hnsw_ef_search=ef)
            results[ef] = _run_benchmark(store)

        print(f"\n{'='*75}")
        print("SEARCH_EF SWEEP (M=16, construction_ef=100, cosine)")
        print(f"{'='*75}")
        print(f"{'ef':>6} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Content':>10} {'Latency':>10}")
        print("-" * 56)
        for ef in [10, 25, 50, 100, 200]:
            r = results[ef]
            print(f"{ef:>6} {r['precision']:>9.1%} {r['recall']:>9.1%} "
                  f"{r['f1']:>9.1%} {r['content']:>9.1%} {r['latency']:>8.1f}ms")
        print(f"{'='*75}")

        out = Path(__file__).parent / "results" / "search_ef_benchmark.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({str(k): v for k, v in results.items()}, indent=2))
        print(f"💾 Saved to {out}")

    def test_distance_metric(self):
        """Benchmark cosine vs l2 vs ip."""
        results = {}
        for metric in ["cosine", "l2", "ip"]:
            store = _create_store(space=metric)
            results[metric] = _run_benchmark(store)

        print(f"\n{'='*75}")
        print("DISTANCE METRIC COMPARISON (M=16, ef=10)")
        print(f"{'='*75}")
        print(f"{'Metric':>8} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Content':>10} {'Latency':>10}")
        print("-" * 58)
        for m in ["cosine", "l2", "ip"]:
            r = results[m]
            print(f"{m:>8} {r['precision']:>9.1%} {r['recall']:>9.1%} "
                  f"{r['f1']:>9.1%} {r['content']:>9.1%} {r['latency']:>8.1f}ms")
        print(f"{'='*75}")

        out = Path(__file__).parent / "results" / "distance_metric_benchmark.json"
        out.write_text(json.dumps(results, indent=2))
        print(f"💾 Saved to {out}")

    def test_m_sweep(self):
        """Benchmark different M values (requires re-ingestion)."""
        results = {}
        for m in [8, 16, 32, 48]:
            store = _create_store(hnsw_m=m)
            results[m] = _run_benchmark(store)

        print(f"\n{'='*75}")
        print("M SWEEP (search_ef=10, construction_ef=100, cosine)")
        print(f"{'='*75}")
        print(f"{'M':>6} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Content':>10} {'Latency':>10}")
        print("-" * 56)
        for m in [8, 16, 32, 48]:
            r = results[m]
            print(f"{m:>6} {r['precision']:>9.1%} {r['recall']:>9.1%} "
                  f"{r['f1']:>9.1%} {r['content']:>9.1%} {r['latency']:>8.1f}ms")
        print(f"{'='*75}")

        out = Path(__file__).parent / "results" / "m_sweep_benchmark.json"
        out.write_text(json.dumps({str(k): v for k, v in results.items()}, indent=2))
        print(f"💾 Saved to {out}")
