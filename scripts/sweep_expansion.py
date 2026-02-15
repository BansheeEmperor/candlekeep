"""Sweep expansion_chunks and similarity threshold on the Centurion Set.

Runs two independent sweeps against the full 108-query evaluation suite:
  1. expansion_chunks: ±1, ±2, ±3 (with default threshold 0.92)
  2. similarity_threshold: 0.85, 0.88, 0.90, 0.92, 0.95 (with default ±2)

Results are saved to tests/results/ for diary entry.
"""
import sys
import os

os.environ["CANDLEKEEP_DEVICE"] = "cpu"

import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from candlekeep.rag.arcane_recall import search_with_arcane_recall, should_expand
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery


def setup_database():
    """Create and seed a temporary database. Returns (vector_store, temp_dir)."""
    temp_dir = tempfile.mkdtemp(prefix="candlekeep_sweep_")
    settings = Settings.from_env()
    settings.chroma_path = temp_dir
    vector_store = ChromaVectorStore(settings)
    processor = DocumentProcessor(settings)

    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    for doc_path in list((fixtures_dir / "sample_docs").glob("*")) + \
                     list((fixtures_dir / "scale_docs").glob("*")):
        if doc_path.is_file():
            chunks = processor.process(str(doc_path))
            vector_store.add_documents(chunks)

    return vector_store, temp_dir


def load_queries():
    """Load the Centurion evaluation suite."""
    suite_path = Path(__file__).parent.parent / "tests" / "fixtures" / "eval_suite_100.json"
    with open(suite_path) as f:
        suite_data = json.load(f)
    return [
        EvalQuery(
            query=q["query"],
            expected_sources=q["expected_sources"],
            category=q["category"],
            difficulty=q["difficulty"],
        )
        for q in suite_data["queries"]
    ]


def run_expansion_chunks_sweep(vector_store, queries):
    """Sweep expansion_chunks ±1, ±2, ±3 with default threshold."""
    print("\n" + "=" * 60)
    print("SWEEP 1: expansion_chunks (similarity threshold fixed at 0.92)")
    print("=" * 60)

    all_results = {}
    for chunks in [1, 2, 3]:
        print(f"\n--- expansion_chunks = ±{chunks} ---")

        def make_search_fn(ec):
            def search_fn(query, k):
                return search_with_arcane_recall(vector_store, query, n_results=k, expansion_chunks=ec)
            return search_fn

        runner = BenchmarkRunner(make_search_fn(chunks))
        results = runner.run_suite(queries, k=5)
        summary = runner.summarize(results)

        print(f"  MRR:        {summary['mrr']:.4f}")
        print(f"  nDCG@5:     {summary['avg_ndcg_5']:.4f}")
        print(f"  Hit Rate@5: {summary['avg_hit_rate_5']:.4f}")
        print(f"  Latency:    {summary['avg_latency_ms']:.0f}ms")
        print(f"  Avg Tokens: {summary['avg_tokens']:.0f}")

        all_results[f"expansion_{chunks}"] = {
            "expansion_chunks": chunks,
            "similarity_threshold": 0.92,
            "summary": summary,
        }

    return all_results


def make_threshold_should_expand(threshold):
    """Create a patched should_expand with a custom similarity threshold."""
    import numpy as np

    def calculate_cosine_similarity(vec1, vec2):
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def patched_should_expand(match_chunk, neighbor_chunk, query_embedding,
                              match_embedding, neighbor_embedding):
        text = neighbor_chunk.text.strip()
        continuation_prefixes = ("- ", "* ", "+ ", "> ", "  ")
        if text.startswith(continuation_prefixes):
            return True

        if query_embedding is not None and match_embedding is not None and neighbor_embedding is not None:
            match_sim = calculate_cosine_similarity(query_embedding, match_embedding)
            neighbor_sim = calculate_cosine_similarity(query_embedding, neighbor_embedding)
            if neighbor_sim >= (match_sim * threshold):
                return True
            return False

        return True

    return patched_should_expand


def run_threshold_sweep(vector_store, queries):
    """Sweep similarity threshold with default ±2 expansion."""
    print("\n" + "=" * 60)
    print("SWEEP 2: similarity_threshold (expansion_chunks fixed at ±2)")
    print("=" * 60)

    all_results = {}
    for threshold in [0.85, 0.88, 0.90, 0.92, 0.95]:
        print(f"\n--- similarity_threshold = {threshold} ---")

        patched_fn = make_threshold_should_expand(threshold)

        def make_search_fn(pfn):
            def search_fn(query, k):
                with patch("candlekeep.rag.arcane_recall.should_expand", pfn):
                    return search_with_arcane_recall(vector_store, query, n_results=k, expansion_chunks=2)
            return search_fn

        runner = BenchmarkRunner(make_search_fn(patched_fn))
        results = runner.run_suite(queries, k=5)
        summary = runner.summarize(results)

        print(f"  MRR:        {summary['mrr']:.4f}")
        print(f"  nDCG@5:     {summary['avg_ndcg_5']:.4f}")
        print(f"  Hit Rate@5: {summary['avg_hit_rate_5']:.4f}")
        print(f"  Latency:    {summary['avg_latency_ms']:.0f}ms")
        print(f"  Avg Tokens: {summary['avg_tokens']:.0f}")

        all_results[f"threshold_{threshold}"] = {
            "expansion_chunks": 2,
            "similarity_threshold": threshold,
            "summary": summary,
        }

    return all_results


def main():
    print("Setting up database...")
    vector_store, temp_dir = setup_database()
    queries = load_queries()
    print(f"Loaded {len(queries)} queries.")

    try:
        chunk_results = run_expansion_chunks_sweep(vector_store, queries)
        threshold_results = run_threshold_sweep(vector_store, queries)

        combined = {
            "expansion_chunks_sweep": chunk_results,
            "similarity_threshold_sweep": threshold_results,
        }

        output_path = Path(__file__).parent.parent / "tests" / "results" / "expansion_sweep_benchmark.json"
        output_path.write_text(json.dumps(combined, indent=2))
        print(f"\n✅ Results saved to {output_path}")
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
