#!/usr/bin/env python3
"""Benchmark one fixture corpus in-process, for the 2026-10-19 fixture repair.

Runs the project's BenchmarkRunner (the Centurion metrics) on one suite, against
the fixtures under --root, so the same code can be run on the fixtures before
and after the repair (e.g. a git worktree of the commit before it):

    python scripts/benchmark_fixture_repair.py --root <repo or worktree> --suite CEN --out result.json

Suites: CEN (sample_docs + scale_docs, eval_suite_100.json, overlap 100),
CEN-G (the same corpus at overlap 50, graded nDCG@5 from the graded labels),
CD-ALT, CD-API, CD-LEG, CD-MED, CD-NAR (cross_domain, overlap 100) and PG
(paul_graham, eval_paul_graham.json, overlap 100). Each run ingests the corpus
with DocumentProcessor into a fresh PersistentClient store and runs the hybrid,
precise and explore paths. Model calls are serialised: on MPS, two threads
calling a model at once (the background normalisation rebuild and a query)
abort the process. Run one suite per process: the graph store and the
normalisation map are process-wide singletons.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

SUITES = {
    "CEN": (["sample_docs", "scale_docs"], "eval_suite_100.json", 100),
    "CEN-G": (["sample_docs", "scale_docs"], "eval_suite_100.json", 50),
    "CD-ALT": (["cross_domain/alternating_docs"], "cross_domain/eval_suite_alternating.json", 100),
    "CD-API": (["cross_domain/api_ref_docs"], "cross_domain/eval_suite_api_ref.json", 100),
    "CD-LEG": (["cross_domain/legal_docs"], "cross_domain/eval_suite_legal.json", 100),
    "CD-MED": (["cross_domain/medical_docs"], "cross_domain/eval_suite_medical.json", 100),
    "CD-NAR": (["cross_domain/narrative_docs"], "cross_domain/eval_suite_narrative.json", 100),
    "PG": (["paul_graham"], "eval_paul_graham.json", 100),
}
PATHS = ("hybrid", "precise", "explore")
KEYS = ("mrr", "avg_ndcg_5", "avg_hit_rate_1", "avg_hit_rate_5", "avg_precision_5", "avg_ndcg_5_graded",
        "avg_tokens", "avg_latency_ms")


def serialise_model_calls() -> None:
    from sentence_transformers import CrossEncoder, SentenceTransformer
    lock = threading.RLock()
    for cls, name in ((SentenceTransformer, "encode"), (CrossEncoder, "predict")):
        fn = getattr(cls, name)

        def wrapper(*a, _fn=fn, **kw):
            with lock:
                return _fn(*a, **kw)
        setattr(cls, name, wrapper)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, type=Path, help="repository or worktree whose tests/fixtures to use")
    ap.add_argument("--suite", required=True, choices=sorted(SUITES))
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    dirs, suite_file, overlap = SUITES[args.suite]
    fixtures = args.root.resolve() / "tests" / "fixtures"

    tmp = Path(tempfile.mkdtemp(prefix="ck_fixture_bench_"))
    os.environ["CANDLEKEEP_DATA_DIR"] = str(tmp / "data")
    os.environ.setdefault("CHROMA_URL", "http://127.0.0.1:65530")   # never a live server
    serialise_model_calls()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore
    from candlekeep.eval.runner import BenchmarkRunner, EvalQuery
    from candlekeep.rag.processor import DocumentProcessor
    from candlekeep.rag.router import search_with_routing

    settings = Settings.from_env()
    settings.chroma_path = str(tmp / "chroma")
    settings.chunk_overlap = overlap
    store = ChromaVectorStore(settings)
    processor = DocumentProcessor(settings)
    n_docs = n_chunks = 0
    for d in dirs:
        result = processor.process_directory(fixtures / d)
        n_docs += len({c.metadata["source"] for c in result.chunks})
        n_chunks += store.add_documents(result.chunks)

    data = json.loads((fixtures / suite_file).read_text(encoding="utf-8"))
    graded = args.suite == "CEN-G"
    queries = [EvalQuery(query=q["query"], expected_sources=q["expected_sources"], category=q["category"],
                         difficulty=q["difficulty"], graded_relevance=q.get("graded_relevance") if graded else None)
               for q in data["queries"]]
    out = {"suite": args.suite, "root": str(args.root), "suite_version": data.get("metadata", {}).get("version"),
           "chunk_overlap": overlap, "documents": n_docs, "chunks": n_chunks, "queries": len(queries), "paths": {}}
    for path in PATHS:
        runner = BenchmarkRunner(lambda q, k, path=path: search_with_routing(store, q, n_results=k, query_type=path))
        results = runner.run_suite(queries, k=5)
        summary = runner.summarize(results)
        out["paths"][path] = {k: summary.get(k) for k in KEYS if k in summary}
        out["paths"][path]["per_query"] = [{"query": r.query, "rr": r.rr, "ndcg_5": r.ndcg_5,
                                            "ndcg_5_graded": r.ndcg_5_graded,
                                            "sources": r.retrieved_sources,
                                            "chunk_ids": r.retrieved_chunk_ids} for r in results]
        print(f"{args.suite} {path}: " + ", ".join(f"{k}={out['paths'][path][k]:.4f}" for k in KEYS
                                                    if isinstance(out["paths"][path].get(k), float)), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
