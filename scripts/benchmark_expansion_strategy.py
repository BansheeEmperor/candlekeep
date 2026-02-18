#!/usr/bin/env python3
"""Benchmark expansion strategies: directional break vs no-break vs skip-ahead.

Compares three expansion strategies:
  - "current": ±2 with directional break (stop when neighbor fails similarity)
  - "no_break": ±2 with similarity check per offset, no break on failure
  - "skip_135": check offsets ±1, ±3, ±5 with similarity check, no break

Runs against original software corpus and alternating-section corpus.

Usage:
    python scripts/benchmark_expansion_strategy.py
"""
import sys
import os
import json
import time
import tempfile
import shutil
from pathlib import Path
from typing import List

os.environ["CANDLEKEEP_DEVICE"] = "cpu"
sys.path.append(str(Path(__file__).parent.parent / "src"))

import chromadb
import numpy as np
from candlekeep.config import Settings
from candlekeep.database.embeddings import EmbeddingManager
from candlekeep.database.interface import SearchResult
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.arcane_recall import calculate_cosine_similarity
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery
import candlekeep.rag.arcane_recall as ar


# ── Isolated store ───────────────────────────────────────────────────

class IsolatedStore:
    def __init__(self, settings, temp_dir):
        self.settings = settings
        self.embedder = EmbeddingManager.get_instance(settings)
        self.client = chromadb.PersistentClient(path=temp_dir)
        self.collection = self.client.get_or_create_collection(
            name="candlekeep",
            metadata={"hnsw:space": "cosine", "embedding_model": settings.embedding_model},
        )
        self._query_count = 0

    def search(self, query, n_results=5, category=None):
        embedding = self.embedder.embed_query(query)
        results = self.collection.query(
            query_embeddings=[embedding], n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0],
            ):
                out.append(SearchResult(
                    text=doc, metadata=meta, score=1.0 - dist,
                    doc_id=meta.get("source", ""),
                ))
        self._query_count += 1
        return out

    def add_documents(self, chunks, collection=None):
        texts = [c.text for c in chunks]
        metadatas = [{**c.metadata, "chunk_index": c.chunk_index} for c in chunks]
        ids = [f"{c.metadata.get('source', 'unknown')}_{c.chunk_index}" for c in chunks]
        embeddings = self.embedder.embed(texts)
        if hasattr(embeddings, 'tolist'):
            embeddings = embeddings.tolist()
        for start in range(0, len(texts), 500):
            end = start + 500
            self.collection.add(
                documents=texts[start:end], metadatas=metadatas[start:end],
                ids=ids[start:end], embeddings=embeddings[start:end],
            )
        return len(texts)

    def get_chunks_by_source(self, source):
        results = self.collection.get(where={"source": source}, include=["documents", "metadatas"])
        return [SearchResult(text=doc, metadata=meta, score=0.0, doc_id=meta.get("source", ""))
                for doc, meta in zip(results["documents"], results["metadatas"])]

    def get_stored_embeddings_by_source(self, source):
        results = self.collection.get(where={"source": source}, include=["embeddings", "metadatas"])
        return {meta.get("chunk_index", 0): emb
                for meta, emb in zip(results["metadatas"], results["embeddings"])}

    def get_embeddings(self, texts):
        embeddings = self.embedder.embed(texts)
        if hasattr(embeddings, 'tolist'):
            return embeddings.tolist()
        return embeddings

    def get_stats(self):
        return {"total_chunks": self.collection.count()}


# ── Custom expand_results with configurable strategy ─────────────────

