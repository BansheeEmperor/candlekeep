#!/usr/bin/env python3
"""Layer 1 of the agent-view evaluation: retrieval, measured in-process.

Protocol section 6. For every query of a suite and every path (hybrid, precise,
explore), time

    candlekeep.rag.router.search_with_routing(store, query, n_results, None, query_type=path)

against the suite's shared Chroma collection, record the ranked results (source,
chunk index, score, full text, match offset, number of matched chunks), compute
the Layer 1 metrics and write tests/results/agent_view_eval/L1/<STATE>_<SUITE>[_<TAG>].json.

It refuses to run when the corpus has no current successful ingest (record ok, with
an ingest_uuid that the data directory's marker repeats), when the corpus's Chroma
server (started by drive.py chroma-up) is not running, or when the state's checkout
has uncommitted changes in src/ or pyproject.toml or a .env file. Meta records the
ingest identity, the provenance read before candlekeep is imported, and the Chroma
process identity {pid, started, port} (meta.chroma_process: the one drive.py passed
in CK_EVAL_CHROMA_PROCESS, else the one running at the start; meta.chroma_process_end:
captured again at the end). If any of these changes during the run the output goes
to <results_root>/invalid/ instead and the exit code is 4.

Run it with the state's own venv python while the corpus's Chroma server is up
(drive.py l1 does this; it never starts or stops Chroma):

    <state venv>/bin/python scripts/eval_agent_view/run_layer1.py --state B --suite CEN
    <state venv>/bin/python scripts/eval_agent_view/run_layer1.py --state B --suite CEN --tag rerun

Recompute the metrics of a stored file without searching (any python with numpy):

    python scripts/eval_agent_view/run_layer1.py --recompute <L1.json> [--check]

The script uses only APIs that state A also has (ChromaVectorStore, Settings,
search_with_routing, graph_store.clear_graph_store_cache, reranker.warm_up).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def result_record(r) -> tuple[dict, bool]:
    """One search result in the data-contract shape; also reports a non-finite score."""
    meta = r.metadata or {}
    source_path = str(meta.get("source", ""))
    matches = meta.get("_matches")
    if isinstance(matches, str):
        try:
            matches = json.loads(matches)
        except ValueError:
            matches = None
    offset = meta.get("_match_offset")
    score = float(r.score)
    finite = math.isfinite(score)
    return {
        "source": meta.get("filename") or C.basename(source_path),
        "source_path": source_path,
        "chunk_index": int(meta.get("chunk_index", 0)),
        "score": score if finite else None,
        "text": r.text,
        "match_offset": int(offset) if offset is not None else None,
        "n_matches": len(matches) if matches is not None else None,
    }, finite


def recompute(path: str, check: bool) -> int:
    doc = C.load_json(Path(path))
    metrics = C.l1_metrics(doc)
    if check:
        diffs = C.compare_metrics(doc.get("metrics", {}), metrics)
        if diffs:
            print(f"MISMATCH ({len(diffs)}):", *diffs[:50], sep="\n  ")
            return 1
        print(f"OK: recomputed metrics are identical to the stored metrics of {path}")
        return 0
    print(C.dumps({"metrics": metrics}))
    return 0


def run(args) -> int:
    state = C.STATES[args.state]
    C.require_interpreter(state)
    suite = C.SUITES[args.suite]
    corpus = C.CORPORA[suite.corpus]
    out = Path(args.out) if args.out else C.layer_path("L1", state.name, suite.name, args.tag)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} exists (use --force to overwrite)")
    queries = C.load_queries(suite)
    url = C.chroma_url(corpus)
    if not C.http_ok(C.chroma_heartbeat_url(corpus.chroma_port)):
        raise SystemExit(f"Chroma for {corpus.id} is not running at {url} (start it with "
                         f"`drive.py chroma-up --corpus {corpus.id}{C.round_flag()}`)")
    chroma_start, chroma_source = C.chroma_process_for_run(corpus, "run_layer1.py")
    ck_data = C.ck_data_dir(corpus)
    if not (ck_data / "graph.db").is_file():
        raise SystemExit(f"{ck_data}/graph.db missing: ingest {corpus.id} first")
    try:  # the corpus's current, successful ingest; its identity goes into meta
        ingest, identity = C.current_ingest(corpus)
    except C.IngestError as e:
        raise SystemExit(str(e))
    prov = C.git_provenance(state.checkout)  # read before any candlekeep code is imported
    problems = C.provenance_problems(prov)
    if problems:
        raise SystemExit(f"refusing to run state {state.name}: " + " | ".join(problems))
    started = C.now_iso()

    C.import_candlekeep()  # dead CHROMA_URL + scratch data dir for the import-time thread
    import candlekeep
    ck_file = Path(candlekeep.__file__).resolve()
    if not ck_file.is_relative_to((state.checkout / "src").resolve()):
        raise SystemExit(f"candlekeep imported from {ck_file}, not from {state.checkout}/src")
    from candlekeep.config import Settings
    from candlekeep.database import graph_store as graph_store_module
    from candlekeep.database.vector_store import ChromaVectorStore
    from candlekeep.rag.reranker import warm_up
    from candlekeep.rag.router import search_with_routing

    graph_store_module.clear_graph_store_cache()  # bind the graph singleton to this corpus
    settings = Settings(chroma_url=url, data_dir=ck_data, device=C.DEVICE, chunk_overlap=corpus.chunk_overlap)
    store = ChromaVectorStore(settings)
    graph = store.graph_store
    if graph is None or Path(graph._path).resolve() != (ck_data / "graph.db").resolve():
        raise SystemExit(f"graph store is not {ck_data}/graph.db")
    collection_count = store.collection.count()
    if ingest.get("counts", {}).get("chunks") != collection_count:
        raise SystemExit(f"collection has {collection_count} chunks, ingest record says "
                         f"{ingest.get('counts', {}).get('chunks')}")

    n_results = suite.n_results
    warm_query = queries[0]["query"]
    store.embedder.get_model()
    warm_up(C.DEVICE)
    for path in C.PATHS:  # one unrecorded warm-up search per path
        search_with_routing(store, warm_query, n_results, None, query_type=path)

    rows, nonfinite = [], 0
    t_run = time.monotonic()
    for i, q in enumerate(queries, 1):
        for path in C.PATHS:
            t0 = time.perf_counter()
            results = search_with_routing(store, q["query"], n_results, None, query_type=path)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            records = []
            for r in results:
                rec, finite = result_record(r)
                nonfinite += 0 if finite else 1
                records.append(rec)
            rows.append({"qid": q["qid"], "path": path, "latency_ms": latency_ms, "results": records})
        if i % 10 == 0 or i == len(queries):
            print(f"[L1 {state.name} {suite.name}] {i}/{len(queries)} queries, "
                  f"{time.monotonic() - t_run:.0f}s", file=sys.stderr, flush=True)

    state_metrics = state.checkout / "src" / "candlekeep" / "eval" / "metrics.py"
    # Provenance, ingest identity and Chroma process again, after every candlekeep
    # module has run.
    prov_end = C.git_provenance(state.checkout)
    invalid = [f"checkout changed during the run: {c}" for c in C.provenance_changes(prov, prov_end)]
    try:
        _, identity_end = C.current_ingest(corpus)
        if identity_end != identity:
            invalid.append(f"ingest record changed during the run: {identity} -> {identity_end}")
    except C.IngestError as e:
        invalid.append(f"ingest record no longer valid: {e}")
    chroma_end = C.chroma_process(corpus)
    if chroma_end != chroma_start:
        invalid.append(f"Chroma process changed during the run: {chroma_start} -> {chroma_end}")
    meta = {
        "layer": "L1",
        "state": state.name,
        "tag": args.tag,
        "suite": suite.name,
        "corpus": corpus.id,
        "git_sha": prov["git_sha"],
        "src_tree_sha": prov["src_tree_sha"],
        "python": platform.python_version(),
        "packages": C.installed_packages(),
        "device": C.DEVICE,
        "n_results": n_results,
        "chunk_overlap": corpus.chunk_overlap,
        "started_at": started,
        "finished_at": C.now_iso(),
        # provenance beyond the data contract
        **identity,                      # ingest_id, ingest_uuid, ingest_record, ingest_record_sha256
        "pyproject_sha": prov.get("pyproject_sha"),
        "src_dirty": prov["src_dirty"],
        "status_porcelain": prov["status_porcelain"],
        "dotenv_present": prov["dotenv_present"],
        "provenance_captured_at": prov["captured_at"],
        "provenance_end": C.provenance_meta(prov_end),
        "checkout": str(state.checkout),
        "venv": str(state.venv),
        "candlekeep_file": str(ck_file),
        "chroma_url": url,
        "chroma_process": chroma_start,  # {pid, started, port}, protocol section 16
        "chroma_process_end": chroma_end,
        "chroma_process_source": chroma_source,
        "data_dir": str(ck_data),
        "corpus_dirs": [str(d) for d in corpus.ingest_dirs()],
        "collection_count": collection_count,
        "hash_seed": os.environ.get("PYTHONHASHSEED"),
        "warmup_query": warm_query,
        "nonfinite_scores": nonfinite,
        "metrics_module": C.metrics_module_info(),
        "state_metrics_module_sha256": C.sha256_file(state_metrics) if state_metrics.is_file() else None,
        "harness_sha256": C.harness_hashes("run_layer1.py"),
    }
    if invalid:
        meta["invalid"] = invalid
    doc = json.loads(C.dumps({"meta": meta, "queries": queries, "rows": rows}))  # metrics see exactly the stored data
    doc["metrics"] = C.l1_metrics(doc)
    if invalid:  # never written where a step could use or skip on it
        bad = C.invalid_path(out)
        C.write_json_atomic(bad, doc)
        print(f"INVALID RUN, written to {bad}:", *invalid, sep="\n  ", file=sys.stderr)
        return 4
    C.write_json_atomic(out, doc)
    print(f"wrote {out}")
    for path, m in doc["metrics"].items():
        print(f"  {path:8} n={m['n']} MRR@5={m['mrr_5']:.4f} nDCG@5={m['ndcg_5']:.4f} Hit@5={m['hit_5']:.4f} "
              f"leaks={m['adv_leak_count']}/{m['adv_n']} p50={m['latency_p50_ms']:.1f}ms")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", choices=sorted(C.STATES))
    ap.add_argument("--suite", help="suite name, e.g. CEN, MH, CEN-G, CD-LEG, BEIR-SF")
    ap.add_argument("--tag", help="output tag, e.g. rerun -> L1/<STATE>_<SUITE>_rerun.json")
    ap.add_argument("--out", help="explicit output path")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output file")
    ap.add_argument("--recompute", metavar="L1_JSON", help="print metrics recomputed from a stored file")
    ap.add_argument("--check", action="store_true", help="with --recompute: compare with the stored metrics")
    C.add_hidden_args(ap)
    args = ap.parse_args()
    C.apply_overrides(args)
    if args.out:
        C.require_round_output(args.out)
    if args.recompute:
        return recompute(args.recompute, args.check)
    if not args.state or not args.suite:
        ap.error("--state and --suite are required")
    C.reexec_with_hash_seed()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
