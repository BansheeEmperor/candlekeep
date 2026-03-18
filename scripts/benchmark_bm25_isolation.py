#!/usr/bin/env python3
"""Benchmark: Isolate BM25 tokenizer vs RRF fusion contribution.

The hybrid path improved lexical query MRR by +26% over the simple path.
This benchmark isolates whether the gain comes from:
  (a) BM25 finding results that vector search misses (tokenizer contribution)
  (b) RRF fusion reranking improving the order (fusion contribution)
  (c) Both

Runs three pipelines on the Centurion Set lexical queries (n=30):
  1. hybrid (full pipeline): search_with_routing(query_type="hybrid")
  2. bm25-only: BM25Searcher.search() + Arcane Recall (no Ward, no Dispersal)
  3. hybrid (full pipeline): search_with_routing(query_type="hybrid")

Usage:
  python scripts/benchmark_bm25_isolation.py [--output PATH]
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
from candlekeep.rag.arcane_recall import expand_results, search_with_arcane_recall
from candlekeep.rag.hybrid import BM25Searcher
from candlekeep.rag.router import search_with_routing
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

    def get_all_chunks(self):
        results = self.collection.get()
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
class PipelineResult:
    label: str
    mrr: float
    mrr_ci: Tuple[float, float]
    ndcg_5: float
    hit_rate_5: float
    precision_5: float
    avg_latency_ms: float
    n_queries: int
    per_query: List[Dict]


def evaluate_pipeline(label: str, store, bm25: BM25Searcher | None,
                      queries: list, mode: str) -> PipelineResult:
    """Run a single pipeline on the query set.

    mode:
      vector  — db.search() + Arcane Recall
      bm25    — BM25Searcher.search() + Arcane Recall
      hybrid  — hybrid_search() (vector + BM25 + RRF + Arcane Recall)
    """
    mrr_vals, ndcg_vals, hr_vals, prec_vals, lat_vals = [], [], [], [], []
    per_query = []

    for q in queries:
        query = q["query"]
        gt = set(q["expected_sources"])

        t0 = time.time()
        processed = preprocess_negation(query)

        if mode == "hybrid":
            results = search_with_routing(store, query, n_results=5,
                                          query_type="hybrid")
        elif mode == "bm25":
            # BM25-only: get BM25 results, then expand with Arcane Recall
            raw = bm25.search(processed, n_results=20)
            results = expand_results(store, raw, n_results=5, query=processed)
        elif mode == "hybrid":
            results = search_with_routing(store, query, n_results=5,
                                          query_type="hybrid")
        else:
            raise ValueError(f"Unknown mode: {mode}")

        lat = (time.time() - t0) * 1000

        retrieved = []
        for r in results:
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
        per_query.append({
            "query": query, "mrr": mrr, "hr5": hr,
            "retrieved_sources": retrieved[:3],
        })

    mrr_mean, mrr_lo, mrr_hi = bootstrap_ci(mrr_vals)
    return PipelineResult(
        label=label,
        mrr=mrr_mean,
        mrr_ci=(mrr_lo, mrr_hi),
        ndcg_5=float(np.mean(ndcg_vals)),
        hit_rate_5=float(np.mean(hr_vals)),
        precision_5=float(np.mean(prec_vals)),
        avg_latency_ms=float(np.mean(lat_vals)),
        n_queries=len(queries),
        per_query=per_query,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Isolate BM25 tokenizer vs RRF fusion contribution")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--all-queries", action="store_true",
                        help="Run on all 108 queries, not just lexical")
    args = parser.parse_args()

    fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
    queries_path = fixtures / "eval_suite_100.json"

    with open(queries_path) as f:
        all_queries = json.load(f)["queries"]

    if args.all_queries:
        queries = [q for q in all_queries if q.get("expected_sources")]
        subset_label = "all (non-adversarial)"
    else:
        queries = [q for q in all_queries if q.get("category") == "lexical"]
        subset_label = "lexical only"

    print(f"BM25 Isolation Benchmark")
    print(f"  Queries: {len(queries)} ({subset_label})")
    print()

    temp_dir = tempfile.mkdtemp(prefix="ck_bm25_iso_")
    try:
        settings = Settings.from_env()
        store = LocalVectorStore(temp_dir, settings)
        processor = DocumentProcessor(settings)

        # Ingest standard corpus
        print("Seeding corpus...")
        doc_count = 0
        for subdir in ("sample_docs", "scale_docs"):
            docs_dir = fixtures / subdir
            if docs_dir.exists():
                for doc in sorted(docs_dir.glob("*")):
                    if doc.is_file():
                        chunks = processor.process(str(doc))
                        store.add_documents(chunks)
                        doc_count += 1
        print(f"  {doc_count} documents ingested")

        # Build BM25 index
        print("Building BM25 index...")
        all_chunks = store.get_all_chunks()
        bm25 = BM25Searcher(all_chunks)
        print(f"  {len(all_chunks)} chunks indexed\n")

        # Run three pipelines
        pipelines = [
            ("hybrid (full)", "hybrid"),
            ("bm25-only", "bm25"),
            ("hybrid (full)", "hybrid"),
        ]

        results = []
        for label, mode in pipelines:
            print(f"  Running {label}...", end=" ", flush=True)
            r = evaluate_pipeline(label, store, bm25, queries, mode)
            results.append(r)
            print(f"MRR={r.mrr:.4f}  HR@5={r.hit_rate_5:.4f}  "
                  f"P@5={r.precision_5:.4f}  Lat={r.avg_latency_ms:.0f}ms")

        # Summary
        print(f"\n{'='*65}")
        print(f"{'Pipeline':<18} {'MRR':>7} {'nDCG@5':>7} {'HR@5':>7} "
              f"{'P@5':>7} {'Lat':>6}")
        print("-" * 65)
        for r in results:
            print(f"{r.label:<18} {r.mrr:>7.4f} {r.ndcg_5:>7.4f} "
                  f"{r.hit_rate_5:>7.4f} {r.precision_5:>7.4f} "
                  f"{r.avg_latency_ms:>5.0f}ms")

        # Attribution analysis
        vec = results[0]
        bm25_r = results[1]
        hyb = results[2]
        total_gain = hyb.mrr - vec.mrr
        bm25_gain = bm25_r.mrr - vec.mrr
        fusion_gain = hyb.mrr - max(vec.mrr, bm25_r.mrr)

        print(f"\nAttribution (MRR on {subset_label}):")
        print(f"  Vector baseline:     {vec.mrr:.4f}")
        print(f"  BM25-only:           {bm25_r.mrr:.4f}  "
              f"(Δ={bm25_gain:+.4f} vs vector)")
        print(f"  Hybrid (RRF):        {hyb.mrr:.4f}  "
              f"(Δ={total_gain:+.4f} vs vector)")
        if abs(total_gain) > 0.001:
            print(f"  BM25 contribution:   {bm25_gain/total_gain*100:+.1f}% "
                  f"of total gain")
            print(f"  Fusion contribution: {fusion_gain/total_gain*100:+.1f}% "
                  f"of total gain")
        else:
            print(f"  Total gain is negligible ({total_gain:.4f})")

        # Per-query comparison: where does BM25 help?
        print(f"\nPer-query analysis (queries where BM25 changes outcome):")
        vec_pq = {q["query"]: q for q in results[0].per_query}
        bm25_pq = {q["query"]: q for q in results[1].per_query}
        hyb_pq = {q["query"]: q for q in results[2].per_query}

        bm25_wins = 0
        bm25_losses = 0
        for q in queries:
            query = q["query"]
            v_mrr = vec_pq[query]["mrr"]
            b_mrr = bm25_pq[query]["mrr"]
            h_mrr = hyb_pq[query]["mrr"]
            if b_mrr > v_mrr + 0.01:
                bm25_wins += 1
                print(f"  BM25 wins: \"{query[:60]}\" "
                      f"(vec={v_mrr:.2f} bm25={b_mrr:.2f} hyb={h_mrr:.2f})")
            elif v_mrr > b_mrr + 0.01:
                bm25_losses += 1

        print(f"\n  BM25 wins: {bm25_wins}/{len(queries)} queries")
        print(f"  BM25 losses: {bm25_losses}/{len(queries)} queries")
        print(f"  Ties: {len(queries) - bm25_wins - bm25_losses}/{len(queries)}")

        # Save
        output = args.output
        if not output:
            results_dir = Path(__file__).parent.parent / "tests" / "results"
            results_dir.mkdir(exist_ok=True)
            suffix = "all" if args.all_queries else "lexical"
            output = str(results_dir / f"bm25_isolation_{suffix}.json")

        report = {
            "config": {"subset": subset_label, "n_queries": len(queries)},
            "results": [asdict(r) for r in results],
            "attribution": {
                "vector_mrr": vec.mrr,
                "bm25_mrr": bm25_r.mrr,
                "hybrid_mrr": hyb.mrr,
                "total_gain": total_gain,
                "bm25_contribution": bm25_gain,
                "fusion_contribution": fusion_gain,
            },
        }
        Path(output).write_text(json.dumps(report, indent=2, default=float))
        print(f"\n💾 Saved to {output}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