def expand_results_custom(
    db, results, n_results=5, expansion_chunks=2, query=None,
    strategy="current", offsets=None,
):
    """expand_results with configurable expansion strategy.

    strategy:
      - "current": break on first similarity failure per direction
      - "no_break": check all offsets within ±expansion_chunks, skip failures
      - "skip_offsets": check specific offsets (given in `offsets` list)
    """
    if not results:
        return []

    results_by_source = {}
    for r in results:
        source = r.metadata.get("source", "")
        if source:
            results_by_source.setdefault(source, []).append(r)

    chunks_by_source = {}
    stored_embeddings_by_source = {}
    for source in results_by_source:
        source_chunks = db.get_chunks_by_source(source)
        chunks_by_source[source] = {
            c.metadata.get("chunk_index", 0): c for c in source_chunks
        }
        stored_embeddings_by_source[source] = db.get_stored_embeddings_by_source(source)

    query_embedding = None
    if query:
        query_embedding = db.get_embeddings([query])[0]

    all_windows = []

    for source, source_results in results_by_source.items():
        doc_chunks = chunks_by_source[source]
        doc_embeddings = stored_embeddings_by_source.get(source, {})

        source_windows = []
        for res in source_results:
            idx = res.metadata.get("chunk_index", 0)
            current_window = {idx}

            if strategy == "skip_offsets" and offsets:
                # Check specific offsets in both directions
                for offset in offsets:
                    for direction in [-1, 1]:
                        check_idx = idx + (offset * direction)
                        if check_idx >= 0 and check_idx in doc_chunks:
                            if _check_similarity(
                                doc_chunks[idx], doc_chunks[check_idx],
                                query_embedding, doc_embeddings.get(idx),
                                doc_embeddings.get(check_idx),
                            ):
                                current_window.add(check_idx)
            else:
                # ±expansion_chunks with or without break
                for direction in [-1, 1]:
                    for offset in range(1, expansion_chunks + 1):
                        check_idx = idx + (offset * direction)
                        if check_idx >= 0 and check_idx in doc_chunks:
                            if _check_similarity(
                                doc_chunks[idx], doc_chunks[check_idx],
                                query_embedding, doc_embeddings.get(idx),
                                doc_embeddings.get(check_idx),
                            ):
                                current_window.add(check_idx)
                            elif strategy == "current":
                                break  # Stop in this direction
                            # "no_break": continue checking next offset

            source_windows.append((sorted(list(current_window)), res.score, res.metadata))

        # Merge overlapping windows
        if source_windows:
            source_windows.sort(key=lambda x: x[0][0])
            curr_indices, curr_score, curr_meta = source_windows[0]
            for next_indices, next_score, next_meta in source_windows[1:]:
                if next_indices[0] <= curr_indices[-1] + 1:
                    combined = sorted(list(set(curr_indices) | set(next_indices)))
                    curr_indices = combined
                    curr_score = max(curr_score, next_score)
                else:
                    all_windows.append((curr_indices, curr_score, curr_meta, source))
                    curr_indices, curr_score, curr_meta = next_indices, next_score, next_meta
            all_windows.append((curr_indices, curr_score, curr_meta, source))

    all_windows.sort(key=lambda x: x[1], reverse=True)

    expanded = []
    seen_texts = set()
    for indices, score, meta, source in all_windows:
        if len(expanded) >= n_results:
            break
        doc_chunks = chunks_by_source.get(source, {})
        context_parts = [doc_chunks[i].text for i in indices if i in doc_chunks]
        expanded_text = "\n\n".join(context_parts)
        if expanded_text in seen_texts:
            continue
        seen_texts.add(expanded_text)
        expanded.append(SearchResult(
            text=expanded_text, score=score, metadata=meta.copy(), doc_id=source,
        ))

    return expanded


def _check_similarity(match_chunk, neighbor_chunk, query_embedding,
                       match_embedding, neighbor_embedding):
    """Similarity check with continuation marker support."""
    text = neighbor_chunk.text.strip()
    if text.startswith(("- ", "* ", "+ ", "> ", "  ")):
        return True
    if (query_embedding is not None and match_embedding is not None
            and neighbor_embedding is not None):
        match_sim = calculate_cosine_similarity(query_embedding, match_embedding)
        neighbor_sim = calculate_cosine_similarity(query_embedding, neighbor_embedding)
        return neighbor_sim >= (match_sim * 0.92)
    return True


# ── Corpus configs ──────────────────────────────────────────────────

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"

CORPORA = {
    "original": {
        "doc_dirs": [FIXTURES / "sample_docs", FIXTURES / "scale_docs"],
        "eval_suite": FIXTURES / "eval_suite_100.json",
    },
    "alternating": {
        "doc_dirs": [FIXTURES / "cross_domain" / "alternating_docs"],
        "eval_suite": FIXTURES / "cross_domain" / "eval_suite_alternating.json",
    },
}

STRATEGIES = {
    "current":    {"strategy": "current", "expansion_chunks": 2, "offsets": None},
    "no_break":   {"strategy": "no_break", "expansion_chunks": 2, "offsets": None},
    "skip_135":   {"strategy": "skip_offsets", "expansion_chunks": 5, "offsets": [1, 3, 5]},
}


def load_queries(suite_path):
    with open(suite_path) as f:
        data = json.load(f)
    return [
        EvalQuery(query=q["query"], expected_sources=q["expected_sources"],
                  category=q["category"], difficulty=q.get("difficulty", "medium"))
        for q in data["queries"]
    ]


