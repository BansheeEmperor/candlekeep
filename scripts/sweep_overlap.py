"""Sweep chunk overlap on the Centurion Set.

Overlap is an ingestion-time parameter, so each value requires a fresh
database with re-chunked documents. Tests overlap values 0, 25, 50, 100
with chunk_size=512 and expansion_chunks=2.

Results saved to tests/results/overlap_sweep_benchmark.json.
"""
import sys
import os

os.environ["CANDLEKEEP_DEVICE"] = "cpu"

import json
import tempfile
import shutil
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.arcane_recall import search_with_arcane_recall
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery


def load_queries():
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


def seed_database(vector_store, processor):
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    doc_count = 0
    chunk_count = 0
    for doc_path in list((fixtures_dir / "sample_docs").glob("*")) + \
                     list((fixtures_dir / "scale_docs").glob("*")):
        if doc_path.is_file():
            chunks = processor.process(str(doc_path))
            vector_store.add_documents(chunks)
            doc_count += 1
            chunk_count += len(chunks)
    return doc_count, chunk_count


def main():
    queries = load_queries()
    print(f"Loaded {len(queries)} queries.\n")

    all_results = {}

    for overlap in [0, 25, 50, 100]:
        print(f"\n{'=' * 60}")
        print(f"OVERLAP = {overlap} (chunk_size=512, expansion=±2)")
        print("=" * 60)

        temp_dir = tempfile.mkdtemp(prefix=f"candlekeep_overlap_{overlap}_")
        try:
            settings = Settings.from_env()
            settings.chroma_path = temp_dir
            settings.chunk_overlap = overlap
            vector_store = ChromaVectorStore(settings)
            processor = DocumentProcessor(settings)

            doc_count, chunk_count = seed_database(vector_store, processor)
            print(f"  Ingested {doc_count} docs, {chunk_count} chunks")

            def search_fn(query, k):
                return search_with_arcane_recall(
                    vector_store, query, n_results=k, expansion_chunks=2
                )

            runner = BenchmarkRunner(search_fn)
            results = runner.run_suite(queries, k=5)
            summary = runner.summarize(results)

            print(f"  MRR:        {summary['mrr']:.4f}")
            print(f"  nDCG@5:     {summary['avg_ndcg_5']:.4f}")
            print(f"  Hit Rate@5: {summary['avg_hit_rate_5']:.4f}")
            print(f"  Latency:    {summary['avg_latency_ms']:.0f}ms")
            print(f"  Avg Tokens: {summary['avg_tokens']:.0f}")

            all_results[f"overlap_{overlap}"] = {
                "chunk_overlap": overlap,
                "chunk_size": 512,
                "expansion_chunks": 2,
                "total_chunks": chunk_count,
                "summary": summary,
            }
        finally:
            shutil.rmtree(temp_dir)

    output_path = (
        Path(__file__).parent.parent / "tests" / "results" / "overlap_sweep_benchmark.json"
    )
    output_path.write_text(json.dumps(all_results, indent=2))
    print(f"\n✅ Results saved to {output_path}")


if __name__ == "__main__":
    main()
