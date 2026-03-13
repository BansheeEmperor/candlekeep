"""Benchmark for BM25 token normalisation — surface-variant supplement.

Measures MRR and Hit Rate@5 on 30 queries that use alternate surface forms
of technical terms present in the Centurion Set lexical category.

Each query is a rewrite of an existing lexical query using 2–3 alternate
surface forms of the key technical term (e.g. 'bge small en' instead of
'bge-small-en-v1.5'). The expected sources are identical to the originals.

Usage:
    python scripts/benchmark_normalisation.py [--query-type hybrid]

Success criteria (from spec):
    - ≥10% MRR improvement on surface-variant queries vs baseline
    - Zero regression on the main Centurion Set
    - Map generation time ≤ 5s on the current corpus
"""
import sys
import os
import json
import time
import argparse
import tempfile
import shutil
from pathlib import Path

os.environ["CANDLEKEEP_DEVICE"] = "cpu"

sys.path.append(str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery

# ---------------------------------------------------------------------------
# Surface-variant supplement: 30 queries derived from Centurion Set lexical
# queries by substituting alternate surface forms of the key technical term.
# Each entry has:
#   query        — the rewritten query using an alternate surface form
#   original     — the original Centurion Set query (for reference)
#   variants     — the surface forms used in the rewrite
#   expected_sources — same as the original Centurion Set query
# ---------------------------------------------------------------------------

SURFACE_VARIANT_QUERIES = [
    # BGE-small-en-v1.5 variants
    EvalQuery(
        query="bge small en model",
        expected_sources=["docs/ARCHITECTURE.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="BGE Small English embedding model",
        expected_sources=["docs/ARCHITECTURE.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="bge-small embedding v1",
        expected_sources=["docs/ARCHITECTURE.md"],
        category="surface_variant",
        difficulty="medium",
    ),

    # ChromaDB variants
    EvalQuery(
        query="chroma db vector store",
        expected_sources=["docs/DESIGN.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="Chroma DB v0.4",
        expected_sources=["docs/DESIGN.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="chromadb version 0.4",
        expected_sources=["docs/DESIGN.md"],
        category="surface_variant",
        difficulty="medium",
    ),

    # MS-MARCO MiniLM variants
    EvalQuery(
        query="ms marco minilm reranker",
        expected_sources=["docs/RESEARCH_DIARY.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="MiniLM L6 v2 cross encoder",
        expected_sources=["docs/RESEARCH_DIARY.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="msmarco minilm-l6 model",
        expected_sources=["docs/RESEARCH_DIARY.md"],
        category="surface_variant",
        difficulty="hard",
    ),

    # Apache Kafka variants
    EvalQuery(
        query="apache kafka features",
        expected_sources=["tests/fixtures/scale_docs/apache-kafka.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="kafka 3 release notes",
        expected_sources=["tests/fixtures/scale_docs/apache-kafka.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="Kafka v3.0 changelog",
        expected_sources=["tests/fixtures/scale_docs/apache-kafka.md"],
        category="surface_variant",
        difficulty="medium",
    ),

    # PostgreSQL variants
    EvalQuery(
        query="postgres 15 internals",
        expected_sources=["tests/fixtures/scale_docs/postgresql-internals.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="postgresql internals version 15",
        expected_sources=["tests/fixtures/scale_docs/postgresql-internals.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="Postgres v15 storage engine",
        expected_sources=["tests/fixtures/scale_docs/postgresql-internals.md"],
        category="surface_variant",
        difficulty="hard",
    ),

    # Kubernetes / dockershim variants
    EvalQuery(
        query="kubernetes dockershim removal",
        expected_sources=["tests/fixtures/scale_docs/kubernetes-architecture.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="k8s v1.24 docker shim deprecation",
        expected_sources=["tests/fixtures/scale_docs/kubernetes-architecture.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="kube 1.24 container runtime changes",
        expected_sources=["tests/fixtures/scale_docs/kubernetes-architecture.md"],
        category="surface_variant",
        difficulty="hard",
    ),

    # TLS variants
    EvalQuery(
        query="tls 1.3 handshake",
        expected_sources=["tests/fixtures/scale_docs/tls-ssl.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="TLSv1.3 connection setup",
        expected_sources=["tests/fixtures/scale_docs/tls-ssl.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="transport layer security version 1.3",
        expected_sources=["tests/fixtures/scale_docs/tls-ssl.md"],
        category="surface_variant",
        difficulty="hard",
    ),

    # gRPC variants
    EvalQuery(
        query="grpc http2 protocol",
        expected_sources=["tests/fixtures/scale_docs/grpc-protocol.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="g-rpc over http 2",
        expected_sources=["tests/fixtures/scale_docs/grpc-protocol.md"],
        category="surface_variant",
        difficulty="medium",
    ),
    EvalQuery(
        query="GRPC remote procedure call",
        expected_sources=["tests/fixtures/scale_docs/grpc-protocol.md"],
        category="surface_variant",
        difficulty="medium",
    ),

    # Redis AOF variants
    EvalQuery(
        query="redis 7 aof persistence",
        expected_sources=["tests/fixtures/scale_docs/redis-data-structures.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="Redis v7.0 append only file",
        expected_sources=["tests/fixtures/scale_docs/redis-data-structures.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="redis multi part aof format",
        expected_sources=["tests/fixtures/scale_docs/redis-data-structures.md"],
        category="surface_variant",
        difficulty="hard",
    ),

    # JWT RS256 variants
    EvalQuery(
        query="jwt rsa256 signing algorithm",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="JSON web token RS 256",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        category="surface_variant",
        difficulty="hard",
    ),
    EvalQuery(
        query="jwt asymmetric signing rs256",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        category="surface_variant",
        difficulty="hard",
    ),

    # Docker Compose variants
    EvalQuery(
        query="docker compose v2 cli",
        expected_sources=["tests/fixtures/scale_docs/container-fundamentals.md"],
        category="surface_variant",
        difficulty="easy",
    ),
    EvalQuery(
        query="docker-compose version 2",
        expected_sources=["tests/fixtures/scale_docs/container-fundamentals.md"],
        category="surface_variant",
        difficulty="easy",
    ),
]

assert len(SURFACE_VARIANT_QUERIES) == 30, f"Expected 30 queries, got {len(SURFACE_VARIANT_QUERIES)}"


def _seed_database(vector_store: ChromaVectorStore, processor: DocumentProcessor) -> int:
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    doc_count = 0
    for subdir in ["sample_docs", "scale_docs"]:
        docs_dir = fixtures_dir / subdir
        if not docs_dir.exists():
            continue
        for doc_path in docs_dir.glob("*"):
            if doc_path.is_file():
                try:
                    result = processor.process(str(doc_path))
                    if result.chunks:
                        vector_store.add_documents(result.chunks)
                        doc_count += 1
                except Exception:
                    pass

    # Also ingest docs/ (ARCHITECTURE.md, DESIGN.md, RESEARCH_DIARY.md)
    docs_dir = Path(__file__).parent.parent / "docs"
    for doc_path in docs_dir.glob("*.md"):
        try:
            result = processor.process(str(doc_path))
            if result.chunks:
                vector_store.add_documents(result.chunks)
                doc_count += 1
        except Exception:
            pass

    return doc_count


def _load_centurion_queries() -> list[EvalQuery]:
    suite_path = Path(__file__).parent.parent / "tests" / "fixtures" / "eval_suite_100.json"
    if not suite_path.exists():
        return []
    with open(suite_path) as f:
        data = json.load(f)
    return [
        EvalQuery(
            query=q["query"],
            expected_sources=q["expected_sources"],
            category=q["category"],
            difficulty=q["difficulty"],
        )
        for q in data["queries"]
    ]


def run_benchmark(query_type: str = "hybrid"):
    print(f"\n🔬 BM25 Normalisation Benchmark  (query_type={query_type})")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="candlekeep_norm_bench_")
    try:
        settings = Settings.from_env()
        settings.data_dir = Path(temp_dir)
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        (settings.data_dir / "chroma").mkdir(exist_ok=True)

        vector_store = ChromaVectorStore(settings)
        processor = DocumentProcessor(settings)

        print("📦 Seeding database...")
        doc_count = _seed_database(vector_store, processor)
        print(f"   Ingested {doc_count} documents")

        # ── Measure map generation time ──────────────────────────────────
        print("\n⏱  Generating normalisation map...")
        from candlekeep.rag.token_normalisation import (
            regenerate_normalisation_map,
            clear_normalisation_cache,
        )
        clear_normalisation_cache()
        t0 = time.monotonic()
        norm_map = regenerate_normalisation_map(vector_store)
        map_gen_time = time.monotonic() - t0
        map_size = norm_map.size if norm_map else 0
        print(f"   Map size: {map_size} variants  |  Generation time: {map_gen_time:.2f}s")

        if map_gen_time > 5.0:
            print(f"   ⚠  FAIL: map generation exceeded 5s target ({map_gen_time:.2f}s)")
        else:
            print(f"   ✓  Map generation within 5s target")

        def search_fn(query: str, k: int):
            return search_with_routing(vector_store, query, n_results=k, query_type=query_type)

        runner = BenchmarkRunner(search_fn)

        # ── Surface-variant supplement ───────────────────────────────────
        print("\n📊 Running surface-variant supplement (30 queries)...")
        sv_results = runner.run_suite(SURFACE_VARIANT_QUERIES, k=5)
        sv_summary = runner.summarize(sv_results)

        print(f"   MRR:        {sv_summary['mrr']:.4f}")
        print(f"   Hit Rate@5: {sv_summary['avg_hit_rate_5']:.4f}")

        # ── Baseline without normalisation ───────────────────────────────
        print("\n📊 Running surface-variant supplement WITHOUT normalisation...")
        clear_normalisation_cache()
        # Temporarily remove the map file so _tokenize skips normalisation
        map_path = settings.normalisation_map_path
        map_backup = map_path.with_suffix(".json.bak")
        if map_path.exists():
            map_path.rename(map_backup)

        # Rebuild BM25 cache without normalisation
        from candlekeep.rag.hybrid import clear_bm25_cache
        clear_bm25_cache()

        sv_baseline_results = runner.run_suite(SURFACE_VARIANT_QUERIES, k=5)
        sv_baseline_summary = runner.summarize(sv_baseline_results)

        print(f"   MRR:        {sv_baseline_summary['mrr']:.4f}")
        print(f"   Hit Rate@5: {sv_baseline_summary['avg_hit_rate_5']:.4f}")

        # Restore map
        if map_backup.exists():
            map_backup.rename(map_path)
        clear_normalisation_cache()
        clear_bm25_cache()

        # ── MRR improvement check ────────────────────────────────────────
        baseline_mrr = sv_baseline_summary["mrr"]
        norm_mrr = sv_summary["mrr"]
        if baseline_mrr > 0:
            mrr_improvement = (norm_mrr - baseline_mrr) / baseline_mrr
        else:
            mrr_improvement = float("inf") if norm_mrr > 0 else 0.0

        print(f"\n📈 MRR improvement: {mrr_improvement:+.1%}  "
              f"(baseline={baseline_mrr:.4f}, normalised={norm_mrr:.4f})")

        if mrr_improvement >= 0.10:
            print("   ✓  PASS: ≥10% MRR improvement on surface-variant supplement")
        else:
            print(f"   ✗  FAIL: <10% MRR improvement (got {mrr_improvement:.1%})")

        # ── Centurion Set regression check ───────────────────────────────
        centurion_queries = _load_centurion_queries()
        if centurion_queries:
            print(f"\n📊 Running Centurion Set regression check ({len(centurion_queries)} queries)...")
            centurion_results = runner.run_suite(centurion_queries, k=5)
            centurion_summary = runner.summarize(centurion_results)
            print(f"   MRR:        {centurion_summary['mrr']:.4f}")
            print(f"   Hit Rate@5: {centurion_summary['avg_hit_rate_5']:.4f}")
            print("   (Compare against your baseline to confirm no regression)")
        else:
            print("\n⚠  Centurion Set not found at tests/fixtures/eval_suite_100.json — skipping regression check")

        # ── Save results ─────────────────────────────────────────────────
        output_dir = Path(__file__).parent.parent / "tests" / "results"
        output_dir.mkdir(exist_ok=True)
        report = {
            "map_generation_time_s": round(map_gen_time, 3),
            "map_size": map_size,
            "surface_variant": {
                "with_normalisation": {
                    "mrr": sv_summary["mrr"],
                    "hit_rate_5": sv_summary["avg_hit_rate_5"],
                },
                "without_normalisation": {
                    "mrr": sv_baseline_summary["mrr"],
                    "hit_rate_5": sv_baseline_summary["avg_hit_rate_5"],
                },
                "mrr_improvement": round(mrr_improvement, 4),
            },
        }
        if centurion_queries:
            report["centurion_regression"] = {
                "mrr": centurion_summary["mrr"],
                "hit_rate_5": centurion_summary["avg_hit_rate_5"],
            }

        report_path = output_dir / "normalisation_benchmark.json"
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\n💾 Results saved to {report_path}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BM25 normalisation benchmark")
    parser.add_argument("--query-type", default="hybrid",
                        choices=["simple", "hybrid", "precise"],
                        help="Search path to benchmark (default: hybrid)")
    args = parser.parse_args()
    run_benchmark(args.query_type)