def ingest_corpus(store, processor, doc_dirs):
    total = 0
    for doc_dir in doc_dirs:
        for doc_path in sorted(doc_dir.glob("*")):
            if doc_path.is_file():
                try:
                    chunks = processor.process(str(doc_path))
                    store.add_documents(chunks)
                    total += len(chunks)
                except Exception:
                    continue
    return total


def run_eval(store, queries, strategy_config):
    def search_fn(query, k):
        raw = store.search(query, n_results=k * 2)
        return expand_results_custom(
            store, raw, n_results=k, query=query,
            expansion_chunks=strategy_config["expansion_chunks"],
            strategy=strategy_config["strategy"],
            offsets=strategy_config["offsets"],
        )
    runner = BenchmarkRunner(search_fn)
    results = runner.run_suite(queries, k=5)
    return runner.summarize(results)


def main():
    RESULTS_DIR = Path(__file__).parent.parent / "tests" / "results"
    RESULTS_DIR.mkdir(exist_ok=True)
    all_results = {}

    for corpus_name, config in CORPORA.items():
        queries = load_queries(config["eval_suite"])
        print(f"\n{'='*60}")
        print(f"Corpus: {corpus_name} ({len(queries)} queries)")
        print(f"{'='*60}", flush=True)

        for strat_name, strat_config in STRATEGIES.items():
            temp_dir = tempfile.mkdtemp(prefix=f"p2_{corpus_name}_{strat_name}_")
            settings = Settings.from_env()
            store = IsolatedStore(settings, temp_dir)
            processor = DocumentProcessor(settings)

            try:
                chunks = ingest_corpus(store, processor, config["doc_dirs"])
                print(f"\n  [{strat_name}] {chunks} chunks ingested", flush=True)

                start = time.time()
                summary = run_eval(store, queries, strat_config)
                elapsed = time.time() - start

                key = f"{corpus_name}_{strat_name}"
                all_results[key] = {
                    "corpus": corpus_name,
                    "strategy": strat_name,
                    "chunks": chunks,
                    "queries": len(queries),
                    "mrr": summary["mrr"],
                    "ndcg_5": summary["avg_ndcg_5"],
                    "hit_rate_5": summary["avg_hit_rate_5"],
                    "avg_latency_ms": summary["avg_latency_ms"],
                    "avg_tokens": summary["avg_tokens"],
                    "elapsed_s": round(elapsed, 1),
                }

                print(f"  [{strat_name}] MRR={summary['mrr']:.4f} | "
                      f"nDCG={summary['avg_ndcg_5']:.4f} | "
                      f"HR@5={summary['avg_hit_rate_5']:.4f} | "
                      f"latency={summary['avg_latency_ms']:.0f}ms | "
                      f"tokens={summary['avg_tokens']:.0f} | "
                      f"({elapsed:.1f}s)", flush=True)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"{'Corpus':>14} | {'Strategy':>10} | {'MRR':>7} | {'nDCG@5':>7} | "
          f"{'HR@5':>7} | {'Latency':>8} | {'Tokens':>7}")
    print("-" * 82)
    for key, r in all_results.items():
        print(f"{r['corpus']:>14} | {r['strategy']:>10} | {r['mrr']:>7.4f} | "
              f"{r['ndcg_5']:>7.4f} | {r['hit_rate_5']:>7.4f} | "
              f"{r['avg_latency_ms']:>6.0f}ms | {r['avg_tokens']:>7.0f}")

    # Deltas vs current
    print(f"\n{'='*70}")
    print("DELTA vs current")
    print(f"{'='*70}")
    for corpus_name in CORPORA:
        curr = all_results.get(f"{corpus_name}_current", {})
        for strat_name in ["no_break", "skip_135"]:
            other = all_results.get(f"{corpus_name}_{strat_name}", {})
            if curr and other:
                print(f"  {corpus_name} / {strat_name}:")
                print(f"    MRR:     {other['mrr'] - curr['mrr']:+.4f}")
                print(f"    nDCG@5:  {other['ndcg_5'] - curr['ndcg_5']:+.4f}")
                print(f"    HR@5:    {other['hit_rate_5'] - curr['hit_rate_5']:+.4f}")
                print(f"    Latency: {other['avg_latency_ms'] - curr['avg_latency_ms']:+.0f}ms")
                print(f"    Tokens:  {other['avg_tokens'] - curr['avg_tokens']:+.0f}")

    output_path = RESULTS_DIR / "p2_expansion_benchmark.json"
    output_path.write_text(json.dumps(all_results, indent=2))
    print(f"\n✅ Results saved to {output_path}", flush=True)


if __name__ == "__main__":
    main()
