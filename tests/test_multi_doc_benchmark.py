"""Multi-document query benchmark against scale corpus."""
import json
import time
from pathlib import Path

import pytest

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from tests.benchmark import RAGBenchmark
from tests.multi_doc_queries import MULTI_DOC_QUERIES

SCALE_DOCS = Path(__file__).parent / "fixtures" / "scale_docs"


@pytest.fixture(scope="module")
def scale_store():
    import tempfile
    settings = Settings.from_env()
    settings.chroma_path = tempfile.mkdtemp()
    store = ChromaVectorStore(settings)
    proc = DocumentProcessor(settings)

    if not SCALE_DOCS.exists():
        pytest.skip("Scale corpus not generated")

    for f in sorted(SCALE_DOCS.glob("*.md")):
        store.add_documents(proc.process(str(f)).chunks)

    print(f"\n📦 {store.collection.count()} chunks ingested")
    return store


class TestMultiDocBenchmark:
    def test_multi_doc_queries(self, scale_store):
        """Benchmark multi-document queries on scale corpus."""

        def search_fn(query, n_results):
            return search_with_routing(scale_store, query, n_results, query_type="simple")

        benchmark = RAGBenchmark(search_fn, MULTI_DOC_QUERIES)
        results = benchmark.run(n_results=5)
        summary = benchmark.summarize(results)
        benchmark.print_report(results, summary)

        # Save
        out = Path(__file__).parent / "results" / "multi_doc_benchmark.json"
        out.parent.mkdir(exist_ok=True)
        benchmark.save_results(results, summary, str(out))

        # Per-query detail: how many expected sources were hit?
        print("\n📋 Multi-doc coverage:")
        print(f"{'Query':<80} {'Sources Hit':>12}")
        print("-" * 95)
        for r in results:
            retrieved_files = set(Path(s).name for s in r.retrieved_sources)
            expected_files = set(Path(s).name for s in r.expected_sources)
            hit = len(retrieved_files & expected_files)
            total = len(expected_files)
            marker = "✓" if hit == total else f"{'◐' if hit > 0 else '✗'}"
            print(f"  {marker} {r.query[:76]:<77} {hit}/{total}")

        print(f"\n  Overall: P={summary['avg_precision']:.1%} R={summary['avg_recall']:.1%} "
              f"Content={summary['content_match_rate']:.1%} Latency={summary['avg_latency_ms']:.0f}ms")
