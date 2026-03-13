"""VLM benchmark: ingest visual corpus, run 20 visual queries, assert success criteria.

Requirements:
  - CANDLEKEEP_VLM_PROVIDER=anthropic (or openai)
  - Live ChromaDB on localhost:8000
  - Run: python scripts/generate_visual_corpus.py  (once, to create corpus)

Run: pytest tests/test_vlm_benchmark.py -v -s -m benchmark
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.benchmark]

CORPUS_DIR = Path(__file__).parent / "fixtures" / "visual_corpus"
SUITE_FILE = CORPUS_DIR / "eval_visual_suite.json"


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

def _skip_reason() -> str | None:
    if not os.getenv("CANDLEKEEP_VLM_PROVIDER"):
        return "CANDLEKEEP_VLM_PROVIDER not set"
    if not SUITE_FILE.exists():
        return f"Corpus not found — run: python scripts/generate_visual_corpus.py"
    try:
        import chromadb
        chromadb.HttpClient(host="localhost", port=8000).heartbeat()
    except Exception:
        return "ChromaDB not reachable on localhost:8000"
    return None


skip_reason = _skip_reason()
pytestmark = [pytest.mark.benchmark, pytest.mark.skipif(bool(skip_reason), reason=skip_reason or "")]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def store_and_processor():
    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore
    from candlekeep.rag.processor import DocumentProcessor

    settings = Settings.from_env()
    store = ChromaVectorStore(settings)
    # Use a dedicated benchmark collection to avoid polluting the main DB
    store._collection_name = "vlm_benchmark"
    processor = DocumentProcessor(settings)
    return store, processor


@pytest.fixture(scope="module")
def queries() -> list[dict]:
    return json.loads(SUITE_FILE.read_text())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hit_at_k(results, expected_sources: list[str], k: int = 5) -> bool:
    top_k = [r.metadata.get("source", "") for r in results[:k]]
    for exp in expected_sources:
        for src in top_k:
            # Match regardless of absolute vs relative path
            if src.endswith(exp) or exp.endswith(src) or src == exp:
                return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVLMBenchmark:
    def test_ingest_corpus_with_captioning(self, store_and_processor):
        """Ingest all 15 docs; verify caption chunks are produced."""
        store, processor = store_and_processor
        store.clear()

        total_captioned = 0
        latencies: list[float] = []

        for doc in sorted(CORPUS_DIR.glob("*.md")):
            t0 = time.perf_counter()
            result = processor.process(doc)
            elapsed = time.perf_counter() - t0

            if result.images_captioned:
                latencies.append(elapsed / result.images_captioned)

            store.add_documents(result.chunks, collection="vlm_benchmark")
            total_captioned += result.images_captioned

            print(
                f"  {doc.name}: {len(result.chunks)} chunks, "
                f"{result.images_captioned} captioned, {result.images_from_cache} cached"
            )

        print(f"\nTotal images captioned: {total_captioned}")
        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            print(f"Avg caption latency: {avg_lat:.1f}s/image")
            assert avg_lat <= 8.0, f"Caption latency {avg_lat:.1f}s exceeds 8s limit"

        assert total_captioned > 0, "No images were captioned — check VLM provider config"

    def test_visual_query_hit_rate(self, store_and_processor, queries):
        """Run 20 visual queries; assert HR@5 >= 0.60."""
        store, _ = store_and_processor

        from candlekeep.rag.router import search_with_routing

        hits = 0
        print("\n--- Visual Query Results ---")
        for q in queries:
            results = search_with_routing(store, q["query"], n_results=5, query_type="hybrid")
            hit = _hit_at_k(results, q["expected_sources"], k=5)
            hits += int(hit)
            status = "✓" if hit else "✗"
            print(f"  {status} [{q['id']}] {q['query'][:70]}")

        hr5 = hits / len(queries)
        print(f"\nHit Rate@5: {hr5:.2f} ({hits}/{len(queries)})")
        assert hr5 >= 0.60, f"HR@5 {hr5:.2f} below 0.60 threshold"

    def test_cache_hit_rate_on_reingest(self, store_and_processor):
        """Re-ingest corpus; assert 100% cache hit rate (zero new API calls)."""
        store, processor = store_and_processor
        store.clear()

        total_captioned = 0
        total_from_cache = 0

        for doc in sorted(CORPUS_DIR.glob("*.md")):
            result = processor.process(doc)
            store.add_documents(result.chunks, collection="vlm_benchmark")
            total_captioned += result.images_captioned
            total_from_cache += result.images_from_cache

        total = total_captioned + total_from_cache
        cache_rate = total_from_cache / total if total else 0
        print(f"\nRe-ingest: {total_from_cache}/{total} from cache ({cache_rate:.0%})")
        assert total_captioned == 0, (
            f"Expected 0 new API calls on re-ingest, got {total_captioned}"
        )
        assert cache_rate == 1.0, f"Cache hit rate {cache_rate:.0%} < 100%"
