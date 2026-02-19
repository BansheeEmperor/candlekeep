#!/usr/bin/env python3
"""Benchmark: Sine-distance diversity reranking strategies.

Tests three sine-distance reranking strategies applied AFTER cosine
cross-encoder reranking. The idea: cosine reranking orders by relevance,
then sine reranking reorders to penalize redundancy and reward diversity.

Strategies:
  1. Anchor    — compare each chunk against the top-1 (highest relevance)
                 chunk; demote chunks with low sine distance to it. O(n).
  2. Iterative — greedily select chunks that maximize sine distance to
                 already-selected set (like MMR with sine kernel). O(k·n).
  3. Centroid  — compare each chunk against the running centroid of
                 selected chunks; pick the most orthogonal next. O(k·n).

Baseline: cosine cross-encoder reranking only (current `precise` path).

Metrics:
  - Standard retrieval: MRR, nDCG@5, Hit Rate@5, Precision@5
  - Diversity: Intra-List Diversity (ILD) = mean pairwise cosine distance
  - Latency: wall-clock time per query (ms)

Usage:
  python scripts/benchmark_sine_rerank.py [--output PATH]
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
from typing import List, Dict, Tuple, Callable

os.environ["CANDLEKEEP_DEVICE"] = "cpu"

sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np

from candlekeep.config import Settings
from candlekeep.database.interface import SearchResult, Chunk
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.reranker import rerank_results
from candlekeep.eval.metrics import (
    calculate_reciprocal_rank,
    calculate_ndcg,
    calculate_hit_rate,
    calculate_precision_at_k,
)
from candlekeep.eval.statistics import bootstrap_ci


# ── Sine-distance reranking strategies ───────────────────────────────


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _sine_dist(a: np.ndarray, b: np.ndarray) -> float:
    """Sine distance: measures orthogonality between two vectors.

    sin(θ) = √(1 - cos²(θ))
    Returns 0.0 for identical vectors, 1.0 for orthogonal vectors.
    """
    cos = _cosine_sim(a, b)
    # Clamp to avoid sqrt of negative due to floating point
    return float(np.sqrt(max(0.0, 1.0 - cos * cos)))


def sine_rerank_anchor(
    results: List[SearchResult],
    embeddings: List[np.ndarray],
    top_k: int = 5,
) -> List[SearchResult]:
    """Strategy 1: Anchor — compare all chunks against the top-1 chunk.

    Score = original_relevance * sine_distance_to_anchor.
    Chunks identical to the anchor get demoted (sine ≈ 0).
    The anchor itself is always included first.

    Complexity: O(n) sine computations.
    """
    if len(results) <= 1:
        return results[:top_k]

    anchor_emb = embeddings[0]
    scored = [(results[0], 1.0)]  # anchor always first

    for i in range(1, len(results)):
        sd = _sine_dist(anchor_emb, embeddings[i])
        # Blend: keep relevance ordering but penalize near-duplicates of anchor
        # Using geometric mean to balance both signals
        relevance_norm = results[i].score / results[0].score if results[0].score != 0 else 0
        blended = np.sqrt(max(0, relevance_norm) * sd)
        scored.append((results[i], blended))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [r for r, _ in scored[:top_k]]


def sine_rerank_iterative(
    results: List[SearchResult],
    embeddings: List[np.ndarray],
    top_k: int = 5,
    lambda_: float = 0.5,
) -> List[SearchResult]:
    """Strategy 2: Iterative — greedily select for max diversity.

    At each step, pick the candidate that maximizes:
        λ · normalized_relevance + (1 - λ) · min_sine_distance_to_selected

    Similar to MMR but using sine distance as the diversity kernel.

    Complexity: O(k · n) sine computations.
    """
    if len(results) <= 1:
        return results[:top_k]

    n = len(results)
    selected_indices: List[int] = [0]  # start with highest relevance
    remaining = set(range(1, n))

    max_score = results[0].score if results[0].score != 0 else 1.0

    while len(selected_indices) < top_k and remaining:
        best_idx = -1
        best_combined = -1.0

        for idx in remaining:
            # Relevance component (normalized to [0, 1])
            rel = results[idx].score / max_score if max_score != 0 else 0

            # Diversity component: min sine distance to any selected chunk
            min_sd = min(
                _sine_dist(embeddings[idx], embeddings[s])
                for s in selected_indices
            )

            combined = lambda_ * rel + (1 - lambda_) * min_sd
            if combined > best_combined:
                best_combined = combined
                best_idx = idx

        if best_idx >= 0:
            selected_indices.append(best_idx)
            remaining.discard(best_idx)
        else:
            break

    return [results[i] for i in selected_indices]


def sine_rerank_centroid(
    results: List[SearchResult],
    embeddings: List[np.ndarray],
    top_k: int = 5,
    lambda_: float = 0.5,
) -> List[SearchResult]:
    """Strategy 3: Centroid — compare against running centroid of selected set.

    At each step, pick the candidate that maximizes:
        λ · normalized_relevance + (1 - λ) · sine_distance_to_centroid

    The centroid is the mean embedding of all selected chunks so far.

    Complexity: O(k · n) sine computations + O(k · d) centroid updates.
    """
    if len(results) <= 1:
        return results[:top_k]

    n = len(results)
    dim = len(embeddings[0])
    selected_indices: List[int] = [0]
    centroid = np.array(embeddings[0], dtype=np.float64)
    remaining = set(range(1, n))

    max_score = results[0].score if results[0].score != 0 else 1.0

    while len(selected_indices) < top_k and remaining:
        best_idx = -1
        best_combined = -1.0

        for idx in remaining:
            rel = results[idx].score / max_score if max_score != 0 else 0
            sd = _sine_dist(centroid, embeddings[idx])
            combined = lambda_ * rel + (1 - lambda_) * sd

            if combined > best_combined:
                best_combined = combined
                best_idx = idx

        if best_idx >= 0:
            selected_indices.append(best_idx)
            remaining.discard(best_idx)
            # Update centroid incrementally
            k = len(selected_indices)
            centroid = centroid * ((k - 1) / k) + np.array(embeddings[best_idx]) / k
        else:
            break

    return [results[i] for i in selected_indices]


# ── Diversity metric ─────────────────────────────────────────────────


def intra_list_diversity(embeddings: List[np.ndarray]) -> float:
    """Mean pairwise cosine distance within a result set.

    ILD = 1 means all results are orthogonal (max diversity).
    ILD = 0 means all results are identical (no diversity).
    """
    n = len(embeddings)
    if n < 2:
        return 0.0
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1.0 - _cosine_sim(embeddings[i], embeddings[j])
            count += 1
    return total / count if count > 0 else 0.0


# ── Local vector store (copied from benchmark_advanced_vs_basic.py) ──

import chromadb
from candlekeep.database.embeddings import EmbeddingManager


class LocalVectorStore:
    """Minimal local ChromaDB store for benchmarking (no server dependency)."""

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

        def _gen_id(c: Chunk) -> str:
            content = f"{c.metadata['source']}:{c.chunk_index}:{c.text[:100]}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

        ids = [_gen_id(c) for c in chunks]
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        metadatas = [{**c.metadata, "chunk_index": c.chunk_index} for c in chunks]
        self.collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        return len(chunks)

    def search(self, query: str, n_results: int = 5, category: str | None = None) -> List[SearchResult]:
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
        candidates = [r for r in candidates if r.metadata.get("filename", "") not in excluded]

        query_terms = set(query.lower().split())
        for r in candidates:
            boost = 0
            title = r.metadata.get("title", "").lower()
            title_matches = sum(1 for t in query_terms if t in title)
            if title_matches:
                boost += min(title_matches * 0.2, 0.6)
            desc = r.metadata.get("description", "").lower()
            if sum(1 for t in query_terms if t in desc):
                boost += 0.3
            kw = r.metadata.get("keywords", "").lower()
            if sum(1 for t in query_terms if t in kw):
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
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_all_chunks(self) -> List[SearchResult]:
        results = self.collection.get()
        if not results["ids"]:
            return []
        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        emb = self.embedder.embed(texts)
        return emb.tolist() if hasattr(emb, "tolist") else emb

    def get_stored_embeddings_by_source(self, source: str) -> Dict[int, List[float]]:
        results = self.collection.get(where={"source": source}, include=["embeddings", "metadatas"])
        if not results["ids"]:
            return {}
        return {
            meta.get("chunk_index", 0): emb
            for meta, emb in zip(results["metadatas"], results["embeddings"])
        }


# ── Data structures ──────────────────────────────────────────────────


@dataclass
class QuerySpec:
    query: str
    expected_sources: List[str]
    category: str
    difficulty: str


@dataclass
class PerQueryResult:
    query: str
    difficulty: str
    mrr: float
    ndcg_5: float
    hit_rate_5: float
    precision_5: float
    ild: float
    latency_ms: float
    e2e_latency_ms: float
    sine_computations: int


@dataclass
class PipelineSummary:
    label: str
    mrr: float
    mrr_ci: Tuple[float, float]
    ndcg_5: float
    hit_rate_5: float
    precision_5: float
    ild: float
    ild_ci: Tuple[float, float]
    avg_latency_ms: float
    avg_e2e_latency_ms: float
    avg_sine_computations: float
    n_queries: int
    by_difficulty: Dict[str, Dict[str, float]]


# ── Evaluation core ──────────────────────────────────────────────────


def load_eval_suite(fixtures_dir: Path) -> List[QuerySpec]:
    suite_path = fixtures_dir / "eval_suite_100.json"
    if suite_path.exists():
        with open(suite_path) as f:
            data = json.load(f)
        return [
            QuerySpec(
                query=q["query"],
                expected_sources=q["expected_sources"],
                category=q["category"],
                difficulty=q["difficulty"],
            )
            for q in data["queries"]
        ]

    from tests.benchmark_queries import BENCHMARK_QUERIES
    return [
        QuerySpec(
            query=q.query,
            expected_sources=q.expected_sources,
            category=q.category or "core",
            difficulty=q.difficulty,
        )
        for q in BENCHMARK_QUERIES
    ]


def _get_result_embeddings(store: LocalVectorStore, results: List[SearchResult]) -> List[np.ndarray]:
    """Get embeddings for a list of search results."""
    if not results:
        return []
    texts = [r.text for r in results]
    embs = store.get_embeddings(texts)
    return [np.array(e) for e in embs]


def evaluate_strategy(
    store: LocalVectorStore,
    queries: List[QuerySpec],
    strategy_fn: Callable,
    strategy_label: str,
    k: int = 5,
    candidate_pool: int = 15,
    retrieval_path: str = "precise",
) -> List[PerQueryResult]:
    """Run a sine-reranking strategy across all queries.

    retrieval_path controls the pre-sine pipeline:
      precise: Arcane Recall → cross-encoder rerank
      simple:  Arcane Recall only (bi-encoder scores)
      hybrid:  BM25 + Vector + RRF + Arcane Recall
    """
    from candlekeep.rag.arcane_recall import search_with_arcane_recall
    from candlekeep.rag.search import preprocess_negation

    device = getattr(store, "settings", None)
    device = device.device if device else "cpu"

    results_list = []
    for q in queries:
        processed = preprocess_negation(q.query)

        e2e_start = time.time()

        if retrieval_path == "hybrid":
            from candlekeep.rag.hybrid import hybrid_search
            candidates = hybrid_search(store, processed, n_results=candidate_pool)
            ranked = candidates
        else:
            # Step 1: Arcane Recall
            candidates = search_with_arcane_recall(store, processed, n_results=candidate_pool)
            # Step 2: optional cross-encoder rerank
            if retrieval_path == "precise":
                ranked = rerank_results(processed, candidates, top_k=candidate_pool, device=device)
            else:
                ranked = candidates

        # Get embeddings for the ranked candidates
        embeddings = _get_result_embeddings(store, ranked)

        # Step 3: Sine diversity rerank (timed separately)
        sine_start = time.time()
        if strategy_fn is None:
            final = ranked[:k]
            sine_ops = 0
        else:
            final, sine_ops = strategy_fn(ranked, embeddings, k)
        rerank_latency = (time.time() - sine_start) * 1000
        e2e_latency = (time.time() - e2e_start) * 1000

        # Get embeddings for final set (for ILD)
        final_embeddings = _get_result_embeddings(store, final)

        # Compute metrics
        retrieved = []
        for r in final:
            src = r.metadata.get("source", "")
            if "tests/fixtures" in src:
                src = src[src.index("tests/fixtures"):]
            retrieved.append(src)

        gt = set(q.expected_sources)
        results_list.append(PerQueryResult(
            query=q.query,
            difficulty=q.difficulty,
            mrr=calculate_reciprocal_rank(retrieved, gt),
            ndcg_5=calculate_ndcg(retrieved, gt, k),
            hit_rate_5=calculate_hit_rate(retrieved, gt, k),
            precision_5=calculate_precision_at_k(retrieved, gt, k),
            ild=intra_list_diversity(final_embeddings),
            latency_ms=rerank_latency,
            e2e_latency_ms=e2e_latency,
            sine_computations=sine_ops,
        ))

    return results_list


def summarize(label: str, results: List[PerQueryResult]) -> PipelineSummary:
    mrr_vals = [r.mrr for r in results]
    ild_vals = [r.ild for r in results]
    mrr_mean, mrr_lo, mrr_hi = bootstrap_ci(mrr_vals)
    ild_mean, ild_lo, ild_hi = bootstrap_ci(ild_vals)

    by_diff: Dict[str, Dict[str, float]] = {}
    for diff in ("easy", "medium", "hard"):
        sub = [r for r in results if r.difficulty == diff]
        if sub:
            by_diff[diff] = {
                "mrr": float(np.mean([r.mrr for r in sub])),
                "ndcg_5": float(np.mean([r.ndcg_5 for r in sub])),
                "hit_rate_5": float(np.mean([r.hit_rate_5 for r in sub])),
                "ild": float(np.mean([r.ild for r in sub])),
                "count": len(sub),
            }

    return PipelineSummary(
        label=label,
        mrr=mrr_mean,
        mrr_ci=(mrr_lo, mrr_hi),
        ndcg_5=float(np.mean([r.ndcg_5 for r in results])),
        hit_rate_5=float(np.mean([r.hit_rate_5 for r in results])),
        precision_5=float(np.mean([r.precision_5 for r in results])),
        ild=ild_mean,
        ild_ci=(ild_lo, ild_hi),
        avg_latency_ms=float(np.mean([r.latency_ms for r in results])),
        avg_e2e_latency_ms=float(np.mean([r.e2e_latency_ms for r in results])),
        avg_sine_computations=float(np.mean([r.sine_computations for r in results])),
        n_queries=len(results),
        by_difficulty=by_diff,
    )


# ── Strategy wrappers ────────────────────────────────────────────────


def _wrap_anchor(results, embeddings, k):
    ops = max(0, len(results) - 1)
    return sine_rerank_anchor(results, embeddings, top_k=k), ops


def _make_iterative_wrapper(lam):
    def _wrap(results, embeddings, k):
        n = len(results)
        ops = k * (n - 1) - k * (k - 1) // 2 if n > 1 else 0
        return sine_rerank_iterative(results, embeddings, top_k=k, lambda_=lam), ops
    return _wrap


def _make_centroid_wrapper(lam):
    def _wrap(results, embeddings, k):
        n = len(results)
        ops = k * (n - 1) - k * (k - 1) // 2 if n > 1 else 0
        return sine_rerank_centroid(results, embeddings, top_k=k, lambda_=lam), ops
    return _wrap


# ── Reporting ────────────────────────────────────────────────────────


def print_comparison(summaries: List[PipelineSummary]):
    hdr = (
        f"{'Strategy':<20} {'MRR':>7} {'nDCG@5':>7} {'HR@5':>7} "
        f"{'P@5':>7} {'ILD':>7} {'Sine(ms)':>8} {'E2E(ms)':>8}"
    )
    print(hdr)
    print("─" * len(hdr))
    for s in summaries:
        print(
            f"{s.label:<20} {s.mrr:>7.4f} {s.ndcg_5:>7.4f} {s.hit_rate_5:>7.4f} "
            f"{s.precision_5:>7.4f} {s.ild:>7.4f} {s.avg_latency_ms:>8.2f} "
            f"{s.avg_e2e_latency_ms:>8.1f}"
        )


def print_diversity_vs_relevance(summaries: List[PipelineSummary]):
    baseline = summaries[0]
    print(f"\n  {'Strategy':<20} {'ΔMRR':>8} {'ΔILD':>8} {'Tradeoff':>10}")
    print("  " + "─" * 48)
    for s in summaries[1:]:
        d_mrr = s.mrr - baseline.mrr
        d_ild = s.ild - baseline.ild
        ratio = d_ild / abs(d_mrr) if d_mrr != 0 else float("inf")
        print(f"  {s.label:<20} {d_mrr:>+8.4f} {d_ild:>+8.4f} {ratio:>10.2f}")
    print("  (Tradeoff = ΔILD / |ΔMRR|; higher = more diversity per unit relevance lost)")


def print_difficulty_breakdown(summaries: List[PipelineSummary]):
    for diff in ("easy", "medium", "hard"):
        print(f"\n  {diff.upper()}")
        print(f"  {'Strategy':<20} {'MRR':>7} {'ILD':>7}")
        print("  " + "─" * 36)
        for s in summaries:
            d = s.by_difficulty.get(diff, {})
            print(f"  {s.label:<20} {d.get('mrr', 0):>7.4f} {d.get('ild', 0):>7.4f}")


# ── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Benchmark sine-distance diversity reranking")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--lambda", type=float, default=None, dest="lambda_",
                        help="Single λ value. Omit to sweep [0.2, 0.3, 0.5, 0.7]")
    parser.add_argument("--pool", type=int, default=15,
                        help="Candidate pool size fed to cross-encoder (default: 15)")
    parser.add_argument("--corpus", choices=["standard", "redundant"], default="standard",
                        help="Corpus to benchmark against (default: standard)")
    parser.add_argument("--path", choices=["precise", "simple", "hybrid"], default="precise",
                        help="Retrieval path to test (default: precise)")
    args = parser.parse_args()

    lambda_values = [args.lambda_] if args.lambda_ is not None else [0.2, 0.3, 0.5, 0.7]
    ret_path = args.path

    print("🔬 Sine-Distance Diversity Reranking Benchmark")
    print(f"   Corpus: {args.corpus}")
    print(f"   Path: {ret_path}")
    print(f"   λ values: {lambda_values}")
    print(f"   Candidate pool = {args.pool}")
    print()

    temp_dir = tempfile.mkdtemp(prefix="candlekeep_sine_bench_")
    try:
        settings = Settings.from_env()
        store = LocalVectorStore(temp_dir, settings)
        processor = DocumentProcessor(settings)

        # Seed corpus
        print("📦 Seeding corpus...")
        fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
        doc_count = 0
        if args.corpus == "redundant":
            corpus_dir = fixtures / "redundant_docs"
            for doc in corpus_dir.glob("*.md"):
                chunks = processor.process(str(doc))
                store.add_documents(chunks)
                doc_count += 1
        else:
            for subdir in ("sample_docs", "scale_docs"):
                docs_dir = fixtures / subdir
                if docs_dir.exists():
                    for doc in docs_dir.glob("*"):
                        if doc.is_file():
                            chunks = processor.process(str(doc))
                            store.add_documents(chunks)
                            doc_count += 1
        print(f"   {doc_count} documents ingested\n")

        # Load queries
        if args.corpus == "redundant":
            queries_path = fixtures / "redundant_docs" / "eval_queries.json"
            with open(queries_path) as f:
                data = json.load(f)
            queries = [
                QuerySpec(
                    query=q["query"],
                    expected_sources=q["expected_sources"],
                    category=q.get("category", "auth"),
                    difficulty=q["difficulty"],
                )
                for q in data["queries"]
            ]
        else:
            queries = load_eval_suite(fixtures)
        print(f"📋 {len(queries)} evaluation queries loaded\n")

        if ret_path == "precise":
            print("🔥 Warming up cross-encoder...")
            from candlekeep.rag.reranker import warm_up
            warm_up(device=settings.device)
            print()

        # ── Phase 1: λ sweep at k=5 ─────────────────────────────────
        all_summaries = {}
        all_results = {}

        for lam in lambda_values:
            print(f"\n{'='*72}")
            print(f"λ = {lam}")
            print(f"{'='*72}")

            strategies: List[Tuple[str, Callable | None]] = [
                ("baseline-k5", None),
                ("sine-anchor", _wrap_anchor),
                ("sine-iter", _make_iterative_wrapper(lam)),
                ("sine-centroid", _make_centroid_wrapper(lam)),
            ]

            summaries = []
            for label, fn in strategies:
                print(f"  ⏱  {label}...", end=" ", flush=True)
                results = evaluate_strategy(
                    store, queries, fn, label,
                    k=5, candidate_pool=args.pool,
                    retrieval_path=ret_path,
                )
                s = summarize(label, results)
                summaries.append(s)
                all_results[f"λ{lam}_{label}"] = results
                print(f"MRR={s.mrr:.4f} ILD={s.ild:.4f}")

            all_summaries[lam] = summaries
            print()
            print_comparison(summaries)
            print_diversity_vs_relevance(summaries)

        # ── Phase 2: Context efficiency ──────────────────────────────
        best_lam = lambda_values[0]
        print(f"\n{'='*72}")
        print(f"CONTEXT EFFICIENCY: sine@k=3 vs baseline@k=5  (λ={best_lam})")
        print(f"{'='*72}")

        ctx_configs = [
            ("baseline-k5", None, 5),
            ("baseline-k3", None, 3),
            ("sine-iter-k3", _make_iterative_wrapper(best_lam), 3),
            ("sine-cent-k3", _make_centroid_wrapper(best_lam), 3),
        ]

        ctx_summaries = []
        for label, fn, k in ctx_configs:
            print(f"  ⏱  {label}...", end=" ", flush=True)
            results = evaluate_strategy(
                store, queries, fn, label,
                k=k, candidate_pool=args.pool,
                retrieval_path=ret_path,
            )
            s = summarize(label, results)
            ctx_summaries.append(s)
            all_results[f"ctx_{label}"] = results
            print(f"MRR={s.mrr:.4f} HR={s.hit_rate_5:.4f} ILD={s.ild:.4f}")

        print()
        print_comparison(ctx_summaries)

        base5 = ctx_summaries[0]
        print(f"\n  vs baseline@k=5 (MRR={base5.mrr:.4f}, HR={base5.hit_rate_5:.4f}):")
        print(f"  {'Strategy':<20} {'ΔMRR':>8} {'ΔHR':>8} {'Context':>10}")
        print("  " + "─" * 48)
        for s in ctx_summaries[1:]:
            ctx_pct = "60%" if "k3" in s.label else "100%"
            print(f"  {s.label:<20} {s.mrr - base5.mrr:>+8.4f} "
                  f"{s.hit_rate_5 - base5.hit_rate_5:>+8.4f} {ctx_pct:>10}")

        # ── λ sweep summary ──────────────────────────────────────────
        if len(lambda_values) > 1:
            baseline_mrr = all_summaries[lambda_values[0]][0].mrr
            baseline_ild = all_summaries[lambda_values[0]][0].ild

            print(f"\n{'='*72}")
            print("λ SWEEP SUMMARY")
            print(f"{'='*72}")
            for strat_name, strat_idx in [("iterative", 2), ("centroid", 3)]:
                print(f"\n  {strat_name}:")
                print(f"  {'λ':>5} {'MRR':>8} {'ILD':>8} {'ΔMRR':>8} {'ΔILD':>8}")
                print("  " + "─" * 40)
                for lam in lambda_values:
                    s = all_summaries[lam][strat_idx]
                    print(f"  {lam:>5.1f} {s.mrr:>8.4f} {s.ild:>8.4f} "
                          f"{s.mrr - baseline_mrr:>+8.4f} {s.ild - baseline_ild:>+8.4f}")

        print_difficulty_breakdown(all_summaries[best_lam])

        # Save
        output = args.output
        if not output:
            results_dir = Path(__file__).parent.parent / "tests" / "results"
            results_dir.mkdir(exist_ok=True)
            ce_suffix = f"_{ret_path}" if ret_path != "precise" else ""
            corpus_suffix = f"_{args.corpus}" if args.corpus != "standard" else ""
            output = str(results_dir / f"sine_rerank_benchmark{corpus_suffix}{ce_suffix}.json")

        report = {}
        for key, results in all_results.items():
            s = summarize(key, results)
            report[key] = {"summary": asdict(s), "details": [asdict(r) for r in results]}
        Path(output).write_text(json.dumps(report, indent=2, default=float))
        print(f"\n💾 Report saved to {output}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
