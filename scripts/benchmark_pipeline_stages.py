#!/usr/bin/env python3
"""Benchmark individual pipeline stages of the hybrid search path.

Produces a single authoritative latency breakdown for the simple path,
measured end-to-end on the Centurion Set corpus.  All other latency
references in the documentation should cite this benchmark.

Stages measured:
  1. Negation preprocessing
  2. Query embedding (bi-encoder inference)
  3. ChromaDB vector search (HNSW lookup)
  4. Arcane Recall expansion (stored embedding fetch + similarity checks + window merge)
  5. Relevance Ward (threshold filter)
  6. Prismatic Dispersal (sine-distance diversity reranking, incl. candidate embedding)
  7. Full end-to-end (search_with_routing)

Uses PersistentClient (no HTTP server required).

Usage:
  CANDLEKEEP_DEVICE=cpu python scripts/benchmark_pipeline_stages.py
  python scripts/benchmark_pipeline_stages.py --warmup 5 --output tests/results/pipeline_stages.json

Output:
  JSON report with per-stage p50/mean/p95 latencies and per-query detail.
"""
import argparse
import hashlib
import json
import os
import sys
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("CANDLEKEEP_DEVICE", "cpu")

sys.path.append(str(Path(__file__).parent.parent / "src"))

import chromadb
import numpy as np

from candlekeep.config import Settings
from candlekeep.database.embeddings import EmbeddingManager
from candlekeep.database.interface import SearchResult, Chunk
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.search import preprocess_negation
from candlekeep.rag.arcane_recall import search_with_arcane_recall
from candlekeep.rag.router import (
    _get_vector_threshold,
    search_with_routing,
)


# ── Local vector store (no HTTP server required) ─────────────────────

class LocalVectorStore:
    """Minimal local ChromaDB store for benchmarking."""

    def __init__(self, persist_dir: str, settings: Settings):
        self.settings = settings
        self.embedder = EmbeddingManager.get_instance(settings)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="benchmark",
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, chunks: List[Chunk]) -> int:
        if not chunks:
            return 0

        def _gen_id(c: Chunk) -> str:
            content = f"{c.metadata['source']}:{c.chunk_index}:{c.text[:100]}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

        ids = [_gen_id(c) for c in chunks]
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        metadatas = [{**c.metadata, "chunk_index": c.chunk_index} for c in chunks]
        self.collection.upsert(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
        )
        return len(chunks)

    def search(
        self, query: str, n_results: int = 5, category: str | None = None
    ) -> List[SearchResult]:
        embedding = self.embedder.embed_query(query)
        where = {"category": category} if category else None
        results = self.collection.query(
            query_embeddings=[embedding], n_results=n_results * 3, where=where
        )
        if not results["ids"][0]:
            return []
        candidates = [
            SearchResult(text=doc, metadata=meta, score=1 - dist, doc_id=doc_id)
            for doc_id, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
        excluded = {"index.md", "README.md", "readme.md"}
        candidates = [
            r for r in candidates if r.metadata.get("filename", "") not in excluded
        ]
        query_terms = set(query.lower().split())
        for r in candidates:
            boost = 0
            title = r.metadata.get("title", "").lower()
            if sum(1 for t in query_terms if t in title):
                boost += min(sum(1 for t in query_terms if t in title) * 0.2, 0.6)
            if sum(1 for t in query_terms if t in r.metadata.get("description", "").lower()):
                boost += 0.3
            if sum(1 for t in query_terms if t in r.metadata.get("keywords", "").lower()):
                boost += 0.3
            r.score += boost
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:n_results]

    def get_chunks_by_source(self, source: str) -> List[SearchResult]:
        results = self.collection.get(where={"source": source})
        if not results["ids"]:
            return []
        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(
                results["ids"], results["documents"], results["metadatas"]
            )
        ]

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        emb = self.embedder.embed(texts)
        return emb.tolist() if hasattr(emb, "tolist") else emb

    def get_stored_embeddings_by_source(self, source: str) -> Dict[int, List[float]]:
        results = self.collection.get(
            where={"source": source}, include=["embeddings", "metadatas"]
        )
        if not results["ids"]:
            return {}
        return {
            meta.get("chunk_index", 0): emb
            for meta, emb in zip(results["metadatas"], results["embeddings"])
        }

    def get_all_chunks(self) -> List[SearchResult]:
        results = self.collection.get()
        if not results["ids"]:
            return []
        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(
                results["ids"], results["documents"], results["metadatas"]
            )
        ]


# ── Helpers ──────────────────────────────────────────────────────────

def percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    d = k - f
    return s[f] + d * (s[c] - s[f])


def seed_corpus(db: LocalVectorStore, processor: DocumentProcessor) -> int:
    fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
    count = 0
    for subdir in ["sample_docs", "scale_docs"]:
        doc_dir = fixtures / subdir
        if not doc_dir.exists():
            continue
        for doc_path in sorted(doc_dir.glob("*")):
            if doc_path.is_file():
                chunks = processor.process(str(doc_path))
                db.add_documents(chunks)
                count += 1
    return count


