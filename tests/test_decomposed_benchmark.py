"""Benchmark simulating agent decomposition of multi-document queries.

WHY THIS EXISTS:
The search tool handles one focused query at a time. Multi-document questions
like "How does TLS work with load balancers?" need TWO searches — one for TLS,
one for load balancing. That decomposition is the agent's job.

test_multi_doc_benchmark.py showed 54.7% content with single searches.
This test simulates what actually happens in production: the agent breaks
the question apart, searches each piece, and combines the results.

The difference between these two benchmarks measures the value of agent
decomposition — how much coverage improves when queries are properly split.
"""
import json
from pathlib import Path

import pytest

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from tests.decomposed_queries import DECOMPOSED_QUERIES

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
        store.add_documents(proc.process(str(f)))

    print(f"\n📦 {store.collection.count()} chunks ingested")
    return store


class TestDecomposedBenchmark:
    def test_decomposed_vs_single(self, scale_store):
        """Compare single-search vs agent-decomposed multi-doc queries."""
        print(f"\n{'='*90}")
        print("AGENT DECOMPOSITION BENCHMARK")
        print("Simulates agent splitting complex queries into focused sub-searches")
        print(f"{'='*90}")

        single_content_total = 0
        decomposed_content_total = 0
        expected_content_total = 0
        single_sources_hit = 0
        decomposed_sources_hit = 0
        total_expected_sources = 0

        for dq in DECOMPOSED_QUERIES:
            expected_files = set(Path(s).name for s in dq.expected_sources)
            total_expected_sources += len(expected_files)

            # --- Single search (baseline) ---
            single_results = search_with_routing(
                scale_store, dq.original, n_results=5, query_type="simple"
            )
            single_text = " ".join(r.text for r in single_results).lower()
            single_found = [c for c in dq.expected_content if c.lower() in single_text]
            single_files = set(
                Path(r.metadata.get("source", "")).name for r in single_results
            )
            single_hit = len(single_files & expected_files)
            single_sources_hit += single_hit

            # --- Decomposed search (simulated agent) ---
            all_decomposed = []
            for sq in dq.sub_queries:
                results = search_with_routing(
                    scale_store, sq, n_results=3, query_type="simple"
                )
                all_decomposed.extend(results)

            # Deduplicate by text
            seen = set()
            unique = []
            for r in all_decomposed:
                if r.text not in seen:
                    seen.add(r.text)
                    unique.append(r)

            decomposed_text = " ".join(r.text for r in unique).lower()
            decomposed_found = [c for c in dq.expected_content if c.lower() in decomposed_text]
            decomposed_files = set(
                Path(r.metadata.get("source", "")).name for r in unique
            )
            decomposed_hit = len(decomposed_files & expected_files)
            decomposed_sources_hit += decomposed_hit

            single_content_total += len(single_found)
            decomposed_content_total += len(decomposed_found)
            expected_content_total += len(dq.expected_content)

            # Print per-query comparison
            s_marker = "✓" if single_hit == len(expected_files) else ("◐" if single_hit > 0 else "✗")
            d_marker = "✓" if decomposed_hit == len(expected_files) else ("◐" if decomposed_hit > 0 else "✗")
            print(f"\n  {dq.original[:80]}")
            print(f"    Single:     {s_marker} {single_hit}/{len(expected_files)} sources  "
                  f"content={len(single_found)}/{len(dq.expected_content)}")
            print(f"    Decomposed: {d_marker} {decomposed_hit}/{len(expected_files)} sources  "
                  f"content={len(decomposed_found)}/{len(dq.expected_content)}")

        # Summary
        single_content_pct = single_content_total / expected_content_total * 100
        decomposed_content_pct = decomposed_content_total / expected_content_total * 100
        single_source_pct = single_sources_hit / total_expected_sources * 100
        decomposed_source_pct = decomposed_sources_hit / total_expected_sources * 100

        print(f"\n{'='*90}")
        print(f"{'Metric':<25} {'Single Search':>15} {'Decomposed':>15} {'Improvement':>15}")
        print(f"{'-'*70}")
        print(f"{'Content match':<25} {single_content_pct:>14.1f}% {decomposed_content_pct:>14.1f}% "
              f"{decomposed_content_pct - single_content_pct:>+14.1f}%")
        print(f"{'Source coverage':<25} {single_source_pct:>14.1f}% {decomposed_source_pct:>14.1f}% "
              f"{decomposed_source_pct - single_source_pct:>+14.1f}%")
        print(f"{'='*90}")

        # Save
        out = Path(__file__).parent / "results" / "decomposed_benchmark.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({
            "single_content_pct": round(single_content_pct, 1),
            "decomposed_content_pct": round(decomposed_content_pct, 1),
            "single_source_pct": round(single_source_pct, 1),
            "decomposed_source_pct": round(decomposed_source_pct, 1),
            "queries": len(DECOMPOSED_QUERIES),
        }, indent=2))
        print(f"\n💾 Saved to {out}")
