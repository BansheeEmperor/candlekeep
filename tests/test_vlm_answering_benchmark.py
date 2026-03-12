"""VLM answering benchmark — Option C: does VLM help agents answer visual queries?

Measures whether an LLM can answer visual queries when given retrieved chunks.
- Baseline (no VLM): LLM gets text chunks that say "refer to diagram" → can't answer
- With VLM: LLM gets text + caption chunks with specific values → can answer

Metric: Answer accuracy (does LLM's answer contain the ground truth value?)

Requirements:
  - CANDLEKEEP_VLM_PROVIDER and CANDLEKEEP_LLM_PROVIDER set
  - Live ChromaDB on localhost:8000
  - Corpus generated: python scripts/generate_real_corpus.py

Run: pytest tests/test_vlm_answering_benchmark.py -v -s -m benchmark
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.benchmark]

CORPUS_DIR = Path(__file__).parent / "fixtures" / "real_corpus"
SUITE_FILE = CORPUS_DIR / "eval_real_suite.json"


def _skip_reason() -> str | None:
    if not os.getenv("CANDLEKEEP_VLM_PROVIDER"):
        return "CANDLEKEEP_VLM_PROVIDER not set"
    if not os.getenv("CANDLEKEEP_LLM_PROVIDER"):
        return "CANDLEKEEP_LLM_PROVIDER not set (needed for answer generation)"
    if not SUITE_FILE.exists():
        return "Queries not found"
    try:
        import chromadb
        chromadb.HttpClient(host="localhost", port=8000).heartbeat()
    except Exception:
        return "ChromaDB not reachable"
    return None


skip_reason = _skip_reason()
pytestmark = [pytest.mark.benchmark, pytest.mark.skipif(bool(skip_reason), reason=skip_reason or "")]


def _normalize(text: str) -> str:
    """Normalize for comparison: lowercase, strip, remove punctuation."""
    return re.sub(r'[^\w\s]', '', text.lower().strip())


def _answer_matches(answer: str, ground_truth: str) -> bool:
    """Check if answer contains the ground truth value."""
    norm_answer = _normalize(answer)
    norm_truth = _normalize(ground_truth)
    return norm_truth in norm_answer


def _ask_llm(llm, query: str, context_chunks: list) -> str:
    """Ask LLM to answer query given context chunks."""
    context = "\n\n".join(f"[{i+1}] {c.text}" for i, c in enumerate(context_chunks))
    prompt = f"""Answer this technical question using ONLY the provided context.

Question: {query}

Context:
{context}

Answer the question precisely. If the context doesn't contain the answer, respond with "Information not available in context."
Answer:"""
    try:
        return llm.complete(prompt, max_tokens=100, temperature=0.0)
    except Exception as e:
        return f"ERROR: {e}"


@pytest.fixture(scope="module")
def llm():
    from candlekeep.providers.factory import create_llm_provider
    return create_llm_provider()


@pytest.fixture(scope="module")
def queries() -> list[dict]:
    return json.loads(SUITE_FILE.read_text())


class TestVLMAnsweringBenchmark:
    def test_answering_with_vlm(self, llm, queries):
        """Answer accuracy WITH VLM captioning (caption chunks in context)."""
        from candlekeep.config import Settings
        from candlekeep.database.vector_store import ChromaVectorStore
        from candlekeep.rag.processor import DocumentProcessor
        from candlekeep.rag.router import search_with_routing

        settings = Settings.from_env()
        store = ChromaVectorStore(settings)
        processor = DocumentProcessor(settings)

        # Ingest with VLM
        store.clear()
        for doc in sorted(CORPUS_DIR.glob("*.md")):
            result = processor.process(doc)
            store.add_documents(result.chunks)

        correct = 0
        print(f"\n--- Answering WITH VLM ({len(queries)} queries) ---")
        print(f"{'Query':<50} {'Correct':>7} {'Answer':<30}")
        print("-" * 90)

        for q in queries:
            results = search_with_routing(store, q["query"], n_results=10, query_type="simple")
            answer = _ask_llm(llm, q["query"], results)
            is_correct = _answer_matches(answer, q["answer"])
            if is_correct:
                correct += 1
            status = "✓" if is_correct else "✗"
            print(f"  {status} {q['query'][:48]:<48} {answer[:28]:<28}")

        accuracy = correct / len(queries)
        print(f"\nAnswer Accuracy (with VLM): {accuracy:.2f} ({correct}/{len(queries)})")
        assert accuracy >= 0.60, f"Accuracy {accuracy:.2f} below 0.60 threshold"

    def test_answering_baseline(self, llm, queries):
        """Answer accuracy WITHOUT VLM (only text chunks, no captions). Runs last."""
        from candlekeep.config import Settings
        from candlekeep.database.vector_store import ChromaVectorStore
        from candlekeep.rag.processor import DocumentProcessor
        from candlekeep.rag.router import search_with_routing

        settings = Settings.from_env()
        store = ChromaVectorStore(settings)

        # Ingest without VLM
        no_vlm = DocumentProcessor.__new__(DocumentProcessor)
        no_vlm.settings = settings
        no_vlm._captioner = None

        store.clear()
        for doc in sorted(CORPUS_DIR.glob("*.md")):
            result = no_vlm.process(doc)
            store.add_documents(result.chunks)

        correct = 0
        print(f"\n--- Answering WITHOUT VLM ({len(queries)} queries) ---")
        print(f"{'Query':<50} {'Correct':>7} {'Answer':<30}")
        print("-" * 90)

        for q in queries:
            results = search_with_routing(store, q["query"], n_results=10, query_type="simple")
            answer = _ask_llm(llm, q["query"], results)
            is_correct = _answer_matches(answer, q["answer"])
            if is_correct:
                correct += 1
            status = "✓" if is_correct else "✗"
            print(f"  {status} {q['query'][:48]:<48} {answer[:28]:<28}")

        baseline = correct / len(queries)
        print(f"\nAnswer Accuracy (baseline): {baseline:.2f} ({correct}/{len(queries)})")
        print(f"Expected ~0.0 — text chunks say 'refer to diagram', LLM can't answer")
