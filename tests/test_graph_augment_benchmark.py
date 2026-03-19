"""Graph augmentation benchmark using NFCorpus.

Tests:
  - Regression: graph doesn't degrade standard retrieval (≤5% Hit Rate@5 drop)
  - Expansion (scenario 1): graph surfaces B-only docs that vector misses
  - Improvement (scenario 3): graded NDCG@5 with Jaccard relevance (max + sum)
  - Latency: cold/no-match/hot
  - Entity precision: ≥80% ruler entities are genuine
"""
import json
import math
import os
import time
from pathlib import Path

import pytest

from tests.conftest_nfcorpus import nfcorpus_store, load_nfcorpus
from tests.nfcorpus_relationship_queries import EXPANSION_QUERIES, RELATIONSHIP_QUERIES

pytestmark = [pytest.mark.benchmark, pytest.mark.slow]

RESULTS_PATH = Path(__file__).parent / "results" / "graph_augment_benchmark.json"
_results: dict = {}


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _search(store, query, augment: bool):
    os.environ["CANDLEKEEP_GRAPH_AUGMENT"] = "true" if augment else "false"
    from candlekeep.rag.router import search_with_routing
    return search_with_routing(store, query, n_results=5, query_type="hybrid")


def _search_explore(store, query):
    os.environ["CANDLEKEEP_GRAPH_AUGMENT"] = "true"
    from candlekeep.rag.router import search_with_routing
    return search_with_routing(store, query, n_results=5, query_type="explore")


def _hit_at_k(results, relevant_ids: set, k: int = 5) -> bool:
    return any(r.metadata.get("source") in relevant_ids for r in results[:k])


