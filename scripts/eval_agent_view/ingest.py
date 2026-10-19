#!/usr/bin/env python3
"""Ingest one corpus, once, through state B's MCP server.

Protocol sections 4, 5 and 11 (step 3). With venv B only:

1. Refuse if the corpus's Chroma port or the ingest port is in use, if drive.py's
   Chroma server for the corpus is running, or if the main checkout has uncommitted
   changes in src/ or pyproject.toml or a .env file. All of this is checked before
   anything is deleted.
2. Refuse if <data_root>/<I0x>/chroma or ck_data already holds data, or an ingest
   record exists, unless --force. --force also refuses while L1/L2 outputs (and, for
   the CEN corpus, judge packs) computed on the current ingest exist, unless
   --supersede is given too: then the old ingest record(s) and those outputs are moved
   to <results_root>/superseded/<I0x>_<stamp>/ before the data is deleted.
3. Give the ingest a fresh uuid4 (ingest_uuid), written to the record and to
   <data_root>/<I0x>/ingest_marker.json; every L1/L2 output records it.
4. Every corpus is ingested with a single `ingest` call on one directory (protocol
   section 16: back-to-back calls can run the embedder concurrently with the
   background normalisation rebuild, which crashes MPS):
   * I01/I02 (kind "links"): <staging_root>/<I0x>/ holds one symlink per file of
     tests/fixtures/sample_docs and scale_docs (basename -> absolute target); a
     basename collision fails the ingest. The symlink map goes into the record.
   * BEIR corpora: every document is staged as <staging_root>/<I0x>/<doc_id>.md with
     the frozen frontmatter (title: <json.dumps(title)>, description: "") and the body.
   * Cross-domain corpora are single directories, ingested as they are.
5. Start venv B's Chroma server on the corpus port with path <I0x>/chroma, and B's
   candlekeep HTTP server (the `candlekeep` command, write probe enabled) on the
   ingest port (8130) with CANDLEKEEP_DATA_DIR=<I0x>/ck_data.
6. Wait until get_stats stops reporting "loading", call `ingest` once on the corpus's
   directory (timeout 3 h), call `rebuild_graph`, call `get_stats`.
7. Write tests/results/agent_view_eval/ingest/<I0x>_<name>.json with timings, raw tool
   outputs and parsed counts, then stop both servers. The record is not ok if the
   checkout's provenance changed during the ingest. The Chroma server used for the
   L1/L2 runs is a separate process, started afterwards (drive.py chroma-up).

    .venv/bin/python scripts/eval_agent_view/ingest.py --corpus I01

With --round FILE, the round file's data and staging directories, ports, results root,
venv B and expected document counts replace round 1's (common.load_round; B's checkout
is this repository in every round).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import platform
import re
import shutil
import signal
import sqlite3
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

INGEST_TIMEOUT_S = 3 * 3600


class IngestFailed(RuntimeError):
    pass


def stage_beir(corpus: C.CorpusDef, force: bool) -> dict:
    """Write <doc_id>.md files for a BEIR corpus and check that the product's
    frontmatter parse gives back exactly the title, an empty description and the text."""
    import yaml
    target = C.CONFIG.staging_root / corpus.id
    docs = list(C.iter_beir_corpus(corpus.beir_dir))
    expected = {f"{doc_id}.md": C.beir_staged_content(title, text) for doc_id, title, text in docs}
    if len(expected) != len(docs):
        raise IngestFailed("duplicate BEIR document ids")
    unsafe = [n for n in expected if "/" in n or n.startswith(".")]
    if unsafe:
        raise IngestFailed(f"unsafe document ids: {unsafe[:5]}")
    if target.exists():
        existing = {p.name for p in target.iterdir()}
        if force:
            shutil.rmtree(target)
        elif existing - set(expected):
            raise IngestFailed(f"{target} holds files that are not in the corpus; use --force")
    target.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0
    for name in sorted(expected):
        data = expected[name].encode("utf-8")
        path = target / name
        if not path.is_file() or path.read_bytes() != data:
            path.write_bytes(data)
            written += 1
        digest.update(name.encode() + b"\0" + data + b"\0")
    failures = []
    for doc_id, title, text in docs:
        content = expected[f"{doc_id}.md"]
        m = C.FRONTMATTER_RE.match(content)
        try:
            meta = yaml.safe_load(m.group(1)) if m else None
        except yaml.YAMLError:
            meta = None
        if (not isinstance(meta, dict) or meta.get("title") != title or meta.get("description") != ""
                or content[m.end():] != text + "\n"):
            failures.append(doc_id)
    if failures:
        raise IngestFailed(f"{len(failures)} staged files do not parse back exactly: {failures[:10]}")
    return {"kind": "beir", "dir": str(target), "files": len(expected), "written": written,
            "sha256": digest.hexdigest(), "frontmatter_roundtrip_failures": 0}


def stage_links(corpus: C.CorpusDef, force: bool) -> dict:
    """<staging_root>/<I0x>/ with one symlink per file of the corpus's source
    directories (basename -> absolute target), so that one ingest call covers them
    all. Fails on a basename collision, and on a staging directory that holds
    anything other than these symlinks (unless --force, which rebuilds it)."""
    target = C.CONFIG.staging_root / corpus.id
    links: dict = {}
    collisions: dict = {}
    for d in corpus.source_dirs:
        d = Path(d)
        if not d.is_dir():
            raise IngestFailed(f"source directory missing: {d}")
        for p in sorted(d.rglob("*")):
            if not p.is_file():
                continue
            dest = os.path.abspath(p)
            if p.name in links:
                collisions.setdefault(p.name, [links[p.name]]).append(dest)
                continue
            links[p.name] = dest
    if collisions:
        raise IngestFailed(f"basename collision(s) between the source directories of {corpus.id}: {collisions}")
    if not links:
        raise IngestFailed(f"no files in {[str(d) for d in corpus.source_dirs]}")

    def foreign(entries: dict) -> list[str]:
        return sorted(n for n, p in entries.items()
                      if n not in links or not p.is_symlink() or os.readlink(p) != links[n])

    if target.exists():
        if force:
            shutil.rmtree(target)
        else:
            unexpected = foreign({p.name: p for p in target.iterdir()})
            if unexpected:
                raise IngestFailed(f"{target} holds entries that are not this corpus's symlinks "
                                   f"({unexpected[:5]}); use --force")
    target.mkdir(parents=True, exist_ok=True)
    created = 0
    for name, dest in sorted(links.items()):
        link = target / name
        if not link.is_symlink():
            os.symlink(dest, link)
            created += 1
    entries = {p.name: p for p in target.iterdir()}
    problems = foreign(entries) + sorted(set(links) - set(entries))
    problems += sorted(n for n, p in entries.items() if n in links and not p.is_file())  # dangling
    if problems:
        raise IngestFailed(f"staging directory {target} is not as built: {problems[:10]}")
    digest = hashlib.sha256()
    for name, dest in sorted(links.items()):
        digest.update(name.encode() + b"\0" + dest.encode() + b"\n")
    return {"kind": "symlinks", "dir": str(target), "source_dirs": [str(d) for d in corpus.source_dirs],
            "files": len(links), "created": created, "links": dict(sorted(links.items())),
            "links_sha256": digest.hexdigest()}


_STAT_LABELS = {
    "chunks": "Total chunks",
    "documents": "Total documents",
    "entities": "Entities",
    "edges": "Co-occurrence edges",
    "entity_ruler_vocabulary": "Entity ruler vocabulary",
    "normalisation_map_variants": "Normalisation map variants",
}


def parse_stats(text: str) -> dict:
    out = {}
    for key, label in _STAT_LABELS.items():
        m = re.search(rf"- {re.escape(label)}: ([\d,]+)", text)
        out[key] = int(m.group(1).replace(",", "")) if m else None
    return out


async def run_tools(url: str, path: Path, steps: list) -> None:
    """get_stats until ready, one `ingest` call on path, rebuild_graph, get_stats."""
    from fastmcp import Client

    async def call(tool, args, timeout, expect):
        t0 = time.monotonic()
        text, is_error = await C.mcp_text(client, tool, args, timeout=timeout)
        step = {"tool": tool, "args": args, "elapsed_s": round(time.monotonic() - t0, 3),
                "is_error": is_error, "output": text}
        steps.append(step)
        if is_error or (expect and not text.startswith(expect)):
            raise IngestFailed(f"{tool} {args}: {text[:500]}")
        return step

    async with Client(url, timeout=INGEST_TIMEOUT_S + 600) as client:
        t0 = time.monotonic()
        text = await C.mcp_wait_ready(client, timeout=900)
        steps.append({"tool": "get_stats", "args": {}, "phase": "ready", "elapsed_s": round(time.monotonic() - t0, 3),
                      "is_error": False, "output": text})
        step = await call("ingest", {"path": str(path)}, INGEST_TIMEOUT_S, "✓ Ingested")
        m = re.search(r"Ingested (\d+) chunks", step["output"])
        step["chunks"] = int(m.group(1)) if m else None
        await call("rebuild_graph", {}, INGEST_TIMEOUT_S, "✓")
        step = await call("get_stats", {}, 600, None)
        step["phase"] = "final"


def graph_edges(ck_data: Path) -> int | None:
    db = ck_data / "graph.db"
    if not db.is_file():
        return None
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute("SELECT COUNT(*) FROM entity_cooccurrence").fetchone()[0]
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", required=True, help="I01..I09")
    ap.add_argument("--force", action="store_true",
                    help="delete this corpus's existing chroma/ck_data (and staging) and ingest again")
    ap.add_argument("--supersede", action="store_true",
                    help="with --force: move the L1/L2 outputs (and CEN judge packs) computed on the old "
                         "ingest to superseded/ together with the old ingest record")
    C.add_hidden_args(ap)
    args = ap.parse_args()
    C.apply_overrides(args)
    C.require_interpreter(C.STATES["B"])
    corpus = C.CORPORA[args.corpus]
    chroma_path, ck_data = C.chroma_dir(corpus), C.ck_data_dir(corpus)
    record_path, failed_path = C.ingest_record_path(corpus), C.failed_record_path(corpus)
    marker_path = C.ingest_marker_path(corpus)
    emptygraph_copy = C.corpus_root(corpus) / "ck_data_emptygraph"

    # 1. Nothing may be serving this corpus, and B's checkout must be clean. All of
    #    this is checked before anything is deleted or moved.
    live = C.our_chroma(corpus)
    if live:
        raise SystemExit(f"drive.py's Chroma server for {corpus.id} is running (pid {live['pid']}, port "
                         f"{live['port']}); stop it first: drive.py chroma-down --corpus {corpus.id}{C.round_flag()}")
    for port in (corpus.chroma_port, C.CONFIG.ingest_port):
        if C.port_in_use(port):
            raise SystemExit(f"port {port} is already in use")
    prov = C.git_provenance(C.REPO)
    problems = C.provenance_problems(prov)
    if problems:
        raise SystemExit("refusing to ingest with state B's checkout in this condition: " + " | ".join(problems))

    # 2. Existing data, records and outputs.
    def holds_data(p: Path) -> bool:
        return p.exists() and any(p.iterdir())

    old_records = [p for p in (record_path, failed_path) if p.exists()]
    if holds_data(chroma_path) or holds_data(ck_data) or old_records or marker_path.exists():
        if not args.force:
            raise SystemExit(f"{corpus.id} already has data ({C.corpus_root(corpus)}) or an ingest record "
                             f"({record_path}); refusing. Use --force to delete and re-ingest.")
        try:
            dependents = C.corpus_dependents(corpus)
        except C.IngestError as e:
            raise SystemExit(f"refusing --force: {e}")
        if dependents and not args.supersede:
            listing = "\n  ".join(str(p) for p in dependents[:20])
            raise SystemExit(f"--force would replace the ingest of {corpus.id}, but {len(dependents)} output(s) "
                             f"were computed on it:\n  {listing}\nAdd --supersede to move them and the old "
                             f"ingest record to superseded/, or move them yourself.")
        if old_records or dependents:  # keep everything of the old ingest for the audit trail
            dest = C.CONFIG.results_root / "superseded" / f"{corpus.id}_{C.utc_stamp()}"
            moved = C.move_preserving(old_records + dependents, dest)
            print(f"--force: moved {len(moved)} file(s) of the previous ingest to {dest}")
        for p in (chroma_path, ck_data, emptygraph_copy):
            if p.exists():
                print(f"--force: deleting {p}")
                shutil.rmtree(p)
        marker_path.unlink(missing_ok=True)

    # 3. A fresh identity for this ingest, stamped on the data directory first.
    ingest_uuid = uuid.uuid4().hex
    started, t_start = C.now_iso(), time.monotonic()
    C.write_json_atomic(marker_path, {"ingest_uuid": ingest_uuid, "corpus": corpus.id, "created_at": started,
                                      "record": str(record_path)})
    try:  # 4. the one directory the single ingest call gets
        staging = (stage_beir(corpus, args.force) if corpus.kind == "beir"
                   else stage_links(corpus, args.force) if corpus.kind == "links" else None)
        target = corpus.ingest_path()
    except (IngestFailed, ValueError) as e:
        raise SystemExit(f"staging {corpus.id} failed: {e}")
    if not target.is_dir():
        raise SystemExit(f"corpus directory missing: {target}")
    ck_data.mkdir(parents=True, exist_ok=True)
    logs = C.logs_dir()
    chroma_log, server_log = logs / f"ingest_{corpus.id}_chroma.log", logs / f"ingest_{corpus.id}_server.log"
    env = C.candlekeep_server_env(corpus, ck_data, C.CONFIG.ingest_port)
    url = C.mcp_url(C.CONFIG.ingest_port)
    steps: list = []
    failure = None
    fingerprint = None
    chroma = C.start_chroma(chroma_path, corpus.chroma_port, chroma_log)
    try:
        server_cwd = C.make_scratch_dir()
        server = C.spawn([C.VENV_B / "bin" / "candlekeep"], env, server_log, cwd=server_cwd)
        try:
            C.wait_server_port(server, C.CONFIG.ingest_port, 300)
            asyncio.run(run_tools(url, target, steps))
        except Exception as e:
            failure = f"{type(e).__name__}: {e}"
        finally:
            code = C.stop_process(server, timeout=900, sig=signal.SIGINT)
            shutil.rmtree(server_cwd, ignore_errors=True)
            print(f"candlekeep server stopped (exit {code})")
        if failure is None:
            fingerprint = C.collection_fingerprint(corpus.chroma_port)
    finally:
        C.stop_process(chroma, timeout=120)
        print("chroma stopped")

    final = next((s for s in reversed(steps) if s.get("phase") == "final"), None)
    counts = parse_stats(final["output"]) if final else {}
    counts["ingested_chunks_sum"] = sum(s.get("chunks") or 0 for s in steps if s["tool"] == "ingest")
    edges_on_disk = graph_edges(ck_data)
    prov_after = C.git_provenance(C.REPO)
    prov_changes = C.provenance_changes(prov, prov_after)
    marker = C.load_json(marker_path) if marker_path.is_file() else {}
    checks = {
        "single_ingest_call": sum(1 for s in steps if s["tool"] == "ingest") == 1,
        "documents_match_protocol": counts.get("documents") == corpus.n_docs if corpus.n_docs else None,
        "chunks_match_ingest_outputs": counts.get("chunks") == counts["ingested_chunks_sum"],
        "fingerprint_count_matches": bool(fingerprint) and fingerprint["count"] == counts.get("chunks"),
        "graph_edges_on_disk_match": edges_on_disk == counts.get("edges"),
        "provenance_unchanged": not prov_changes,
        "data_marker_matches": marker.get("ingest_uuid") == ingest_uuid,
    }
    if prov_changes and failure is None:
        failure = "state B's checkout changed during the ingest: " + "; ".join(prov_changes)
    ok = failure is None and all(v is not False for v in checks.values())
    record = {
        "ingest_id": corpus.id,          # the run id of protocol section 14 (I01..I09)
        "ingest_uuid": ingest_uuid,      # unique per ingest; recorded by every L1/L2 output
        "name": corpus.name,
        "corpus": corpus.id,
        "kind": corpus.kind,
        "ok": ok,
        "failure": failure,
        "dirs": [str(target)],           # what the single ingest call got
        "ingest_path": str(target),
        "source_dirs": [str(d) for d in corpus.source_dirs] or ([str(corpus.beir_dir)] if corpus.beir_dir else []),
        "chunk_overlap": corpus.chunk_overlap,
        "expected_documents": corpus.n_docs,
        "state": "B",
        "git_sha": prov["git_sha"],
        "src_tree_sha": prov["src_tree_sha"],
        "src_dirty": prov["src_dirty"],
        "provenance": prov,
        "provenance_after": prov_after,
        "data_marker": str(marker_path),
        "python": platform.python_version(),
        "packages": C.installed_packages(),
        "server_url": url,
        "server_env": env,
        "server_log": str(server_log),
        "chroma": {"port": corpus.chroma_port, "path": str(chroma_path), "cli": str(C.chroma_cli()),
                   "chromadb": C.chroma_version(), "log": str(chroma_log)},
        "data_dir": str(ck_data),
        "started_at": started,
        "finished_at": C.now_iso(),
        "elapsed_s": round(time.monotonic() - t_start, 1),
        "steps": steps,
        "counts": counts,
        "graph_edges_on_disk": edges_on_disk,
        "checks": checks,
        "collection_fingerprint": fingerprint,
        "staging": staging,
        "harness_sha256": C.harness_hashes("ingest.py"),
    }
    out = record_path if ok else failed_path
    C.write_json_atomic(out, record)
    print(f"wrote {out}")
    print(f"  ingest_uuid: {ingest_uuid}")
    print(f"  counts: {counts}")
    print(f"  checks: {checks}")
    if not ok:
        print(f"INGEST FAILED: {failure or 'checks failed'}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
