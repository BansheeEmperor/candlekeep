"""Scale benchmark: test router performance with large corpus."""
import pytest
import json
import time
from pathlib import Path

from candlekeep.rag.router import search_with_routing
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.config import Settings

pytestmark = [pytest.mark.slow]

SCALE_DOCS = Path(__file__).parent / "fixtures" / "scale_docs"

# Queries spanning the scale corpus domains
SCALE_QUERIES = [
    # Simple lookups
    "What is TCP three-way handshake?",
    "Linux file permissions chmod",
    "Redis sorted sets",
    "Helm chart values",
    # Cross-domain
    "How does TLS work with load balancers?",
    "Database connection pooling in Kubernetes",
    "Monitoring serverless functions",
    # Abstract
    "distributed systems consistency tradeoffs",
    "security best practices for cloud infrastructure",
    # Adversarial
    "quantum computing blockchain AI synergy",
    # Long
    "How do I set up a CI/CD pipeline that deploys a containerized application to Kubernetes with blue-green deployment strategy and automated rollback on failure?",
]


@pytest.fixture(scope="module")
def scale_store():
    """Seed a store with the scale corpus."""
    import tempfile

    settings = Settings.from_env()
    settings.chroma_path = tempfile.mkdtemp()

    from candlekeep.database.vector_store import ChromaVectorStore

    store = ChromaVectorStore(settings)
    proc = DocumentProcessor(settings)

    if not SCALE_DOCS.exists():
        pytest.skip("Scale corpus not generated. Run scripts/generate_scale_corpus.py")

    t0 = time.time()
    total_chunks = 0
    for f in sorted(SCALE_DOCS.glob("*.md")):
        chunks = proc.process(str(f))
        store.add_documents(chunks)
        total_chunks += len(chunks)
    ingest_time = time.time() - t0

    print(f"\n📦 Ingested {total_chunks} chunks from {len(list(SCALE_DOCS.glob('*.md')))} docs in {ingest_time:.1f}s")
    return store, total_chunks


class TestScaleBenchmark:
    def test_scale_simple(self, scale_store):
        """Benchmark simple path at scale."""
        store, chunk_count = scale_store
        print(f"\n{'='*70}")
        print(f"SCALE BENCHMARK — {chunk_count} chunks")
        print(f"{'='*70}")

        for qt in ["simple", "precise"]:
            times = []
            result_counts = []
            for q in SCALE_QUERIES:
                t0 = time.time()
                results = search_with_routing(store, q, n_results=5, query_type=qt)
                elapsed = (time.time() - t0) * 1000
                times.append(elapsed)
                result_counts.append(len(results))

            avg = sum(times) / len(times)
            p50 = sorted(times)[len(times) // 2]
            p99 = sorted(times)[-1]
            filtered = sum(1 for c in result_counts if c == 0)

            print(f"\n[{qt}] avg={avg:.0f}ms  p50={p50:.0f}ms  p99={p99:.0f}ms  filtered={filtered}/{len(SCALE_QUERIES)}")
            for q, t, c in zip(SCALE_QUERIES, times, result_counts):
                print(f"  {t:6.0f}ms  {c} results  {q[:65]}")

        # Save results
        out = Path(__file__).parent / "results" / "scale_benchmark.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"chunk_count": chunk_count, "queries": len(SCALE_QUERIES)}, indent=2))
        print(f"\n💾 Saved to {out}")