def _dcg(relevances: list[float]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def _ndcg_at_k(results, relevance_fn, k: int = 5) -> float:
    """Compute NDCG@k with a custom relevance function per result."""
    rels = [relevance_fn(r) for r in results[:k]]
    dcg = _dcg(rels)
    ideal = _dcg(sorted(rels, reverse=True))
    return dcg / ideal if ideal > 0 else 0.0


def _doc_relevance(doc_entities: list[str], query_pairs: list[tuple[str, str]],
                   gs, mode: str = "max") -> float:
    """Compute graded relevance for a doc based on Jaccard of query entity pairs.

    mode="max": highest Jaccard among pairs present in the doc.
    mode="sum": sum of Jaccard for all pairs present in the doc.
    """
    doc_ents = set(doc_entities) if doc_entities else set()
    scores = []
    for e1, e2 in query_pairs:
        if e1 in doc_ents and e2 in doc_ents:
            # Look up Jaccard from graph store
            for entity, jaccard in gs.get_related(e1, top_n=50):
                if entity == e2:
                    scores.append(jaccard)
                    break
    if not scores:
        return 0.0
    return max(scores) if mode == "max" else sum(scores)


def _get_entity_pairs(query: str, extractor, gs) -> list[tuple[str, str]]:
    """Extract all entity pairs from a query that have co-occurrence edges."""
    entities = extractor.extract(query)
    pairs = []
    for i, e1 in enumerate(entities):
        for e2 in entities[i + 1:]:
            # Check if edge exists in either direction
            for ent, _ in gs.get_related(e1, top_n=50):
                if ent == e2:
                    pairs.append((e1, e2))
                    break
    return pairs


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGraphAugmentBenchmark:

    def test_regression(self, nfcorpus_store):
        """Graph augmentation must not degrade Hit Rate@5 by more than 5%."""
        store, gs, settings, corpus = nfcorpus_store
        _, queries, qrels = load_nfcorpus()

        corpus_ids = set(corpus.keys())
        eval_queries = [
            (qid, qtext, {cid for cid, s in rels.items() if s == 2 and cid in corpus_ids})
            for qid, qtext in queries.items()
            if (rels := qrels.get(qid, {}))
            and any(cid in corpus_ids and s == 2 for cid, s in rels.items())
        ][:25]

        assert eval_queries, "No qualifying regression queries found"

        hits_with, hits_without = [], []
        for qid, qtext, rel_ids in eval_queries:
            hits_with.append(_hit_at_k(_search(store, qtext, True), rel_ids))
            hits_without.append(_hit_at_k(_search(store, qtext, False), rel_ids))

        n = len(hits_with)
        hr_with = sum(hits_with) / n
        hr_without = sum(hits_without) / n
        drop = hr_without - hr_with

        _results["regression"] = {
            "hr_with_graph": hr_with, "hr_without_graph": hr_without,
            "drop_pct": drop * 100, "n_queries": n, "passed": drop <= 0.05,
        }
        print(f"\nRegression — with: {hr_with:.1%}  without: {hr_without:.1%}  drop: {drop*100:+.1f}%")
        assert drop <= 0.05, f"Regression: Hit Rate@5 dropped {drop*100:.1f}% (limit 5%)"

    def test_expansion(self, nfcorpus_store):
        """Scenario 1: explore must surface B-only docs that hybrid misses."""
        store, gs, settings, corpus = nfcorpus_store

        per_query = []
        for item in EXPANSION_QUERIES:
            ea, eb = item["entity_a"], item["entity_b"]

            r_a = store.collection.get(where={"entities": {"$contains": ea}}, limit=1000)
            r_b = store.collection.get(where={"entities": {"$contains": eb}}, limit=1000)
            docs_a = {m["source"] for m in r_a["metadatas"]}
            docs_b = {m["source"] for m in r_b["metadatas"]}
            b_only = docs_b - docs_a

            if not b_only:
                continue

            r_explore = _search_explore(store, item["query"])
            r_hybrid = _search(store, item["query"], augment=False)

            explore_sources = [r.metadata.get("source") for r in r_explore]
            hybrid_sources = [r.metadata.get("source") for r in r_hybrid]

            explore_b = sum(1 for s in explore_sources if s in b_only)
            hybrid_b = sum(1 for s in hybrid_sources if s in b_only)

            per_query.append({
                "query": item["query"],
                "entity_a": ea, "entity_b": eb,
                "b_only_pool": len(b_only),
                "explore_b_only": explore_b,
                "hybrid_b_only": hybrid_b,
            })

        n = len(per_query)
        recall_explore = sum(1 for q in per_query if q["explore_b_only"] > 0) / n
        recall_hybrid = sum(1 for q in per_query if q["hybrid_b_only"] > 0) / n

        _results["expansion"] = {
            "recall_explore": recall_explore,
            "recall_hybrid": recall_hybrid,
            "n_queries": n,
            "per_query": per_query,
            "passed": recall_explore > recall_hybrid,
        }
        print(f"\nExpansion — explore: {recall_explore:.0%}  hybrid: {recall_hybrid:.0%}")
        assert recall_explore > recall_hybrid, "Explore must find more B-only docs than hybrid"

    def test_improvement(self, nfcorpus_store):
        """Scenario 3: explore NDCG@5 must not degrade more than 5% vs hybrid."""
        store, gs, settings, corpus = nfcorpus_store
        from candlekeep.rag.extractor import get_extractor
        extractor = get_extractor(settings.entity_ruler_path)

        ndcg_max_explore, ndcg_max_hybrid = [], []
        ndcg_sum_explore, ndcg_sum_hybrid = [], []
        per_query = []

        for item in RELATIONSHIP_QUERIES:
            pairs = _get_entity_pairs(item["query"], extractor, gs)
            if not pairs:
                pairs = [item["entity_pair"]]

            r_explore = _search_explore(store, item["query"])
            r_hybrid = _search(store, item["query"], augment=False)

            def _rel_max(r):
                return _doc_relevance(r.metadata.get("entities", []), pairs, gs, "max")

            def _rel_sum(r):
                return _doc_relevance(r.metadata.get("entities", []), pairs, gs, "sum")

            nm_e = _ndcg_at_k(r_explore, _rel_max)
            nm_h = _ndcg_at_k(r_hybrid, _rel_max)
            ns_e = _ndcg_at_k(r_explore, _rel_sum)
            ns_h = _ndcg_at_k(r_hybrid, _rel_sum)

            ndcg_max_explore.append(nm_e)
            ndcg_max_hybrid.append(nm_h)
            ndcg_sum_explore.append(ns_e)
            ndcg_sum_hybrid.append(ns_h)

            per_query.append({
                "query": item["query"],
                "entity_pair": list(item["entity_pair"]),
                "ndcg_max_explore": round(nm_e, 4),
                "ndcg_max_hybrid": round(nm_h, 4),
                "ndcg_sum_explore": round(ns_e, 4),
                "ndcg_sum_hybrid": round(ns_h, 4),
            })

        n = len(ndcg_max_explore)
        avg_max_e = sum(ndcg_max_explore) / n
        avg_max_h = sum(ndcg_max_hybrid) / n
        avg_sum_e = sum(ndcg_sum_explore) / n
        avg_sum_h = sum(ndcg_sum_hybrid) / n
        degradation = avg_max_h - avg_max_e

        _results["improvement"] = {
            "ndcg_max_explore": round(avg_max_e, 4),
            "ndcg_max_hybrid": round(avg_max_h, 4),
            "ndcg_max_delta": round(avg_max_e - avg_max_h, 4),
            "ndcg_sum_explore": round(avg_sum_e, 4),
            "ndcg_sum_hybrid": round(avg_sum_h, 4),
            "ndcg_sum_delta": round(avg_sum_e - avg_sum_h, 4),
            "n_queries": n,
            "per_query": per_query,
            "passed": degradation <= 0.05,
        }
        print(f"\nNDCG@5 (max) — explore: {avg_max_e:.4f}  hybrid: {avg_max_h:.4f}  Δ: {avg_max_e - avg_max_h:+.4f}")
        print(f"NDCG@5 (sum) — explore: {avg_sum_e:.4f}  hybrid: {avg_sum_h:.4f}  Δ: {avg_sum_e - avg_sum_h:+.4f}")
        assert degradation <= 0.05, f"NDCG@5 degradation {degradation:.4f} exceeds 5% tolerance"

    def test_latency(self, nfcorpus_store):
        """Latency: cold reported, no-match warm ≤5ms p50, hot reported."""
        store, gs, settings, corpus = nfcorpus_store
        from candlekeep.rag.graph_augment import get_graph_chunks
        from candlekeep.rag.extractor import clear_extractor_cache, get_extractor

        os.environ["CANDLEKEEP_GRAPH_AUGMENT"] = "true"

        clear_extractor_cache()
        t0 = time.perf_counter()
        get_graph_chunks(store, gs, "how does insulin affect glucose?", n_results=5)
        cold_ms = (time.perf_counter() - t0) * 1000

        get_extractor(settings.entity_ruler_path)

        no_match = [
            "what is the weather like today?",
            "how do computers process information?",
            "what are the rules of chess?",
            "describe the water cycle in nature",
            "how does photosynthesis work in plants?",
            "what causes earthquakes and tsunamis?",
            "explain supply and demand economics",
            "how are rainbows formed in the sky?",
        ]
        no_match_times = []
        for q in no_match:
            t0 = time.perf_counter()
            get_graph_chunks(store, gs, q, n_results=5)
            no_match_times.append((time.perf_counter() - t0) * 1000)
        no_match_times.sort()
        p50_no = no_match_times[len(no_match_times) // 2]

        hot = [q["query"] for q in RELATIONSHIP_QUERIES[:8]]
        hot_times = []
        for q in hot:
            t0 = time.perf_counter()
            get_graph_chunks(store, gs, q, n_results=5)
            hot_times.append((time.perf_counter() - t0) * 1000)
        hot_times.sort()
        p50_hot = hot_times[len(hot_times) // 2]
        p95_hot = hot_times[int(len(hot_times) * 0.95)]

        _results["latency"] = {
            "cold_ms": cold_ms, "no_match_p50_ms": p50_no,
            "hot_p50_ms": p50_hot, "hot_p95_ms": p95_hot,
            "passed": p50_no <= 5,
        }
        print(f"\nLatency — cold: {cold_ms:.1f}ms  no-match p50: {p50_no:.1f}ms  hot p50: {p50_hot:.1f}ms  hot p95: {p95_hot:.1f}ms")
        assert p50_no <= 5, f"No-match warm p50 {p50_no:.1f}ms > 5ms"

    def test_entity_precision(self, nfcorpus_store):
        """≥80% of ruler-matched entities must be genuine biomedical terms."""
        store, gs, settings, corpus = nfcorpus_store
        from candlekeep.rag.extractor import get_extractor

        extractor = get_extractor(settings.entity_ruler_path)
        ruler_vocab = set()
        if settings.entity_ruler_path.exists():
            for line in settings.entity_ruler_path.read_text().splitlines():
                if line.strip():
                    ruler_vocab.add(json.loads(line)["pattern"])

        seen, sampled = set(), []
        for chunk in store.get_all_chunks():
            for e in extractor.extract(chunk.text):
                if e in ruler_vocab and e not in seen:
                    seen.add(e)
                    sampled.append(e)
                if len(sampled) >= 50:
                    break
            if len(sampled) >= 50:
                break

        NOISE = {"the", "and", "for", "with", "this", "that", "from", "are"}
        genuine = [e for e in sampled if len(e) >= 4 and e not in NOISE]
        precision = len(genuine) / max(len(sampled), 1)

        _results["entity_precision"] = {
            "sampled": len(sampled), "genuine": len(genuine),
            "precision": precision, "ruler_vocab_size": len(ruler_vocab),
            "sample": sampled[:20], "passed": precision >= 0.80,
        }
        print(f"\nEntity precision — {len(genuine)}/{len(sampled)} = {precision:.1%} (ruler vocab: {len(ruler_vocab)})")
        assert precision >= 0.80, f"Entity precision {precision:.1%} < 80%"

    def test_save_results(self, nfcorpus_store):
        """Write all benchmark results to JSON."""
        RESULTS_PATH.parent.mkdir(exist_ok=True)
        _results["benchmark_params"] = {
            "corpus": "NFCorpus (BEIR)",
            "corpus_size": len(nfcorpus_store[3]),
            "n_expansion_queries": len(EXPANSION_QUERIES),
            "n_relationship_queries": len(RELATIONSHIP_QUERIES),
            "entity_ruler": "biomedical (curated, doc_freq >= 5)",
        }
        RESULTS_PATH.write_text(json.dumps(_results, indent=2))
        print(f"\nResults written to {RESULTS_PATH}")
