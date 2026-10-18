#!/usr/bin/env python3
"""Layer 2 of the agent-view evaluation: what an agent sees through MCP.

Protocol section 7. Opens one FastMCP client session (timeout 600 s) to a running
candlekeep HTTP server, makes 3 unrecorded warm-up calls (one per path), then
calls the `search` tool with {query, n_results, query_type} for every query and
path. It stores the raw tool output string, the client-side latency and any tool
error, computes the Layer 2 metrics from the raw outputs alone, and writes
tests/results/agent_view_eval/L2/<STATE>_<SUITE>[_<TAG>].json.

Always run it with venv B's python (the fixed client), whatever the server's state.
drive.py l2 starts the state's server (`<state venv>/bin/python serve.py`, whose
startup write probe never reaches Chroma), checks the server log for that, passes
the server's environment (with "write_probe": "neutralised" added), the server
checkout's provenance and the Chroma process identity (CK_EVAL_CHROMA_PROCESS), all
captured before the server started, runs this script and stops the server:

    .venv/bin/python scripts/eval_agent_view/run_layer2.py --state A --suite CEN \\
        --url http://127.0.0.1:8131/mcp --server-env-file <env.json> --provenance-file <prov.json>

It refuses to run when the corpus has no current successful ingest, when the
corpus's Chroma server (started by drive.py chroma-up) is not running, or when the
server's checkout has uncommitted changes in src/ or pyproject.toml or a .env file.
Meta records the Chroma process identity {pid, started, port} as chroma_process and,
captured again at the end, chroma_process_end. If the checkout, the ingest record or
the Chroma process changes during the run, the output goes to <results_root>/invalid/
instead and the exit code is 4 (3: some tool calls failed).

CEN-G gold chunks are cut from the body selected by --gold-body (default
common.CEN_G_GOLD_BODY = product); the mode is stored in meta.cen_g_gold_body.

Recompute the metrics of a stored file without searching (venv B's python; CEN-G
gold chunks are rebuilt with the product chunker, in the mode recorded in the file
unless --gold-body overrides it):

    .venv/bin/python scripts/eval_agent_view/run_layer2.py --recompute <L2.json> [--check] [--gold-body MODE]
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

CLIENT_TIMEOUT_S = 600


def recompute(path: str, check: bool, gold_body: str | None = None) -> int:
    doc = C.load_json(Path(path))
    metrics = C.l2_metrics(doc, gold_body=gold_body)
    if check:
        diffs = C.compare_metrics(doc.get("metrics", {}), metrics)
        if diffs:
            print(f"MISMATCH ({len(diffs)}):", *diffs[:50], sep="\n  ")
            return 1
        print(f"OK: recomputed metrics are identical to the stored metrics of {path}")
        return 0
    print(C.dumps({"metrics": metrics}))
    return 0


async def collect(url: str, queries: list, n_results: int, label: str) -> tuple[list, str, str]:
    """(rows, readiness get_stats text, warm-up query) from one client session."""
    from fastmcp import Client
    rows = []
    async with Client(url, timeout=CLIENT_TIMEOUT_S) as client:
        stats = await C.mcp_wait_ready(client, timeout=900)
        warm_query = queries[0]["query"]
        for path in C.PATHS:  # 3 unrecorded warm-up calls
            await C.mcp_text(client, "search", {"query": warm_query, "n_results": n_results,
                                                "query_type": path}, timeout=CLIENT_TIMEOUT_S)
        t_run = time.monotonic()
        for i, q in enumerate(queries, 1):
            for path in C.PATHS:
                args = {"query": q["query"], "n_results": n_results, "query_type": path}
                t0 = time.perf_counter()
                try:
                    text, is_error = await C.mcp_text(client, "search", args, timeout=CLIENT_TIMEOUT_S)
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    raw, error = (text, None) if not is_error else ("", text or "tool error")
                except Exception as e:  # transport or timeout error: recorded, not fatal
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    raw, error = "", f"{type(e).__name__}: {e}"
                rows.append({"qid": q["qid"], "path": path, "latency_ms": latency_ms,
                             "raw_output": raw, "error": error})
            if i % 10 == 0 or i == len(queries):
                print(f"[L2 {label}] {i}/{len(queries)} queries, {time.monotonic() - t_run:.0f}s",
                      file=sys.stderr, flush=True)
    return rows, stats, warm_query


def run(args) -> int:
    C.require_interpreter(C.STATES["B"])
    state = C.STATES[args.state]
    suite = C.SUITES[args.suite]
    corpus = C.CORPORA[suite.corpus]
    out = Path(args.out) if args.out else C.layer_path("L2", state.name, suite.name, args.tag)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} exists (use --force to overwrite)")
    queries = C.load_queries(suite)
    server_env = C.load_json(Path(args.server_env_file)) if args.server_env_file else {}
    if not server_env:
        print("warning: no --server-env-file; meta.server_env will be empty", file=sys.stderr)
    elif server_env.get("write_probe") != "neutralised":
        print("warning: server_env has no \"write_probe\": \"neutralised\" (drive.py l2 adds it after checking the "
              "server log); verify.py will flag this file", file=sys.stderr)
    try:  # the corpus's current, successful ingest; its identity goes into meta
        _, identity = C.current_ingest(corpus)
    except C.IngestError as e:
        raise SystemExit(str(e))
    chroma_start, chroma_source = C.chroma_process_for_run(corpus, "run_layer2.py")
    if chroma_source.startswith("captured by run_layer2.py"):
        chroma_source += "; the server's start is not covered"
    if args.provenance_file:  # captured by drive.py before the server process started
        prov = C.load_json(Path(args.provenance_file))
        prov_source = "captured by drive.py before the server started"
        if Path(prov.get("checkout", "")).resolve() != state.checkout.resolve():
            raise SystemExit(f"{args.provenance_file} is for {prov.get('checkout')}, not {state.checkout}")
    else:
        prov = C.git_provenance(state.checkout)
        prov_source = "read by the client at its start (the server's start is not covered)"
    problems = C.provenance_problems(prov) or C.provenance_problems(C.git_provenance(state.checkout))
    if problems:
        raise SystemExit(f"refusing to measure state {state.name}: " + " | ".join(problems))
    packages = C.packages_of(state.python)
    gold_body = args.gold_body or C.CEN_G_GOLD_BODY
    gold = C.GoldText(corpus.ingest_dirs(), corpus.beir_dir, gold_body)
    if any(q["graded_chunks"] for q in queries):  # build CEN-G gold chunks before the run
        for q in queries:
            gold.gold_chunk_shingle_sets(q["graded_chunks"] or {})
    started = C.now_iso()
    rows, stats, warm_query = asyncio.run(collect(args.url, queries, suite.n_results,
                                                  f"{state.name} {suite.name}{' ' + args.tag if args.tag else ''}"))
    # Provenance, ingest identity and Chroma process again. drive.py checks once more
    # after the server has stopped.
    prov_end = C.git_provenance(state.checkout)
    invalid = [f"checkout changed: {c}" for c in C.provenance_changes(prov, prov_end)]
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
        "layer": "L2",
        "state": state.name,
        "tag": args.tag,
        "suite": suite.name,
        "corpus": corpus.id,
        "server_url": args.url,
        "server_env": server_env,
        "client_fastmcp": importlib.metadata.version("fastmcp"),
        "git_sha": prov["git_sha"],
        "src_tree_sha": prov["src_tree_sha"],
        "packages": packages,
        "device": server_env.get("CANDLEKEEP_DEVICE", C.DEVICE),
        "n_results": suite.n_results,
        "started_at": started,
        "finished_at": C.now_iso(),
        # provenance beyond the data contract
        **identity,                      # ingest_id, ingest_uuid, ingest_record, ingest_record_sha256
        "pyproject_sha": prov.get("pyproject_sha"),
        "src_dirty": prov["src_dirty"],
        "status_porcelain": prov["status_porcelain"],
        "dotenv_present": prov["dotenv_present"],
        "provenance_captured_at": prov.get("captured_at"),
        "provenance_source": prov_source,
        "provenance_end": C.provenance_meta(prov_end),
        "checkout": str(state.checkout),
        "venv": str(state.venv),
        "client_python": sys.executable,
        "graph_empty": bool(args.graph_empty),
        "server_log": args.server_log,
        "server_get_stats": stats,
        "chroma_process": chroma_start,  # {pid, started, port}, protocol section 16
        "chroma_process_end": chroma_end,
        "chroma_process_source": chroma_source,
        "corpus_dirs": [str(d) for d in corpus.ingest_dirs()],
        "gold_text_source": gold.source,
        "cen_g_gold_body": gold_body,
        "cen_g_chunk_body": C.GOLD_BODY_DESCRIPTIONS[gold_body],
        "warmup_query": warm_query,
        "metrics_module": C.metrics_module_info(),
        "candlekeep_file_for_gold_chunks": C.candlekeep_file(),
        "harness_sha256": C.harness_hashes("run_layer2.py", "serve.py"),
    }
    if invalid:
        meta["invalid"] = invalid
    doc = json.loads(C.dumps({"meta": meta, "queries": queries, "rows": rows}))  # metrics see exactly the stored data
    doc["metrics"] = C.l2_metrics(doc, gold)
    if invalid:  # never written where a step could use or skip on it
        bad = C.invalid_path(out)
        C.write_json_atomic(bad, doc)
        print(f"INVALID RUN, written to {bad}:", *invalid, sep="\n  ", file=sys.stderr)
        return 4
    C.write_json_atomic(out, doc)
    print(f"wrote {out}")
    for path, m in doc["metrics"].items():
        extra = ""
        if m["gpv"] is not None:
            extra += f" GPV={m['gpv']:.4f} (n={m['gpv_n']}) GPC={m['gpc']:.4f}"
        if m["support_visible"] is not None:
            extra += f" SupportVisible={m['support_visible']:.4f}"
        print(f"  {path:8} n={m['n']} errors={m['errors']} SrcVis@5={m['srcvis_5']:.4f}"
              f" GoldText={m['goldtext_mean'] if m['goldtext_mean'] is None else round(m['goldtext_mean'], 2)}"
              f" chars={m['chars_mean']:.0f}{extra} p50={m['latency_p50_ms']:.1f}ms")
    errors = sum(m["errors"] for m in doc["metrics"].values())
    if errors:
        print(f"{errors} tool call(s) failed; see rows[].error", file=sys.stderr)
    return 3 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", choices=sorted(C.STATES), help="state of the server being measured")
    ap.add_argument("--suite")
    ap.add_argument("--url", help="MCP endpoint, e.g. http://127.0.0.1:8131/mcp")
    ap.add_argument("--tag")
    ap.add_argument("--out", help="explicit output path (informational rows)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--server-env-file", help="JSON of the environment the server was started with")
    ap.add_argument("--server-log", help="path of the server log, recorded in meta")
    ap.add_argument("--provenance-file",
                    help="JSON of the server checkout's provenance, captured before the server started")
    ap.add_argument("--graph-empty", action="store_true", help="recorded in meta: server runs on an empty-graph copy")
    ap.add_argument("--gold-body", choices=C.GOLD_BODIES, default=None,
                    help=f"body the CEN-G gold chunks are cut from (default {C.CEN_G_GOLD_BODY}; with "
                         "--recompute: the mode recorded in the file)")
    ap.add_argument("--recompute", metavar="L2_JSON", help="print metrics recomputed from a stored file")
    ap.add_argument("--check", action="store_true", help="with --recompute: compare with the stored metrics")
    C.add_hidden_args(ap)
    args = ap.parse_args()
    C.apply_overrides(args)
    if args.recompute:
        return recompute(args.recompute, args.check, args.gold_body)
    if not (args.state and args.suite and args.url):
        ap.error("--state, --suite and --url are required")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
