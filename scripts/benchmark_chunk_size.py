#!/usr/bin/env python3
"""Benchmark: Chunk size impact on unstructured text.

The original chunk size sweep (Entry 21) tested on markdown-header-structured
docs where 768 and 1024 produced identical chunking. This benchmark uses a
corpus of long-form prose without headers, forcing the fixed-size chunker
to be the primary splitter at every chunk_size value.

Sweeps chunk_size=[256, 512, 768, 1024] with Arcane Recall active.
Reports MRR, nDCG@5, Hit Rate@5, chunk count, and avg chunk length
to confirm that different sizes produce genuinely different chunking.

Usage:
  python scripts/benchmark_chunk_size.py [--corpus unstructured|standard]
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Tuple

os.environ["CANDLEKEEP_DEVICE"] = "cpu"

sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np

from candlekeep.config import Settings
from candlekeep.database.interface import SearchResult, Chunk
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.arcane_recall import search_with_arcane_recall
from candlekeep.rag.search import preprocess_negation
from candlekeep.eval.metrics import (
    calculate_reciprocal_rank,
    calculate_ndcg,
    calculate_hit_rate,
    calculate_precision_at_k,
)
from candlekeep.eval.statistics import bootstrap_ci

import chromadb
from candlekeep.database.embeddings import EmbeddingManager


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
        import hashlib
        ids = [hashlib.sha256(
            f"{c.metadata['source']}:{c.chunk_index}:{c.text[:100]}".encode()
        ).hexdigest()[:16] for c in chunks]
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        metadatas = [{**c.metadata, "chunk_index": c.chunk_index} for c in chunks]
        self.collection.upsert(ids=ids, embeddings=embeddings,
                               documents=texts, metadatas=metadatas)
        return len(chunks)

    def search(self, query: str, n_results: int = 5, category=None):
        embedding = self.embedder.embed_query(query)
        results = self.collection.query(
            query_embeddings=[embedding], n_results=n_results * 3)
        if not results["ids"][0]:
            return []
        candidates = [
            SearchResult(text=doc, metadata=meta, score=1 - dist, doc_id=doc_id)
            for doc_id, doc, meta, dist in zip(
                results["ids"][0], results["documents"][0],
                results["metadatas"][0], results["distances"][0])
        ]
        # Metadata boosting (Bardic Inspiration)
        query_terms = set(query.lower().split())
        for r in candidates:
            boost = 0
            for field in ("title", "description", "keywords"):
                val = r.metadata.get(field, "").lower()
                if sum(1 for t in query_terms if t in val):
                    boost += 0.2
            r.score += boost
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:n_results]

    def get_chunks_by_source(self, source: str):
        results = self.collection.get(where={"source": source})
        if not results["ids"]:
            return []
        return [SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
                for doc_id, doc, meta in zip(
                    results["ids"], results["documents"], results["metadatas"])]

    def get_embeddings(self, texts):
        if not texts:
            return []
        emb = self.embedder.embed(texts)
        return emb.tolist() if hasattr(emb, "tolist") else emb

    def get_stored_embeddings_by_source(self, source: str):
        results = self.collection.get(
            where={"source": source}, include=["embeddings", "metadatas"])
        if not results["ids"]:
            return {}
        return {meta.get("chunk_index", 0): emb
                for meta, emb in zip(results["metadatas"], results["embeddings"])}


@dataclass
class SweepResult:
    chunk_size: int
    chunk_count: int
    avg_chunk_chars: int
    mrr: float
    mrr_ci: Tuple[float, float]
    ndcg_5: float
    hit_rate_5: float
    precision_5: float
    avg_latency_ms: float
    n_queries: int
    by_category: Dict[str, Dict[str, float]]


def run_sweep(corpus_dir: Path, queries_path: Path, chunk_sizes: List[int],
              overlap: int = 50) -> List[SweepResult]:
    """Run chunk size sweep on the given corpus."""
    with open(queries_path) as f:
        raw = json.load(f)
    queries = raw["queries"]
    # Filter out adversarial queries (expected_sources=[])
    queries = [q for q in queries if q.get("expected_sources")]

    results = []
    for size in chunk_sizes:
        print(f"\n  chunk_size={size}, overlap={overlap}")
        temp_dir = tempfile.mkdtemp(prefix=f"ck_chunk_{size}_")
        try:
            settings = Settings.from_env()
            settings.chunk_size = size
            settings.chunk_overlap = overlap
            store = LocalVectorStore(temp_dir, settings)
            processor = DocumentProcessor(settings)

            # Ingest
            doc_count = 0
            total_chunks = 0
            total_chars = 0
            for doc in sorted(corpus_dir.glob("*.md")):
                chunks = processor.process(str(doc))
                store.add_documents(chunks)
                doc_count += 1
                total_chunks += len(chunks)
                total_chars += sum(len(c.text) for c in chunks)

            avg_chars = total_chars // max(total_chunks, 1)
            print(f"    {doc_count} docs, {total_chunks} chunks, "
                  f"avg {avg_chars} chars/chunk")

            # Evaluate
            mrr_vals, ndcg_vals, hr_vals, prec_vals, lat_vals = [], [], [], [], []
            cat_data: Dict[str, List[Dict]] = {}

            for q in queries:
                query = q["query"]
                gt = set(q["expected_sources"])
                cat = q.get("category", "unknown")

                t0 = time.time()
                processed = preprocess_negation(query)
                res = search_with_arcane_recall(store, processed, n_results=5)
                lat = (time.time() - t0) * 1000

                retrieved = []
                for r in res:
                    src = r.metadata.get("source", "")
                    if "tests/fixtures" in src:
                        src = src[src.index("tests/fixtures"):]
                    retrieved.append(src)

                mrr = calculate_reciprocal_rank(retrieved, gt)
                ndcg = calculate_ndcg(retrieved, gt, 5)
                hr = calculate_hit_rate(retrieved, gt, 5)
                prec = calculate_precision_at_k(retrieved, gt, 5)

                mrr_vals.append(mrr)
                ndcg_vals.append(ndcg)
                hr_vals.append(hr)
                prec_vals.append(prec)
                lat_vals.append(lat)

                if cat not in cat_data:
                    cat_data[cat] = []
                cat_data[cat].append({"mrr": mrr, "ndcg": ndcg, "hr": hr})

            mrr_mean, mrr_lo, mrr_hi = bootstrap_ci(mrr_vals)
            by_cat = {}
            for cat, vals in cat_data.items():
                by_cat[cat] = {
                    "mrr": float(np.mean([v["mrr"] for v in vals])),
                    "ndcg_5": float(np.mean([v["ndcg"] for v in vals])),
                    "hit_rate_5": float(np.mean([v["hr"] for v in vals])),
                    "count": len(vals),
                }

            sr = SweepResult(
                chunk_size=size,
                chunk_count=total_chunks,
                avg_chunk_chars=avg_chars,
                mrr=mrr_mean,
                mrr_ci=(mrr_lo, mrr_hi),
                ndcg_5=float(np.mean(ndcg_vals)),
                hit_rate_5=float(np.mean(hr_vals)),
                precision_5=float(np.mean(prec_vals)),
                avg_latency_ms=float(np.mean(lat_vals)),
                n_queries=len(queries),
                by_category=by_cat,
            )
            results.append(sr)
            print(f"    MRR={sr.mrr:.4f}  nDCG@5={sr.ndcg_5:.4f}  "
                  f"HR@5={sr.hit_rate_5:.4f}  Latency={sr.avg_latency_ms:.0f}ms")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark chunk size on unstructured text")
    parser.add_argument("--corpus", choices=["unstructured", "standard"],
                        default="unstructured")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    fixtures = Path(__file__).parent.parent / "tests" / "fixtures"

    if args.corpus == "unstructured":
        corpus_dir = fixtures / "unstructured_docs"
        queries_path = corpus_dir / "eval_queries.json"
    else:
        corpus_dir = fixtures / "sample_docs"
        queries_path = fixtures / "eval_suite_100.json"

    if not corpus_dir.exists():
        print(f"Corpus not found: {corpus_dir}")
        print("Run scripts/generate_unstructured_corpus.py first")
        sys.exit(1)

    chunk_sizes = [256, 512, 768, 1024]
    print(f"Chunk Size Sweep Benchmark")
    print(f"  Corpus: {args.corpus} ({corpus_dir})")
    print(f"  Sizes: {chunk_sizes}")

    results = run_sweep(corpus_dir, queries_path, chunk_sizes)

    # Summary table
    print(f"\n{'='*72}")
    print(f"{'Size':>6} {'Chunks':>7} {'AvgCh':>6} {'MRR':>7} {'nDCG@5':>7} "
          f"{'HR@5':>7} {'P@5':>7} {'Lat':>6}")
    print("-" * 72)
    for r in results:
        print(f"{r.chunk_size:>6} {r.chunk_count:>7} {r.avg_chunk_chars:>6} "
              f"{r.mrr:>7.4f} {r.ndcg_5:>7.4f} {r.hit_rate_5:>7.4f} "
              f"{r.precision_5:>7.4f} {r.avg_latency_ms:>5.0f}ms")

    # Confirm differentiation
    counts = [r.chunk_count for r in results]
    if len(set(counts)) == len(counts):
        print(f"\n✓ All chunk sizes produce different chunk counts — "
              f"sweep is valid")
    else:
        dupes = [s for s in chunk_sizes
                 if counts.count(results[chunk_sizes.index(s)].chunk_count) > 1]
        print(f"\n⚠ Chunk sizes {dupes} produce identical chunk counts — "
              f"sweep may not differentiate at these values")

    # Save
    output = args.output
    if not output:
        results_dir = Path(__file__).parent.parent / "tests" / "results"
        results_dir.mkdir(exist_ok=True)
        output = str(results_dir / f"chunk_size_{args.corpus}.json")

    report = {"config": {"chunk_sizes": chunk_sizes, "corpus": args.corpus,
                         "overlap": 50},
              "results": [asdict(r) for r in results]}
    Path(output).write_text(json.dumps(report, indent=2, default=float))
    print(f"\n💾 Saved to {output}")


if __name__ == "__main__":
    main()