def load_queries() -> list[str]:
    suite_path = (
        Path(__file__).parent.parent / "tests" / "fixtures" / "eval_suite_100.json"
    )
    with open(suite_path) as f:
        data = json.load(f)
    return [q["query"] for q in data["queries"]]


# ── Staged benchmark ─────────────────────────────────────────────────

def run_staged_benchmark(
    db: LocalVectorStore,
    queries: list[str],
    n_results: int = 5,
) -> list[dict]:
    results = []

    for query in queries:
        timings: dict = {}

        # Stage 1: Negation preprocessing
        t0 = time.perf_counter()
        processed = preprocess_negation(query)
        timings["negation_ms"] = (time.perf_counter() - t0) * 1000

        # Stage 2: Query embedding (bi-encoder inference)
        t0 = time.perf_counter()
        _query_emb = db.get_embeddings([processed])
        timings["query_embedding_ms"] = (time.perf_counter() - t0) * 1000

        # Stage 3: ChromaDB vector search (HNSW lookup, includes embedding)
        t0 = time.perf_counter()
        _raw = db.search(processed, n_results=n_results)
        timings["vector_search_ms"] = (time.perf_counter() - t0) * 1000

        # Stage 4: Arcane Recall (full call: vector search + expansion)
        t0 = time.perf_counter()
        expanded = search_with_arcane_recall(db, processed, n_results)
        timings["arcane_recall_full_ms"] = (time.perf_counter() - t0) * 1000
        timings["arcane_recall_expansion_ms"] = max(
            0, timings["arcane_recall_full_ms"] - timings["vector_search_ms"]
        )

        # Stage 5: Relevance Ward
        threshold = _get_vector_threshold(processed)
        t0 = time.perf_counter()
        _warded = [r for r in expanded if r.score >= threshold]
        timings["relevance_ward_ms"] = (time.perf_counter() - t0) * 1000

        # Stage 6: Full end-to-end via search_with_routing
        t0 = time.perf_counter()
        _e2e = search_with_routing(
            db, query, n_results=n_results, query_type="hybrid"
        )
        timings["end_to_end_ms"] = (time.perf_counter() - t0) * 1000

        timings["query"] = query
        results.append(timings)

    return results


def summarize(results: list[dict]) -> dict:
    stages = [
        "negation_ms",
        "query_embedding_ms",
        "vector_search_ms",
        "arcane_recall_full_ms",
        "arcane_recall_expansion_ms",
        "relevance_ward_ms",
        "end_to_end_ms",
    ]
    summary = {}
    for stage in stages:
        values = [r[stage] for r in results]
        summary[stage] = {
            "mean": round(float(np.mean(values)), 2),
            "p50": round(percentile(values, 50), 2),
            "p95": round(percentile(values, 95), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark simple-path pipeline stages"
    )
    parser.add_argument(
        "--warmup", type=int, default=3, help="Warmup queries before timing"
    )
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    print("Setting up temporary database...", file=sys.stderr)
    temp_dir = tempfile.mkdtemp(prefix="candlekeep_stages_")

    try:
        settings = Settings.from_env()
        db = LocalVectorStore(temp_dir, settings)
        processor = DocumentProcessor(settings)

        doc_count = seed_corpus(db, processor)
        print(f"Ingested {doc_count} documents.", file=sys.stderr)

        queries = load_queries()
        print(f"Loaded {len(queries)} queries.", file=sys.stderr)

        # Warmup
        print(f"Warming up ({args.warmup} queries)...", file=sys.stderr)
        for i in range(min(args.warmup, len(queries))):
            search_with_routing(db, queries[i], n_results=5, query_type="hybrid")
        print("Warmup complete.", file=sys.stderr)

        # Benchmark
        print("Running staged benchmark...", file=sys.stderr)
        results = run_staged_benchmark(db, queries)
        summary = summarize(results)

        # Print summary table
        print(
            f"\n{'Stage':<30} {'Mean':>8} {'p50':>8} {'p95':>8}",
            file=sys.stderr,
        )
        print("-" * 56, file=sys.stderr)
        for stage, stats in summary.items():
            label = stage.replace("_ms", "").replace("_", " ")
            print(
                f"{label:<30} {stats['mean']:>7.1f}ms "
                f"{stats['p50']:>7.1f}ms {stats['p95']:>7.1f}ms",
                file=sys.stderr,
            )

        # Build report
        report = {
            "metadata": {
                "device": settings.device,
                "embedding_model": settings.embedding_model,
                "corpus_docs": doc_count,
                "queries": len(queries),
                "warmup": args.warmup,
                "n_results": 5,
            },
            "summary": summary,
            "per_query": results,
        }

        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2))
            print(f"\nReport saved to {args.output}", file=sys.stderr)
        else:
            print(json.dumps(report, indent=2))

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
