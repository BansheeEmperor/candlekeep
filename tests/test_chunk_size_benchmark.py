"""Benchmark different chunk sizes to find optimal setting.

Current default: 512 chars, 50 overlap.
Arcane Recall expands ±2 chunks, so smaller chunks get compensated with context.
The question: does chunk size affect retrieval quality or just expansion behavior?
"""
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

CHUNK_SIZES = [256, 512, 768, 1024]
OVERLAP = 50


class TestChunkSizeBenchmark:
    def test_chunk_sizes(self):
        """Benchmark retrieval quality across chunk sizes."""
        all_results = {}

        for size in CHUNK_SIZES:
            settings = Settings.from_env()
            settings.chunk_size = size
            settings.chunk_overlap = OVERLAP
            settings.chroma_path = tempfile.mkdtemp()

            store = ChromaVectorStore(settings)
            proc = DocumentProcessor(settings)

            for f in SAMPLE_DOCS.glob("*"):
                if f.is_file():
                    store.add_documents(proc.process(str(f)).chunks)

            chunk_count = store.collection.count()

            def make_fn(s):
                def fn(query, n_results):
                    return search_with_routing(s, query, n_results, query_type="simple")
                return fn

            benchmark = RAGBenchmark(make_fn(store), BENCHMARK_QUERIES)
            results = benchmark.run(n_results=5)
            summary = benchmark.summarize(results)

            all_results[size] = {
                "chunks": chunk_count,
                "precision": summary["avg_precision"],
                "recall": summary["avg_recall"],
                "f1": summary["f1_score"],
                "content": summary["content_match_rate"],
                "latency": summary["avg_latency_ms"],
            }

        # Print comparison
        print(f"\n{'='*80}")
        print("CHUNK SIZE BENCHMARK (with Arcane Recall ±2 expansion)")
        print(f"{'='*80}")
        print(f"{'Size':>6} {'Chunks':>8} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Content':>10} {'Latency':>10}")
        print("-" * 64)
        for size in CHUNK_SIZES:
            r = all_results[size]
            print(f"{size:>6} {r['chunks']:>8} {r['precision']:>9.1%} {r['recall']:>9.1%} "
                  f"{r['f1']:>9.1%} {r['content']:>9.1%} {r['latency']:>8.0f}ms")
        print(f"{'='*80}")

        # Save
        out = Path(__file__).parent / "results" / "chunk_size_benchmark.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(
            {str(k): v for k, v in all_results.items()}, indent=2
        ))
        print(f"\n💾 Saved to {out}")
