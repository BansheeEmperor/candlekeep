"""Real corpus VLM benchmark — Case 1: visual knowledge retrieval.

Correct metric: does a CAPTION CHUNK containing the specific visual detail
appear in the top-5 results? Text retrieval already finds the right document
(HR@5 ≈ 1.0 with or without VLM). The question is whether the caption chunk
surfaces alongside the text chunks, making the specific detail directly
retrievable.

Metrics:
  - Caption Chunk Hit Rate@5: caption chunk from correct doc in top-5
  - Caption Chunk MRR: mean reciprocal rank of caption chunks
  - Embedding score comparison: caption vs text chunk scores per query
  - Score gap: caption_score - best_text_score (positive = caption ranks higher)

Baseline (no VLM): Caption Hit Rate = 0.0, no caption chunks exist.
With VLM: Caption Hit Rate should be >= 0.60.

Requirements:
  - CANDLEKEEP_VLM_PROVIDER set
  - Live ChromaDB on localhost:8000
  - Corpus generated: python scripts/generate_real_corpus.py

Run: pytest tests/test_vlm_benchmark_real.py -v -s -m benchmark
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.benchmark]

CORPUS_DIR = Path(__file__).parent / "fixtures" / "real_corpus"
SUITE_FILE = CORPUS_DIR / "eval_real_suite.json"


def _skip_reason() -> str | None:
    if not os.getenv("CANDLEKEEP_VLM_PROVIDER"):
        return "CANDLEKEEP_VLM_PROVIDER not set"
    if not SUITE_FILE.exists():
        return "Queries not found — run: python scripts/generate_real_corpus.py"
    if not list(CORPUS_DIR.glob("*.md")):
        return "Corpus not found — run: python scripts/generate_real_corpus.py"
    try:
        import chromadb
        chromadb.HttpClient(host="localhost", port=8000).heartbeat()
    except Exception:
        return "ChromaDB not reachable on localhost:8000"
    return None


skip_reason = _skip_reason()
pytestmark = [pytest.mark.benchmark, pytest.mark.skipif(bool(skip_reason), reason=skip_reason or "")]


def _source_matches(src: str, expected: list[str]) -> bool:
    return any(src.endswith(e) or e.endswith(src) or src == e for e in expected)


def _ingest_corpus(store, processor) -> dict:
    store.clear()
    total_captioned = total_from_cache = 0
    latencies: list[float] = []
    for doc in sorted(CORPUS_DIR.glob("*.md")):
        t0 = time.perf_counter()
        result = processor.process(doc)
        elapsed = time.perf_counter() - t0
        if result.images_captioned:
            latencies.append(elapsed / result.images_captioned)
        store.add_documents(result.chunks)
        total_captioned += result.images_captioned
        total_from_cache += result.images_from_cache
    return {
        "total_captioned": total_captioned,
        "total_from_cache": total_from_cache,
        "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
    }


@pytest.fixture(scope="module")
def store_and_processor():
    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore
    from candlekeep.rag.processor import DocumentProcessor
    settings = Settings.from_env()
    return ChromaVectorStore(settings), DocumentProcessor(settings)


@pytest.fixture(scope="module")
def queries() -> list[dict]:
    return json.loads(SUITE_FILE.read_text())


class TestRealCorpusVLMBenchmark:
    def test_ingest_corpus_with_captioning(self, store_and_processor):
        """Ingest all 50 docs with VLM captioning."""
        store, processor = store_and_processor
        stats = _ingest_corpus(store, processor)
        total = stats["total_captioned"] + stats["total_from_cache"]
        print(f"\n  Captioned: {stats['total_captioned']}  From cache: {stats['total_from_cache']}")
        print(f"  Avg caption latency: {stats['avg_latency']:.1f}s/image")
        assert total > 0, "No caption chunks produced"
        if stats["avg_latency"] > 0:
            assert stats["avg_latency"] <= 8.0

    def test_caption_chunk_retrieval(self, store_and_processor, queries):
        """Core Case 1 metric: does a caption chunk from the correct doc appear in top-5?

        Baseline (no VLM): 0.0 — no caption chunks exist.
        With VLM: caption chunks contain specific visual details → should be >= 0.60.
        """
        store, _ = store_and_processor
        from candlekeep.rag.router import search_with_routing

        caption_hits = 0
        text_hits = 0
        mrr_sum = 0.0
        score_gaps: list[float] = []

        print(f"\n--- Caption Chunk Retrieval ({len(queries)} queries) ---")
        print(f"{'Query':<55} {'Cap@5':>5} {'Rank':>5} {'CapScore':>9} {'TxtScore':>9} {'Gap':>7}")
        print("-" * 95)

        for q in queries:
            results = search_with_routing(store, q["query"], n_results=10, query_type="hybrid")

            # Find best caption chunk and best text chunk from correct doc in top-10
            cap_rank = None
            cap_score = 0.0
            txt_score = 0.0

            for rank, r in enumerate(results, 1):
                is_correct = _source_matches(r.metadata.get("source", ""), q["expected_sources"])
                is_caption = r.metadata.get("content_type") == "image_caption"

                if is_correct and is_caption and cap_rank is None:
                    cap_rank = rank
                    cap_score = r.score
                if is_correct and not is_caption:
                    txt_score = max(txt_score, r.score)

            cap_in_top5 = cap_rank is not None and cap_rank <= 5
            txt_in_top5 = any(
                _source_matches(r.metadata.get("source", ""), q["expected_sources"])
                and r.metadata.get("content_type") != "image_caption"
                for r in results[:5]
            )

            if cap_in_top5:
                caption_hits += 1
                mrr_sum += 1.0 / cap_rank
            if txt_in_top5:
                text_hits += 1

            gap = cap_score - txt_score if cap_score > 0 else float("-inf")
            if cap_score > 0:
                score_gaps.append(gap)

            rank_str = str(cap_rank) if cap_rank else "—"
            cap_str = f"{cap_score:.4f}" if cap_score > 0 else "  none"
            txt_str = f"{txt_score:.4f}" if txt_score > 0 else "  none"
            gap_str = f"{gap:+.4f}" if cap_score > 0 else "     —"
            hit_str = "✓" if cap_in_top5 else "✗"
            print(f"  {hit_str} {q['query'][:53]:<53} {rank_str:>5} {cap_str:>9} {txt_str:>9} {gap_str:>7}")

        n = len(queries)
        cap_hr5 = caption_hits / n
        txt_hr5 = text_hits / n
        mrr = mrr_sum / n
        avg_gap = sum(score_gaps) / len(score_gaps) if score_gaps else 0.0
        pct_cap_beats_txt = sum(1 for g in score_gaps if g > 0) / len(score_gaps) if score_gaps else 0.0

        print(f"\n{'─'*95}")
        print(f"Caption Chunk Hit Rate@5:  {cap_hr5:.2f} ({caption_hits}/{n})")
        print(f"Text Chunk Hit Rate@5:     {txt_hr5:.2f} ({text_hits}/{n})  ← text retrieval baseline")
        print(f"Caption Chunk MRR:         {mrr:.3f}")
        print(f"Avg score gap (cap-txt):   {avg_gap:+.4f}  ({'caption ranks higher' if avg_gap > 0 else 'text ranks higher'})")
        print(f"Caption beats text:        {pct_cap_beats_txt:.0%} of queries")

        assert cap_hr5 >= 0.60, f"Caption Chunk HR@5 {cap_hr5:.2f} below 0.60 threshold"

    def test_embedding_score_comparison(self, store_and_processor, queries):
        """Embedding metric: compare caption vs text chunk scores across all queries.

        Shows whether VLM captions are semantically closer to visual queries
        than the surrounding text chunks.
        """
        store, _ = store_and_processor
        from candlekeep.rag.router import search_with_routing

        cap_scores: list[float] = []
        txt_scores: list[float] = []
        cap_ranks: list[int] = []

        for q in queries:
            results = search_with_routing(store, q["query"], n_results=20, query_type="simple")
            for rank, r in enumerate(results, 1):
                if not _source_matches(r.metadata.get("source", ""), q["expected_sources"]):
                    continue
                if r.metadata.get("content_type") == "image_caption":
                    cap_scores.append(r.score)
                    cap_ranks.append(rank)
                else:
                    txt_scores.append(r.score)

        avg_cap = sum(cap_scores) / len(cap_scores) if cap_scores else 0
        avg_txt = sum(txt_scores) / len(txt_scores) if txt_scores else 0
        avg_rank = sum(cap_ranks) / len(cap_ranks) if cap_ranks else float("inf")

        print(f"\n--- Embedding Score Comparison (simple/vector search) ---")
        print(f"Caption chunks found:      {len(cap_scores)}/{len(queries)}")
        print(f"Avg caption chunk score:   {avg_cap:.4f}")
        print(f"Avg text chunk score:      {avg_txt:.4f}")
        print(f"Caption score advantage:   {avg_cap - avg_txt:+.4f}")
        print(f"Avg caption chunk rank:    {avg_rank:.1f}")

        assert len(cap_scores) > 0, "No caption chunks found — VLM captioning may have failed"
        assert avg_cap > avg_txt, (
            f"Caption chunks ({avg_cap:.4f}) should score higher than text chunks ({avg_txt:.4f}) "
            f"for visual queries"
        )

    def test_baseline_no_vlm(self, store_and_processor, queries):
        """Baseline: ingest WITHOUT VLM, measure caption chunk hit rate (must be 0.0).

        Confirms the knowledge gap: without VLM, no caption chunks exist,
        so visual details are completely unretrievable. Runs last.
        """
        store, processor = store_and_processor
        from candlekeep.rag.processor import DocumentProcessor
        from candlekeep.rag.router import search_with_routing

        no_vlm = DocumentProcessor.__new__(DocumentProcessor)
        no_vlm.settings = processor.settings
        no_vlm._captioner = None

        store.clear()
        for doc in sorted(CORPUS_DIR.glob("*.md")):
            result = no_vlm.process(doc)
            store.add_documents(result.chunks)

        caption_hits = text_hits = 0
        for q in queries:
            results = search_with_routing(store, q["query"], n_results=5, query_type="hybrid")
            for r in results[:5]:
                if _source_matches(r.metadata.get("source", ""), q["expected_sources"]):
                    if r.metadata.get("content_type") == "image_caption":
                        caption_hits += 1
                    else:
                        text_hits += 1
                        break

        n = len(queries)
        print(f"\n--- Baseline (no VLM) ---")
        print(f"Caption Chunk Hit Rate@5:  0.00 (0/{n})  ← no caption chunks exist")
        print(f"Text Chunk Hit Rate@5:     {text_hits/n:.2f} ({text_hits}/{n})  ← text retrieval still works")
        print(f"Knowledge gap confirmed:   visual details are unretrievable without VLM")

        assert caption_hits == 0, f"Expected 0 caption hits without VLM, got {caption_hits}"
