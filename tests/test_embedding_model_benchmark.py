"""Benchmark embedding models: bge-small vs minilm vs nomic.

Each model produces different embeddings, so we re-ingest the corpus
per model and measure retrieval quality on the same queries.
"""
import pytest
import json
import tempfile
import time
from pathlib import Path

from candlekeep.config import Settings, EMBEDDING_MODELS
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor

pytestmark = [pytest.mark.slow]
from candlekeep.rag.router import search_with_routing
from tests.benchmark import RAGBenchmark
from tests.benchmark_queries import BENCHMARK_QUERIES

SAMPLE_DOCS = Path(__file__).parent / "fixtures" / "sample_docs"
MODELS = ["minilm", "bge-small", "nomic"]


class TestEmbeddingModelBenchmark:
    def test_embedding_models(self):
        """Benchmark retrieval quality across embedding models."""
        all_results = {}

        for model_name in MODELS:
            print(f"\n🔄 Testing {model_name} ({EMBEDDING_MODELS[model_name]})...")

            settings = Settings.from_env()
            settings.embedding_model = model_name
            settings.chroma_path = tempfile.mkdtemp()

            # Force fresh embedding manager per model
            from candlekeep.database.embeddings import EmbeddingManager
            EmbeddingManager._instance = None
            EmbeddingManager._model = None
            EmbeddingManager._current_model = None

            store = ChromaVectorStore(settings)
            # Use separate collection per model to avoid dimension mismatch
            store.collection = store.client.get_or_create_collection(
                name=f"bench_{model_name}",
                metadata={"hnsw:space": "cosine"}
            )
            proc = DocumentProcessor(settings)

            t0 = time.time()
            for f in SAMPLE_DOCS.glob("*"):
                if f.is_file():
                    store.add_documents(proc.process(str(f)))
            ingest_time = time.time() - t0

            chunk_count = store.collection.count()

            def make_fn(s):
                def fn(query, n_results):
                    return search_with_routing(s, query, n_results, query_type="simple")
                return fn

            benchmark = RAGBenchmark(make_fn(store), BENCHMARK_QUERIES)
            results = benchmark.run(n_results=5)
            summary = benchmark.summarize(results)

            all_results[model_name] = {
                "model_id": EMBEDDING_MODELS[model_name],
                "chunks": chunk_count,
                "ingest_s": round(ingest_time, 1),
                "precision": summary["avg_precision"],
                "recall": summary["avg_recall"],
                "f1": summary["f1_score"],
                "content": summary["content_match_rate"],
                "latency": summary["avg_latency_ms"],
            }

        # Print comparison
        print(f"\n{'='*85}")
        print("EMBEDDING MODEL BENCHMARK")
        print(f"{'='*85}")
        print(f"{'Model':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Content':>10} {'Latency':>10} {'Ingest':>8}")
        print("-" * 72)
        for m in MODELS:
            r = all_results[m]
            print(f"{m:<12} {r['precision']:>9.1%} {r['recall']:>9.1%} "
                  f"{r['f1']:>9.1%} {r['content']:>9.1%} "
                  f"{r['latency']:>8.0f}ms {r['ingest_s']:>6.1f}s")
        print(f"{'='*85}")

        # Save
        out = Path(__file__).parent / "results" / "embedding_model_benchmark.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(all_results, indent=2))
        print(f"\n💾 Saved to {out}")
