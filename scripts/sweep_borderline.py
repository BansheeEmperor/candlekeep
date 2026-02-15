"""Sweep similarity threshold against borderline-quality documents.

Tests three corpus configurations:
  1. Clean-only: sample_docs + scale_docs (Centurion baseline)
  2. Borderline-only: borderline_docs
  3. Mixed: all three directories together

For each configuration, sweeps similarity threshold 0.85-0.95 and
records MRR, nDCG@5, Hit Rate@5, latency, and token volume.

The key signal: does the mixed corpus degrade results for queries
targeting clean docs?
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
from candlekeep.rag.arcane_recall import search_with_arcane_recall
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery


FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"

# Queries targeting clean docs (should not degrade in mixed corpus)
CLEAN_QUERIES = [
    EvalQuery("cache eviction policies", ["tests/fixtures/sample_docs/caching.md"], "semantic", "medium"),
    EvalQuery("JWT token security", ["tests/fixtures/sample_docs/authentication.md"], "semantic", "medium"),
    EvalQuery("REST API versioning", ["tests/fixtures/sample_docs/api-design.md"], "semantic", "medium"),
    EvalQuery("database normalization forms", ["tests/fixtures/sample_docs/database-design.md"], "semantic", "medium"),
    EvalQuery("microservices communication", ["tests/fixtures/sample_docs/microservices.md"], "semantic", "medium"),
]

# Queries targeting borderline docs
BORDERLINE_QUERIES = [
    EvalQuery("cache TTL settings", ["tests/fixtures/borderline_docs/sparse-caching.md"], "semantic", "easy"),
    EvalQuery("token storage mistakes", ["tests/fixtures/borderline_docs/sparse-auth.md"], "semantic", "medium"),
    EvalQuery("API rate limiting", ["tests/fixtures/borderline_docs/sparse-api.md"], "semantic", "medium"),
    EvalQuery("database connection pooling tips", ["tests/fixtures/borderline_docs/sparse-database.md"], "semantic", "medium"),
    EvalQuery("POST endpoint reference", ["tests/fixtures/borderline_docs/repetitive-endpoints.md"], "semantic", "easy"),
    EvalQuery("environment variable configuration", ["tests/fixtures/borderline_docs/repetitive-config.md"], "semantic", "easy"),
    EvalQuery("HTTP 429 rate limit error", ["tests/fixtures/borderline_docs/repetitive-errors.md"], "lexical", "medium"),
    EvalQuery("golden signals monitoring", ["tests/fixtures/borderline_docs/mixed-monitoring.md"], "semantic", "medium"),
    EvalQuery("unit test naming conventions", ["tests/fixtures/borderline_docs/mixed-testing.md"], "semantic", "medium"),
    EvalQuery("blue-green deployment rollback", ["tests/fixtures/borderline_docs/mixed-deployment.md"], "semantic", "medium"),
]


def make_threshold_should_expand(threshold):
    """Create a patched should_expand with a custom similarity threshold."""
    import numpy as np

    def calculate_cosine_similarity(vec1, vec2):
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def patched(match_chunk, neighbor_chunk, query_embedding, match_embedding, neighbor_embedding):
        text = neighbor_chunk.text.strip()
        if text.startswith(("- ", "* ", "+ ", "> ", "  ")):
            return True
        if query_embedding is not None and match_embedding is not None and neighbor_embedding is not None:
            match_sim = calculate_cosine_similarity(query_embedding, match_embedding)
            neighbor_sim = calculate_cosine_similarity(query_embedding, neighbor_embedding)
            return neighbor_sim >= (match_sim * threshold)
        return True

    return patched


def build_corpus(settings, processor, doc_dirs):
    """Seed a fresh database with docs from the given directories."""
    temp_dir = tempfile.mkdtemp(prefix="candlekeep_borderline_")
    settings.chroma_path = temp_dir
    vector_store = ChromaVectorStore(settings)

    chunk_count = 0
    doc_count = 0
    for d in doc_dirs:
        for doc_path in sorted(d.glob("*")):
            if doc_path.is_file():
                chunks = processor.process(str(doc_path))
                vector_store.add_documents(chunks)
                doc_count += 1
                chunk_count += len(chunks)

    return vector_store, temp_dir, doc_count, chunk_count


def run_sweep(label, vector_store, queries, thresholds):
    """Run threshold sweep and return results dict."""
    print(f"\n{'=' * 60}")
    print(f"CORPUS: {label} ({len(queries)} queries)")
    print("=" * 60)

    results = {}
    for threshold in thresholds:
        patched_fn = make_threshold_should_expand(threshold)

        def make_search_fn(pfn):
            def search_fn(query, k):
                with patch("candlekeep.rag.arcane_recall.should_expand", pfn):
                    return search_with_arcane_recall(vector_store, query, n_results=k, expansion_chunks=2)
            return search_fn

        runner = BenchmarkRunner(make_search_fn(patched_fn))
        eval_results = runner.run_suite(queries, k=5)
        summary = runner.summarize(eval_results)

        print(f"  threshold={threshold}: MRR={summary['mrr']:.4f}  nDCG@5={summary['avg_ndcg_5']:.4f}  "
              f"HR@5={summary['avg_hit_rate_5']:.4f}  Tokens={summary['avg_tokens']:.0f}  "
              f"Latency={summary['avg_latency_ms']:.0f}ms")

        results[f"threshold_{threshold}"] = {
            "similarity_threshold": threshold,
            "summary": summary,
        }

    return results


def main():
    thresholds = [0.85, 0.88, 0.90, 0.92, 0.95]
    settings = Settings.from_env()
    processor = DocumentProcessor(settings)

    all_results = {}

    # --- Config 1: Clean-only ---
    clean_dirs = [FIXTURES / "sample_docs", FIXTURES / "scale_docs"]
    vs, tmp, docs, chunks = build_corpus(Settings.from_env(), processor, clean_dirs)
    print(f"Clean corpus: {docs} docs, {chunks} chunks")
    all_results["clean_only"] = {
        "docs": docs, "chunks": chunks,
        "query_set": "clean",
        "sweeps": run_sweep("Clean-only (clean queries)", vs, CLEAN_QUERIES, thresholds),
    }
    shutil.rmtree(tmp)

    # --- Config 2: Borderline-only ---
    border_dirs = [FIXTURES / "borderline_docs"]
    vs, tmp, docs, chunks = build_corpus(Settings.from_env(), processor, border_dirs)
    print(f"\nBorderline corpus: {docs} docs, {chunks} chunks")
    all_results["borderline_only"] = {
        "docs": docs, "chunks": chunks,
        "query_set": "borderline",
        "sweeps": run_sweep("Borderline-only (borderline queries)", vs, BORDERLINE_QUERIES, thresholds),
    }
    shutil.rmtree(tmp)

    # --- Config 3: Mixed ---
    mixed_dirs = [FIXTURES / "sample_docs", FIXTURES / "scale_docs", FIXTURES / "borderline_docs"]
    vs, tmp, docs, chunks = build_corpus(Settings.from_env(), processor, mixed_dirs)
    print(f"\nMixed corpus: {docs} docs, {chunks} chunks")
    all_results["mixed_clean_queries"] = {
        "docs": docs, "chunks": chunks,
        "query_set": "clean",
        "sweeps": run_sweep("Mixed corpus (clean queries)", vs, CLEAN_QUERIES, thresholds),
    }
    all_results["mixed_borderline_queries"] = {
        "docs": docs, "chunks": chunks,
        "query_set": "borderline",
        "sweeps": run_sweep("Mixed corpus (borderline queries)", vs, BORDERLINE_QUERIES, thresholds),
    }
    shutil.rmtree(tmp)

    # --- Summary comparison ---
    print("\n" + "=" * 60)
    print("DEGRADATION CHECK (threshold=0.92)")
    print("=" * 60)
    clean_mrr = all_results["clean_only"]["sweeps"]["threshold_0.92"]["summary"]["mrr"]
    mixed_mrr = all_results["mixed_clean_queries"]["sweeps"]["threshold_0.92"]["summary"]["mrr"]
    delta = mixed_mrr - clean_mrr
    pct = (delta / clean_mrr * 100) if clean_mrr > 0 else 0
    print(f"  Clean-only MRR:  {clean_mrr:.4f}")
    print(f"  Mixed MRR:       {mixed_mrr:.4f}")
    print(f"  Delta:           {delta:+.4f} ({pct:+.1f}%)")
    if abs(pct) > 2:
        print("  ⚠️  Degradation exceeds 2% threshold")
    else:
        print("  ✅ Within acceptable range")

    border_tokens = all_results["borderline_only"]["sweeps"]["threshold_0.92"]["summary"]["avg_tokens"]
    clean_tokens = all_results["clean_only"]["sweeps"]["threshold_0.92"]["summary"]["avg_tokens"]
    token_ratio = border_tokens / clean_tokens if clean_tokens > 0 else 0
    print(f"\n  Clean avg tokens:      {clean_tokens:.0f}")
    print(f"  Borderline avg tokens: {border_tokens:.0f}")
    print(f"  Ratio:                 {token_ratio:.2f}x")
    if token_ratio > 1.5:
        print("  ⚠️  Borderline token volume >50% higher — possible over-expansion")
    else:
        print("  ✅ Token volume within acceptable range")

    output_path = Path(__file__).parent.parent / "tests" / "results" / "borderline_sweep_benchmark.json"
    output_path.write_text(json.dumps(all_results, indent=2))
    print(f"\n✅ Results saved to {output_path}")


if __name__ == "__main__":
    main()
