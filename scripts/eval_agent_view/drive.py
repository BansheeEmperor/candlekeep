#!/usr/bin/env python3
"""Orchestrates the agent-view evaluation (protocol section 11) with the right
venvs, ports and environments. Uses only the standard library; MCP and Chroma
client work runs in subprocesses with venv B's python.

    drive.py preflight
    drive.py env [--state S]
    drive.py ingest --corpus I0x [--force [--supersede]]
    drive.py chroma-up --corpus I0x | chroma-down --corpus I0x
    drive.py l1 --state S --suite X [--tag T] [--force]
    drive.py l2 --state S --suite X [--tag T] [--result-chars N] [--extra-chars N] [--graph-empty] [--force]
    drive.py ci --state S [--compare-only]
    drive.py all [--states A,B,C] [--corpora I01,...] [--skip-ci]
    drive.py status
    drive.py verify [verify.py arguments, e.g. --all --check-doc]

Every L1/L2 step refuses to run when the state's checkout has uncommitted changes in
src/ or pyproject.toml or a .env file, when the corpus has no current successful
ingest, when the corpus's Chroma server is not already running (l1 and l2 never
start or stop Chroma: chroma-up / chroma-down do), or when outputs of another ingest
of the corpus, outputs computed against another Chroma process, or outputs of the
same state computed with other code, exist. The checkout's provenance and the Chroma
process identity (pid, `ps -o lstart=` start time, port) are captured before the
step's code starts and again after it ends; an output whose run saw a change is
moved to invalid/. `all` starts each corpus's Chroma server once, before the first
run on it, never stops it, skips an existing output only if it belongs to the
current ingest and the state's current code, and prints how to stop the servers
it leaves running.

Layer 2 servers are started as `<state venv>/bin/python serve.py`, which keeps
candlekeep's startup write probe from reaching Chroma; the step fails unless the
server log shows that write access was denied. The ingest server is B's
`candlekeep` command, probe enabled.

Ports: Chroma for I01..I09 on 8121..8129, the ingest server on 8130, the Layer 2
server on 8131; 65530 must stay unused (the dead CHROMA_URL for in-process
imports and for the CI run). Server and run logs go to
tests/results/agent_view_eval/logs/.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import serve  # noqa: E402  (log-line constants only; importing it has no side effects)

HARNESS = C.HARNESS_DIR
DEFAULT_RESULTS_ROOT = C.CONFIG.results_root   # before any --results-root override
PY_B = C.STATES["B"].python
SERVE = HARNESS / "serve.py"   # Layer 2 server launcher (write probe neutralised)
HIDDEN: list = []          # hidden smoke-test options, forwarded to every harness script
# Candlekeep's background-init lines about the write probe (mcp/server.py, every state).
READ_ONLY_LINE = "Read-only mode (write access denied)"
WRITE_ENABLED_LINE = "Write access enabled"


class StepFailed(RuntimeError):
    pass


# ── Logging and subprocesses ─────────────────────────────────────────────────

def log_event(kind: str, **fields) -> None:
    with open(C.logs_dir() / "drive.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": C.now_iso(), "kind": kind, **fields}, ensure_ascii=False) + "\n")


def run_logged(cmd: list, log_path: Path, env: dict | None = None, cwd: Path | None = None,
               ok_codes=(0,), timeout: float | None = None) -> int:
    """Run cmd, streaming its output to the console and appending it to log_path.
    Without cwd it runs in a throwaway directory (so no stray .env is picked up)."""
    cmd = [str(c) for c in cmd]
    env = env if env is not None else C.base_env()
    scratch = None if cwd else C.make_scratch_dir()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    code = None
    try:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"\n===== {C.now_iso()} run: {' '.join(cmd)}\n")
            log.flush()
            proc = subprocess.Popen(cmd, env=env, cwd=str(cwd or scratch), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                    encoding="utf-8", errors="replace", bufsize=1)
            watchdog = threading.Timer(timeout, proc.kill) if timeout else None
            if watchdog:
                watchdog.start()
            try:
                for line in proc.stdout:
                    sys.stdout.write(line)
                    log.write(line)
                code = proc.wait()
            finally:
                if watchdog:
                    watchdog.cancel()
            log.write(f"===== exit {code} after {time.monotonic() - t0:.1f}s\n")
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)
    log_event("run", cmd=cmd, code=code, seconds=round(time.monotonic() - t0, 1), log=str(log_path))
    if ok_codes is not None and code not in ok_codes:
        raise StepFailed(f"exit {code}: {' '.join(cmd)} (log: {log_path})")
    return code


def harness_env() -> dict:
    env = C.base_env()
    env["PYTHONHASHSEED"] = C.HASH_SEED
    return env


def ingest_record(corpus: C.CorpusDef) -> dict | None:
    path = C.ingest_record_path(corpus)
    return C.load_json(path) if path.is_file() else None


def require_ingested(corpus: C.CorpusDef) -> tuple[dict, dict]:
    """(record, identity) of the corpus's current successful ingest."""
    try:
        return C.current_ingest(corpus)
    except C.IngestError as e:
        raise StepFailed(str(e))


def require_same_ingest(corpus: C.CorpusDef, identity: dict, replacing: Path | None = None) -> None:
    """Refuse to add outputs next to outputs of this corpus that were computed on a
    different ingest (or whose ingest is unknown). `replacing` is the file a --force
    run overwrites."""
    stale = C.stale_outputs(corpus, identity, exclude=replacing)
    if stale:
        raise StepFailed(f"{len(stale)} output(s) of {corpus.id} do not belong to its current ingest "
                         f"{identity['ingest_uuid']}:\n  " + "\n  ".join(stale[:20])
                         + "\nMove them aside (ingest.py --force --supersede does this when re-ingesting).")


def require_output_of_ingest(out: Path, identity: dict) -> None:
    """Refuse to skip on an existing output that was computed on a different ingest."""
    why = C.identity_mismatch(C.read_meta(out) or {}, identity)
    if why:
        raise StepFailed(f"{out} exists but was not computed on the current ingest ({why}); move it aside")


def require_state(state: str) -> C.StateDef:
    s = C.STATES[state]
    for p in (s.checkout, s.python, s.bin / "candlekeep"):
        if not p.exists():
            raise StepFailed(f"state {state}: {p} does not exist")
    return s


def clean_provenance(s: C.StateDef) -> dict:
    """Provenance of a state's checkout, captured before a step starts its code.
    Refuses a checkout with uncommitted src/ or pyproject.toml changes or a .env."""
    prov = C.git_provenance(s.checkout)
    problems = C.provenance_problems(prov)
    if problems:
        raise StepFailed(f"state {s.name}: " + " | ".join(problems))
    return prov


def require_same_code(s: C.StateDef, prov: dict, replacing: Path | None = None) -> None:
    """Refuse to add outputs of a state next to outputs of the same state computed
    with other code (src tree or pyproject.toml). A changed state is a new state
    (protocol section 10) whose old outputs must be moved aside first."""
    bad = []
    for p, meta, error in C.state_outputs(s.name):
        if replacing is not None and p.resolve() == replacing.resolve():
            continue
        why = error or C.code_mismatch(meta, prov)
        if why:
            bad.append(f"{p}: {why}")
    if bad:
        raise StepFailed(f"{len(bad)} output(s) of state {s.name} were computed with other code than "
                         f"{s.checkout} has now:\n  " + "\n  ".join(bad[:20]) + "\nMove them aside first.")


def require_output_of_code(out: Path, s: C.StateDef) -> None:
    """Refuse to skip on an existing output computed with other code than the state's
    checkout has now."""
    prov = clean_provenance(s)
    why = C.code_mismatch(C.read_meta(out) or {}, prov)
    if why:
        raise StepFailed(f"{out} exists but was computed with other code ({why}); move it aside")


def check_after(s: C.StateDef, before: dict, out: Path, label: str) -> None:
    """After a step: the checkout must be as it was before the step started, and the
    output must carry those values. Otherwise the output is moved to invalid/."""
    after = C.git_provenance(s.checkout)
    reasons = [f"checkout changed during {label}: {c}" for c in C.provenance_changes(before, after)]
    if out.exists():
        meta = C.read_meta(out) or {}
        for key in ("git_sha", *C.CODE_KEYS):
            if meta.get(key) != before.get(key):
                reasons.append(f"{out.name} records {key} {meta.get(key)!r}, checkout had {before.get(key)!r}")
    if reasons:
        moved = C.quarantine(out, "\n".join(reasons)) if out.exists() else None
        log_event("invalid-output", run=label, out=str(out), moved_to=str(moved) if moved else None, reasons=reasons)
        raise StepFailed("; ".join(reasons) + (f" (output moved to {moved})" if moved else ""))


# ── Chroma servers (one per corpus, detached, tracked by pid file) ───────────
#
# Protocol section 16: one Chroma server process per corpus, started after the
# ingest, serves every L1/L2 run on that corpus. Only chroma-up starts it (also
# from `all`) and only chroma-down stops it; l1 and l2 refuse to run without it,
# record its identity before and after the run, and refuse to add outputs next to
# outputs computed against another process (a restart voids comparisons across it).

pidfile = C.chroma_pidfile
our_chroma = C.our_chroma


def chroma_up(corpus: C.CorpusDef) -> bool:
    """Start the corpus's Chroma server unless ours is already up. True if started now."""
    if our_chroma(corpus) and C.http_ok(C.chroma_heartbeat_url(corpus.chroma_port)):
        print(f"chroma {corpus.id} already up on {corpus.chroma_port}: {C.chroma_process(corpus)}")
        return False
    path = C.chroma_dir(corpus)
    if not path.is_dir() or not any(path.iterdir()):
        raise StepFailed(f"{path} is empty: ingest {corpus.id} first")
    try:
        proc = C.start_chroma(path, corpus.chroma_port, C.logs_dir() / f"chroma_{corpus.id}.log")
    except RuntimeError as e:  # port taken by another process, or the server did not come up
        raise StepFailed(str(e)) from e
    C.CONFIG.run_root.mkdir(parents=True, exist_ok=True)
    C.write_json_atomic(pidfile(corpus), {"pid": proc.pid, "port": corpus.chroma_port, "path": str(path),
                                          "started_at": C.now_iso()})
    ident = C.chroma_process(corpus)
    log_event("chroma-up", corpus=corpus.id, pid=proc.pid, port=corpus.chroma_port, process=ident)
    print(f"chroma {corpus.id} up on {corpus.chroma_port}: {ident}")
    return True


def chroma_down(corpus: C.CorpusDef) -> None:
    info = our_chroma(corpus)
    if info is None:
        print(f"no Chroma server of ours is running for {corpus.id}")
        return
    ident = C.chroma_process(corpus)
    C.stop_pid(info["pid"])
    pidfile(corpus).unlink(missing_ok=True)
    log_event("chroma-down", corpus=corpus.id, pid=info["pid"], process=ident)
    print(f"chroma {corpus.id} stopped (pid {info['pid']})")
    outputs = C.corpus_outputs(corpus.id)
    if outputs:
        ours = sum(1 for _, meta, error in outputs if ident and not error and (meta or {}).get("chroma_process") == ident)
        print(f"note: {ours} of the {len(outputs)} L1/L2 output(s) of {corpus.id} were computed against the stopped "
              f"process; runs against a new Chroma process cannot be added next to any of them (protocol section 16)")


def require_chroma(corpus: C.CorpusDef) -> dict:
    """Identity {pid, started, port} of the corpus's running Chroma server."""
    ident = C.chroma_process(corpus)
    if ident is None:
        raise StepFailed(f"no Chroma server of ours is running for {corpus.id} on port {corpus.chroma_port}; start "
                         f"it with `drive.py chroma-up --corpus {corpus.id}` (l1 and l2 never start or stop Chroma: "
                         f"one process must serve every run on a corpus)")
    return ident


def require_same_chroma(corpus: C.CorpusDef, ident: dict, replacing: Path | None = None) -> None:
    """Refuse to add outputs next to outputs of this corpus that were computed against
    another Chroma process (or whose process is unknown). `replacing` is the file a
    --force run overwrites."""
    other = C.other_chroma_outputs(corpus, ident, exclude=replacing)
    if other:
        raise StepFailed(f"{len(other)} output(s) of {corpus.id} were not computed against the running Chroma "
                         f"process {ident}:\n  " + "\n  ".join(other[:20])
                         + "\nA Chroma restart voids comparisons across it (protocol section 16): move the "
                           "corpus's outputs aside and repeat those runs against one process.")


def check_chroma_after(corpus: C.CorpusDef, before: dict, out: Path, label: str) -> None:
    """After a step: the corpus's Chroma server must still be the process captured
    before the step, and the output must record that process at its start and end.
    Otherwise the output is moved to invalid/."""
    now = C.chroma_process(corpus)
    reasons = [] if now == before else [f"Chroma process of {corpus.id} changed during {label}: {before} -> {now}"]
    if out.exists():
        meta = C.read_meta(out) or {}
        for key in ("chroma_process", "chroma_process_end"):
            if meta.get(key) != before:
                reasons.append(f"{out.name} records {key} {meta.get(key)!r}, drive captured {before!r}")
    if reasons:
        moved = C.quarantine(out, "\n".join(reasons)) if out.exists() else None
        log_event("invalid-output", run=label, out=str(out), moved_to=str(moved) if moved else None, reasons=reasons)
        raise StepFailed("; ".join(reasons) + (f" (output moved to {moved})" if moved else ""))


def running_chroma_note() -> list[str]:
    """Lines naming every Chroma server of ours that is still up, with the command to stop it."""
    lines = []
    for cid, corpus in C.CORPORA.items():
        ident = C.chroma_process(corpus)
        if ident:
            lines.append(f"  {cid}: pid {ident['pid']}, started {ident['started']}, port {ident['port']}; stop with "
                         f"`drive.py chroma-down --corpus {cid}{''.join(' ' + a for a in HIDDEN)}`")
    return lines


def fingerprint(corpus: C.CorpusDef) -> dict:
    scratch = C.make_scratch_dir()
    try:
        res = subprocess.run([str(PY_B), str(HARNESS / "common.py"), "fingerprint", "--port", str(corpus.chroma_port)],
                             capture_output=True, text=True, env=C.base_env(), cwd=str(scratch))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if res.returncode:
        raise StepFailed(f"fingerprint failed: {res.stderr[-500:]}")
    return json.loads(res.stdout.strip().splitlines()[-1])


# ── Steps ────────────────────────────────────────────────────────────────────

def do_preflight() -> None:
    out = C.CONFIG.results_root / "verification" / "preflight.json"
    run_logged([PY_B, HARNESS / "common.py", "preflight", "--out", out, *HIDDEN], C.logs_dir() / "preflight.log")


def do_env(state: str) -> None:
    run_logged([PY_B, HARNESS / "env.py", "--state", state, *HIDDEN], C.logs_dir() / f"env_{state}.log")


def do_ingest(corpus_id: str, force: bool, supersede: bool = False) -> None:
    corpus = C.CORPORA[corpus_id]
    if our_chroma(corpus):
        raise StepFailed(f"a Chroma server for {corpus_id} is running; chroma-down first")
    run_logged([PY_B, HARNESS / "ingest.py", "--corpus", corpus_id, *(["--force"] if force else []),
                *(["--supersede"] if supersede else []), *HIDDEN],
               C.logs_dir() / f"ingest_{corpus_id}.log")


def do_l1(state: str, suite: str, tag: str | None, force: bool) -> Path:
    s = require_state(state)
    corpus = C.CORPORA[C.SUITES[suite].corpus]
    _, identity = require_ingested(corpus)
    out = C.layer_path("L1", state, suite, tag)
    if out.exists() and not force:
        raise StepFailed(f"{out} exists (use --force to overwrite)")
    require_same_ingest(corpus, identity, replacing=out if force else None)
    chroma = require_chroma(corpus)          # never started here
    require_same_chroma(corpus, chroma, replacing=out if force else None)
    before = clean_provenance(s)
    require_same_code(s, before, replacing=out if force else None)
    cmd = [s.python, HARNESS / "run_layer1.py", "--state", state, "--suite", suite,
           *(["--tag", tag] if tag else []), *(["--force"] if force else []), *HIDDEN]
    env = harness_env()
    env[C.CHROMA_PROCESS_ENV] = json.dumps(chroma)
    run_logged(cmd, C.logs_dir() / f"L1_{out.stem}.log", env=env)
    check_after(s, before, out, f"L1 {out.stem}")
    check_chroma_after(corpus, chroma, out, f"L1 {out.stem}")
    require_output_of_ingest(out, identity)
    return out


def l2_target(state: str, suite: str, tag: str | None, result_chars, extra_chars, graph_empty) -> tuple[Path, str | None]:
    """Output path and tag. Informational rows (protocol 7.2) are L2/info_<S>_<tag>_<suite>.json."""
    if graph_empty:
        tag = tag or "emptygraph"
        return C.CONFIG.results_root / "L2" / f"info_{state}_{tag}_{suite}.json", tag
    if result_chars is not None:
        tag = tag or str(result_chars)
        return C.CONFIG.results_root / "L2" / f"info_{state}_{tag}_{suite}.json", tag
    if extra_chars is not None:
        tag = tag or ("killswitch" if extra_chars == 0 else f"extra{extra_chars}")
    return C.layer_path("L2", state, suite, tag), tag


def empty_graph_copy(corpus: C.CorpusDef) -> tuple[Path, dict]:
    """Copy of ck_data whose entity_cooccurrence table is empty (A as shipped)."""
    src, dst = C.ck_data_dir(corpus), C.corpus_root(corpus) / "ck_data_emptygraph"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    con = sqlite3.connect(dst / "graph.db")
    try:
        before = con.execute("SELECT COUNT(*) FROM entity_cooccurrence").fetchone()[0]
        con.execute("DELETE FROM entity_cooccurrence")
        con.commit()
        after = con.execute("SELECT COUNT(*) FROM entity_cooccurrence").fetchone()[0]
        mentions = con.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
    finally:
        con.close()
    return dst, {"source": str(src), "copy": str(dst), "edges_before": before, "edges_after": after,
                 "entity_mentions": mentions}


def require_write_probe_refused(server_log: Path, offset: int, run_name: str) -> None:
    """The part of the server log this server wrote (from byte offset) must show that
    candlekeep's startup write probe was refused before it reached Chroma: serve.py's
    "neutralised" and "blocked" lines, candlekeep's read-only line, and no
    "Write access enabled"."""
    with open(server_log, "rb") as f:
        f.seek(offset)
        lines = f.read().decode("utf-8", errors="replace").splitlines()
    wanted = {"neutralised": serve.NEUTRALISED_LINE, "blocked": serve.BLOCKED_LINE.format(method="add"),
              "read_only": READ_ONLY_LINE}
    found = {k: [line for line in lines if text in line] for k, text in wanted.items()}
    enabled = [line for line in lines if WRITE_ENABLED_LINE in line]
    missing = [k for k, hits in found.items() if not hits]
    log_event("write-probe", run=run_name, log=str(server_log), offset=offset, ok=not missing and not enabled,
              found={k: hits[:2] for k, hits in found.items()}, write_enabled=enabled[:2])
    if missing or enabled:
        raise StepFailed(f"{server_log} does not show that the server's write probe was refused before it reached "
                         f"Chroma: missing {[wanted[k] for k in missing]}"
                         + (f"; found {enabled[:2]}" if enabled else ""))


def do_l2(state: str, suite: str, tag: str | None, result_chars: int | None, extra_chars: int | None,
          graph_empty: bool, force: bool) -> Path:
    s = require_state(state)
    if not SERVE.is_file():
        raise StepFailed(f"{SERVE} missing")
    corpus = C.CORPORA[C.SUITES[suite].corpus]
    record, identity = require_ingested(corpus)
    out, tag = l2_target(state, suite, tag, result_chars, extra_chars, graph_empty)
    if out.exists() and not force:
        raise StepFailed(f"{out} exists (use --force to overwrite)")
    require_same_ingest(corpus, identity, replacing=out if force else None)
    chroma = require_chroma(corpus)          # never started here
    require_same_chroma(corpus, chroma, replacing=out if force else None)
    port = C.CONFIG.l2_port
    if C.port_in_use(port):
        raise StepFailed(f"port {port} is already in use")
    logs = C.logs_dir()
    run_name = out.stem
    label = f"L2 {run_name}"
    # The server's code provenance, captured before its process starts (the server
    # imports router/rag modules lazily, at its first search) and checked again
    # after it has stopped.
    before = clean_provenance(s)
    require_same_code(s, before, replacing=out if force else None)
    prov_file = logs / f"L2_{run_name}_provenance.json"
    C.write_json_atomic(prov_file, before)
    data_dir, graph_info = C.ck_data_dir(corpus), None
    if graph_empty:
        data_dir, graph_info = empty_graph_copy(corpus)
        log_event("empty-graph-copy", run=run_name, **graph_info)
    overrides = {}
    if result_chars is not None:
        overrides["CANDLEKEEP_RESULT_CHARS"] = result_chars
    if extra_chars is not None:
        overrides["CANDLEKEEP_RESULT_EXTRA_CHARS"] = extra_chars
    env = C.candlekeep_server_env(corpus, data_dir, port, overrides)
    env_file = logs / f"L2_{run_name}_server_env.json"
    C.write_json_atomic(env_file, env)       # "write_probe" is added once the server log proves it
    server_log = logs / f"L2_{run_name}_server.log"
    log_offset = server_log.stat().st_size if server_log.exists() else 0   # the log is appended to
    url = C.mcp_url(port)
    server_cwd = C.make_scratch_dir()
    server_cmd = [s.python, SERVE]
    proc = C.spawn(server_cmd, env, server_log, cwd=server_cwd)
    log_event("server-up", run=run_name, state=state, pid=proc.pid, port=port, data_dir=str(data_dir),
              command=[str(c) for c in server_cmd], chroma_process=chroma)
    client_env = harness_env()
    client_env[C.CHROMA_PROCESS_ENV] = json.dumps(chroma)
    failure = None
    try:
        try:
            C.wait_server_port(proc, port, 300)
        except RuntimeError as e:
            raise StepFailed(f"{e} (log: {server_log})") from e
        run_logged([PY_B, HARNESS / "common.py", "wait-ready", "--url", url, "--timeout", "900"],
                   logs / f"L2_{run_name}.log")
        require_write_probe_refused(server_log, log_offset, run_name)
        C.write_json_atomic(env_file, {**env, "write_probe": "neutralised"})
        run_logged([PY_B, HARNESS / "run_layer2.py", "--state", state, "--suite", suite, "--url", url,
                    "--server-env-file", env_file, "--server-log", server_log, "--out", out,
                    "--provenance-file", prov_file, "--gold-body", C.CEN_G_GOLD_BODY,
                    *(["--tag", tag] if tag else []), *(["--graph-empty"] if graph_empty else []),
                    *(["--force"] if force else []), *HIDDEN],
                   logs / f"L2_{run_name}.log", env=client_env)
    except StepFailed as e:  # e.g. exit 3 (tool errors): the checks below still apply
        failure = e
    finally:
        code = C.stop_process(proc, timeout=180, sig=signal.SIGINT)
        shutil.rmtree(server_cwd, ignore_errors=True)
        log_event("server-down", run=run_name, pid=proc.pid, code=code)
    try:
        check_after(s, before, out, label)
        check_chroma_after(corpus, chroma, out, label)
    except StepFailed as e:
        raise StepFailed(f"{failure}; {e}" if failure else str(e)) from e
    after = fingerprint(corpus)
    expected = record.get("collection_fingerprint")
    same = after == expected
    log_event("fingerprint", run=run_name, corpus=corpus.id, after=after, ingest=expected, same=same)
    if not same:
        moved = (C.quarantine(out, f"collection fingerprint {after} differs from the ingest record's {expected}")
                 if out.exists() else None)
        raise StepFailed(f"collection of {corpus.id} changed during {run_name}: {after} vs ingest {expected} "
                         f"(output moved to {moved})")
    if failure:
        raise failure
    require_output_of_ingest(out, identity)
    return out


def _results_snapshot(results_dir: Path, protected: Path) -> dict:
    snap = {}
    for p in results_dir.rglob("*"):
        if p.is_file() and not p.is_relative_to(protected):
            snap[str(p.relative_to(results_dir))] = C.sha256_file(p)
    return snap


def _pytest_counts(text: str) -> dict:
    counts = {}
    tail = "\n".join(text.splitlines()[-30:])
    for n, word in re.findall(r"(\d+) (passed|failed|skipped|deselected|errors?|xfailed|xpassed|warnings?)", tail):
        counts[word.rstrip("s") if word in ("errors", "warnings") else word] = int(n)
    return counts


def snapshot_results(results_dir: Path, protected: Path, backup: Path) -> tuple[dict, set]:
    """Hash and back up every file under results_dir except the protected subtree."""
    snapshot = _results_snapshot(results_dir, protected)
    for rel in snapshot:
        (backup / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(results_dir / rel, backup / rel)
    dirs = {str(p.relative_to(results_dir)) for p in results_dir.rglob("*") if p.is_dir()}
    return snapshot, dirs


def restore_results(results_dir: Path, protected: Path, snapshot: dict, dirs_before: set,
                    backup: Path) -> tuple[list, list, list]:
    """Return results_dir to the snapshot: restore changed or deleted files from the
    backup and delete only files (and empty directories) that did not exist before.
    Nothing under the protected subtree is ever touched."""
    restored, deleted, recreated = [], [], []
    for p in sorted(results_dir.rglob("*"), reverse=True):
        if p.is_relative_to(protected) or not p.is_file():
            continue
        rel = str(p.relative_to(results_dir))
        if rel not in snapshot:
            p.unlink()
            deleted.append(rel)
        elif C.sha256_file(p) != snapshot[rel]:
            shutil.copy2(backup / rel, p)
            restored.append(rel)
    for rel in snapshot:
        if not (results_dir / rel).exists():
            (results_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / rel, results_dir / rel)
            recreated.append(rel)
    for p in sorted(results_dir.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        if p.is_dir() and not p.is_relative_to(protected) \
                and str(p.relative_to(results_dir)) not in dirs_before and not any(p.iterdir()):
            p.rmdir()
    return restored, deleted, recreated


# The three router paths the project's CI compares, with its labels
# (.github/workflows/test.yml, "Explore Path (Divination)" included).
CI_PATHS = ("hybrid", "precise", "explore")
CI_LABELS = {"hybrid": "Hybrid Path (BM25 + Vector)", "precise": "Precise Path (Reranker)",
             "explore": "Explore Path (Divination)"}


def benchmark_file_problem(path: Path | None) -> str | None:
    """None if path is a router benchmark result compare_benchmarks.py can read."""
    if path is None:
        return "not produced by this run"
    if not Path(path).is_file():
        return "missing"
    try:
        summary = C.load_json(path)["summary"]
        for key in ("avg_precision", "avg_recall", "avg_latency_ms"):
            float(summary[key])
    except Exception as e:
        return f"unreadable ({type(e).__name__}: {e})"
    return None


def compare_benchmarks(s: C.StateDef, state: str, results_dir: Path, verification: Path, produced: dict) -> dict:
    """scripts/compare_benchmarks.py for hybrid, precise and explore, as CI runs it.

    * archive: against tests/results/archive (informational; the archive has no
      explore baseline, which the script, like CI, compares against zeros).
    * A (states B and C): against A's run in this environment, the decisive
      comparison of the C-14 deviation. It fails closed: a missing or unreadable
      baseline or current file for any of the three paths marks it failed, as does
      any red flag.
    Red flags are counted per path, from one script run per path; the combined,
    CI-identical table is saved as ci_<S>_compare_<name>.md."""
    script = s.checkout / "scripts" / "compare_benchmarks.py"
    baselines = {"archive": {p: results_dir / "archive" / f"router_{p}_benchmark.json" for p in CI_PATHS}}
    if state != "A":
        baselines["A"] = {p: verification / f"ci_A_router_{p}_benchmark.json" for p in CI_PATHS}

    def run_script(args: list) -> subprocess.CompletedProcess:
        return subprocess.run([str(s.python), "-I", str(script), *map(str, args)], capture_output=True, text=True,
                              env=C.base_env())

    def digest(p: Path | None) -> str | None:
        return C.sha256_file(p) if p is not None and Path(p).is_file() else None

    compare = {}
    for name, base in baselines.items():
        decisive = name == "A"
        problems, per_path, triples = [], {}, []
        for p in CI_PATHS:
            cur = Path(produced[p]) if p in produced else None
            cur_problem, base_problem = benchmark_file_problem(cur), benchmark_file_problem(base[p])
            entry = {"label": CI_LABELS[p], "baseline": str(base[p]), "baseline_sha256": digest(base[p]),
                     "baseline_problem": base_problem, "current": str(cur) if cur else None,
                     "current_sha256": digest(cur), "current_problem": cur_problem, "red_flags": None}
            if cur_problem:
                problems.append(f"{p}: current results {cur_problem}")
            if base_problem:
                problems.append(f"{p}: baseline {base[p].name} {base_problem}")
            if not cur_problem:
                triples += [CI_LABELS[p], base[p], cur]
                res = run_script([CI_LABELS[p], base[p], cur])
                entry.update({"exit": res.returncode, "red_flags": res.stdout.count("🔴"),
                              "stderr": res.stderr[-500:] or None})
                if res.returncode:
                    problems.append(f"{p}: compare_benchmarks.py exited {res.returncode}")
            per_path[p] = entry
        red = {p: e["red_flags"] for p, e in per_path.items()}
        table = None
        if triples:
            res = run_script(triples)
            md = verification / f"ci_{state}_compare_{name}.md"
            md.write_text(res.stdout + (f"\n<!-- stderr: {res.stderr} -->\n" if res.stderr else ""), encoding="utf-8")
            table = {"file": str(md), "exit": res.returncode, "red_flags": res.stdout.count("🔴")}
            if table["red_flags"] != sum(v or 0 for v in red.values()):
                problems.append(f"combined table has {table['red_flags']} red flags, per-path runs {red}")
        record = {"decisive": decisive, "script": str(script), "script_sha256": digest(script),
                  "per_path": per_path, "red_flags": red, "table": table, "problems": problems}
        if not decisive:
            record["status"] = "informational"
        elif problems:
            record.update(status="failed", reason="fail closed: " + "; ".join(problems))
        elif any(red.values()):
            record.update(status="failed", reason=f"red flags against A's run: {red}")
        else:
            record["status"] = "passed"
        compare[name] = record
    return compare


def c14_summary(state: str, exit_code, compare: dict, invalid: list | None = None) -> dict:
    """C-14 for one state: tests pass and no red flag against A's same-environment run."""
    if state == "A":
        return {"role": "baseline: A's run is the reference for B and C", "tests_passed": exit_code == 0}
    vs_a = compare.get("A") or {}
    return {"tests_passed": exit_code == 0, "compare_vs_A": vs_a.get("status", "failed"),
            "red_flags_vs_A": vs_a.get("red_flags"), "reason": vs_a.get("reason"),
            "pass": exit_code == 0 and vs_a.get("status") == "passed" and not invalid}


def do_ci_compare_only(s: C.StateDef, state: str) -> None:
    """Redo the comparisons of a finished CI run (e.g. after A's run), from the router
    results that run saved; pytest is not run."""
    verification = C.CONFIG.results_root / "verification"
    summary_path = verification / f"ci_{state}.json"
    if not summary_path.is_file():
        raise StepFailed(f"{summary_path} missing: run drive.py ci --state {state} first")
    summary = C.load_json(summary_path)
    compare = compare_benchmarks(s, state, s.checkout / "tests" / "results", verification,
                                 summary.get("router_results") or {})
    summary.update(compare=compare, compare_rerun_at=C.now_iso(),
                   c14=c14_summary(state, summary.get("exit_code"), compare, summary.get("invalid")))
    C.write_json_atomic(summary_path, summary)
    print(f"CI {state} comparisons redone: " + json.dumps(
        {k: {"status": v["status"], "red_flags": v["red_flags"]} for k, v in compare.items()}))


def do_ci(state: str, pytest_k: str | None = None, compare_only: bool = False,
          serialize_models: bool = False) -> None:
    """pytest -m "unit or (benchmark and not slow)" on MPS in the state's checkout, then
    compare_benchmarks.py; restore the checkout's tests/results afterwards.

    serialize_models (informational run only, protocol section 16): load the
    pytest_plugins/mps_serial.py plugin, which serialises model calls; refused
    unless --results-root points away from the protocol's results."""
    s = require_state(state)
    if serialize_models and C.CONFIG.results_root.resolve() == DEFAULT_RESULTS_ROOT.resolve():
        raise StepFailed("--serialize-models is informational: pass --results-root to keep its files apart")
    if compare_only:
        do_ci_compare_only(s, state)
        return
    checkout = s.checkout
    results_dir = checkout / "tests" / "results"
    protected = results_dir / "agent_view_eval"          # never touched
    verification = C.CONFIG.results_root / "verification"
    verification.mkdir(parents=True, exist_ok=True)
    before = clean_provenance(s)
    if state != "A":
        missing = [p for p in CI_PATHS if benchmark_file_problem(verification / f"ci_A_router_{p}_benchmark.json")]
        if missing:
            print(f"warning: A's router results for {missing} are missing; the decisive comparison will be "
                  f"marked failed (run ci --state A, then ci --state {state} --compare-only)", file=sys.stderr)
    # A previous CI run of this state is moved aside (never deleted), so no file of
    # it can be read as part of this run.
    previous = sorted(p for p in verification.glob(f"ci_{state}[._]*") if p.is_file())
    if previous:
        dest = verification / "previous" / f"ci_{state}_{C.utc_stamp()}"
        dest.mkdir(parents=True, exist_ok=True)
        for p in previous:
            os.replace(p, dest / p.name)
        log_event("ci-previous-moved", state=state, files=[p.name for p in previous], to=str(dest))
        print(f"moved {len(previous)} file(s) of the previous CI run of {state} to {dest}")
    backup = Path(tempfile.mkdtemp(prefix="ck_ci_backup_", dir=C.make_scratch_dir()))
    snapshot, dirs_before = snapshot_results(results_dir, protected, backup)
    status_before = C.git(checkout, "status", "--porcelain")
    ci_root = C.make_scratch_dir()
    out_txt = verification / f"ci_{state}.txt"
    if C.port_in_use(C.DEAD_PORT):
        raise StepFailed(f"port {C.DEAD_PORT} must be unused")
    # The selected tests need no Chroma server. CHROMA_URL points at a dead port so
    # the import-time background init of candlekeep.mcp.server stops at its
    # connection check: with a reachable server it goes on to load the models on MPS
    # concurrently with the tests, which aborts in Metal (observed in a smoke run).
    # The data dir is a throwaway so tests never write to the user's real one.
    env = C.base_env()
    env.update({
        "CANDLEKEEP_DEVICE": C.DEVICE,
        "CHROMA_URL": C.DEAD_CHROMA_URL,
        "CANDLEKEEP_DATA_DIR": str(ci_root / "data"),
        "XDG_DATA_HOME": str(ci_root / "xdg"),
        "PYTHONPATH": str(checkout / "src") + (f":{HARNESS / 'pytest_plugins'}" if serialize_models else ""),
    })
    cmd = [s.python, "-m", "pytest", "-m", "unit or (benchmark and not slow)", "-v", "-s",
           *(["-p", "mps_serial"] if serialize_models else []), *(["-k", pytest_k] if pytest_k else [])]
    header = (f"# CI run for state {state}\n# checkout: {checkout}\n# git_sha: {before['git_sha']}\n"
              f"# src_tree_sha: {before['src_tree_sha']}\n# command: {' '.join(map(str, cmd))}\n"
              f"# env: {json.dumps({k: v for k, v in env.items() if k != 'PATH'})}\n# started_at: {C.now_iso()}\n")
    out_txt.write_text(header, encoding="utf-8")
    code, seconds, counts, produced, compare = None, None, {}, {}, {}
    try:
        t0 = time.monotonic()
        try:
            code = run_logged(cmd, out_txt, env=env, cwd=checkout, ok_codes=None, timeout=4 * 3600)
        finally:
            shutil.rmtree(ci_root, ignore_errors=True)
        seconds = round(time.monotonic() - t0, 1)
        counts = _pytest_counts(out_txt.read_text(encoding="utf-8"))
        # Keep this run's router benchmark results (the checkout's copies are restored
        # below). A previous run's copies were moved aside before this run started.
        for path in CI_PATHS:
            dst = verification / f"ci_{state}_router_{path}_benchmark.json"
            f = results_dir / f"router_{path}_benchmark.json"
            if f.is_file() and C.sha256_file(f) != snapshot.get(f.name):
                shutil.copy2(f, dst)
                produced[path] = str(dst)
        compare = compare_benchmarks(s, state, results_dir, verification, produced)
    finally:
        # Restore tests/results to the pre-run state; delete only what the run created.
        restored, deleted, recreated = restore_results(results_dir, protected, snapshot, dirs_before, backup)
        shutil.rmtree(backup.parent, ignore_errors=True)
    status_after = C.git(checkout, "status", "--porcelain")
    after = C.git_provenance(checkout)
    invalid = [f"checkout changed during the CI run: {c}" for c in C.provenance_changes(before, after)]
    summary = {
        "state": state, "checkout": str(checkout),
        "git_sha": before["git_sha"], "src_tree_sha": before["src_tree_sha"], "src_dirty": before["src_dirty"],
        "provenance_before": before, "provenance_after": after, "provenance_unchanged": not invalid,
        "command": [str(c) for c in cmd],
        "exit_code": code, "passed": code == 0, "seconds": seconds, "counts": counts,
        "output": str(out_txt), "router_results": produced, "compare": compare,
        "c14": c14_summary(state, code, compare, invalid),
        "restored": restored, "deleted_created_files": deleted, "recreated": recreated,
        "git_status_unchanged": status_before == status_after,
        "git_status_before": status_before.splitlines(), "git_status_after": status_after.splitlines(),
        "finished_at": C.now_iso(),
    }
    if invalid:
        summary["invalid"] = invalid
    C.write_json_atomic(verification / f"ci_{state}.json", summary)
    print(f"CI {state}: exit {code} {counts}; restored {len(restored)}, deleted {len(deleted)}; "
          f"git status unchanged: {summary['git_status_unchanged']}")
    for name, cmp_ in compare.items():
        print(f"  compare vs {name}: {cmp_['status']} red flags {cmp_['red_flags']}"
              + (f" ({cmp_['reason']})" if cmp_.get("reason") else ""))
    print(f"  C-14 ({state}): {summary['c14']}")
    if invalid:
        raise StepFailed("; ".join(invalid))


def l2_has_errors(path: Path) -> bool:
    doc = C.load_json(path)
    return any(m.get("errors") for m in doc.get("metrics", {}).values())


def do_all(states: list, corpora: list, skip_ci: bool) -> None:
    """Section 11 without judging and verification. Skips outputs that already exist,
    but only those computed on the corpus's current ingest with the state's current
    code; any other existing output stops the run. Each corpus's Chroma server is
    started once, after the ingests and before the corpus's first run that is not
    skipped (or reused if chroma-up already started it), and is never stopped here:
    every L1/L2 run on the corpus, now or in a later `all`, must use that process."""
    chroma_ready: set = set()

    def ensure_chroma(corpus: C.CorpusDef) -> None:
        if corpus.id not in chroma_ready:  # once per corpus; a server that dies later fails the next run
            chroma_up(corpus)
            chroma_ready.add(corpus.id)

    def step(label, fn, out: Path | None = None, corpus: C.CorpusDef | None = None, state: str | None = None,
             needs_chroma: bool = False):
        if out is not None and out.exists():
            if corpus is not None:
                _, identity = require_ingested(corpus)
                require_output_of_ingest(out, identity)
            if state is not None:
                require_output_of_code(out, C.STATES[state])
            if out.parent.name == "L2" and l2_has_errors(out):
                raise StepFailed(f"{out} exists but has tool errors; inspect it, then rerun with --force")
            print(f"skip {label}: {out} exists")
            return
        print(f"\n=== {label}")
        if needs_chroma:
            ensure_chroma(corpus)
        fn()

    for st in states:
        step(f"env {st}", lambda st=st: do_env(st), C.CONFIG.results_root / "env" / f"{st}.txt")
    for cid in corpora:
        corpus = C.CORPORA[cid]
        rec = ingest_record(corpus)
        if not (rec and rec.get("ok")):
            step(f"ingest {cid}", lambda cid=cid: do_ingest(cid, False))
    try:
        for cid in corpora:
            corpus = C.CORPORA[cid]
            suites = C.suites_of_corpus(cid)
            for suite in suites:
                for st, tag in [("B", None), *([("B", "rerun")] if suite == "CEN" else []), ("A", None), ("C", None)]:
                    if st in states:
                        step(f"L1 {st} {suite} {tag or ''}",
                             lambda st=st, suite=suite, tag=tag: do_l1(st, suite, tag, False),
                             C.layer_path("L1", st, suite, tag), corpus=corpus, state=st, needs_chroma=True)
            for suite in suites:
                runs = [("B", None, {}), *([("B", "rerun", {})] if suite == "CEN" else []), ("A", None, {}),
                        ("C", None, {})]
                if suite == "CEN":
                    runs.append(("C", None, {"extra_chars": 0}))
                if suite in ("CEN", "MH"):
                    runs += [("A", None, {"graph_empty": True}), ("B", None, {"result_chars": 500})]
                for st, tag, kw in runs:
                    if st not in states:
                        continue
                    out, _ = l2_target(st, suite, tag, kw.get("result_chars"), kw.get("extra_chars"),
                                       kw.get("graph_empty", False))
                    step(f"L2 {out.stem}", lambda st=st, suite=suite, tag=tag, kw=kw: do_l2(
                        st, suite, tag, kw.get("result_chars"), kw.get("extra_chars"), kw.get("graph_empty", False),
                        False), out, corpus=corpus, state=st, needs_chroma=True)
        if not skip_ci:  # the CI run uses no Chroma server (CHROMA_URL is the dead port)
            for st in [s for s in ("A", "B", "C") if s in states]:
                step(f"CI {st}", lambda st=st: do_ci(st), C.CONFIG.results_root / "verification" / f"ci_{st}.json")
    finally:
        running = running_chroma_note()
        if running:
            print("\nChroma servers left running (every later run on these corpora must use the same process; "
                  "protocol section 16):", *running, sep="\n")


def do_status() -> None:
    root = C.CONFIG.results_root
    print(f"results root: {root}")
    for st in C.STATES:
        print(f"  env/{st}.txt: {'yes' if (root / 'env' / f'{st}.txt').exists() else '-'}")
    for cid, corpus in C.CORPORA.items():
        our_chroma(corpus)  # drops a stale pid file
        ident = C.chroma_process(corpus)
        up = f" (chroma up: pid {ident['pid']}, started {ident['started']}, port {ident['port']})" if ident else ""
        if not C.ingest_record_path(corpus).exists() and not C.failed_record_path(corpus).exists():
            state = "-"
        else:
            try:
                _, identity = C.current_ingest(corpus)
                stale = C.stale_outputs(corpus, identity)
                state = f"ok {identity['ingest_uuid']}"
                if stale:
                    state += f", {len(stale)} output(s) of OTHER ingests"
                other = C.other_chroma_outputs(corpus, ident) if ident else []
                if other:
                    state += f", {len(other)} output(s) of ANOTHER Chroma process"
            except C.IngestError as e:
                state = f"NOT USABLE: {e}"
        print(f"{cid} {corpus.name}: ingest {state}{up}")
        for suite in C.suites_of_corpus(cid):
            l1 = "".join(st if C.layer_path("L1", st, suite).exists() else "." for st in C.STATES)
            l2 = "".join(st if C.layer_path("L2", st, suite).exists() else "." for st in C.STATES)
            print(f"   {suite:8} L1 [{l1}]  L2 [{l2}]")
    extra = sorted(p.name for p in (root / "L2").glob("*_*_*.json")) if (root / "L2").is_dir() else []
    extra += sorted(p.name for p in (root / "L1").glob("*_*_*.json")) if (root / "L1").is_dir() else []
    if extra:
        print("tagged/informational:", ", ".join(extra))
    for st, s in C.STATES.items():
        if not s.checkout.exists():
            print(f"state {st}: checkout {s.checkout} missing")
            continue
        prov = C.git_provenance(s.checkout)
        other = [p.name for p, meta, error in C.state_outputs(st) if error or C.code_mismatch(meta, prov)]
        notes = C.provenance_problems(prov)
        if other:
            notes.append(f"{len(other)} output(s) from other code: {other[:5]}")
        print(f"state {st}: HEAD {prov['git_sha'][:12]} src {prov['src_tree_sha'][:12]}"
              + ("".join(f"\n   ! {n}" for n in notes)))
    for st in C.STATES:
        f = root / "verification" / f"ci_{st}.json"
        if f.exists():
            ci = C.load_json(f)
            print(f"CI {st}: exit {ci['exit_code']} {ci['counts']}; C-14 {ci.get('c14')}")
    invalid = sorted(str(p.relative_to(root)) for p in (root / "invalid").rglob("*.json")) \
        if (root / "invalid").is_dir() else []
    if invalid:
        print("invalid (quarantined) outputs:", ", ".join(invalid))


def do_verify(extra: list) -> None:
    """verify.py (written independently; not part of `all`) with the harness's CEN-G
    gold body and CI paths passed explicitly, so both sides use the same rules
    whatever the defaults, plus any further verify.py arguments."""
    script = HARNESS / "verify.py"
    if not script.is_file():
        raise StepFailed(f"{script} missing")
    scratch = C.make_scratch_dir()
    env = harness_env()
    # In case verify.py imports candlekeep: a dead Chroma URL and a throwaway data
    # dir for the import-time background thread.
    env.update({"CHROMA_URL": C.DEAD_CHROMA_URL, "CANDLEKEEP_DATA_DIR": str(scratch)})
    try:
        run_logged([PY_B, script, "--gold-body", C.CEN_G_GOLD_BODY, "--ci-paths", ",".join(CI_PATHS),
                    "--root", C.CONFIG.results_root, *extra], C.logs_dir() / "verify.log", env=env)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight")
    p = sub.add_parser("env")
    p.add_argument("--state", choices=sorted(C.STATES))
    p = sub.add_parser("ingest")
    p.add_argument("--corpus", required=True)
    p.add_argument("--force", action="store_true", help="delete the corpus's data and ingest again")
    p.add_argument("--supersede", action="store_true",
                   help="with --force: move the outputs of the old ingest (and its record) to superseded/")
    for name, text in (("chroma-up", "start the corpus's Chroma server; it serves every L1/L2 run on the corpus"),
                       ("chroma-down", "stop it (runs added after a restart cannot be combined with earlier ones)")):
        sub.add_parser(name, help=text).add_argument("--corpus", required=True)
    p = sub.add_parser("l1")
    p.add_argument("--state", required=True, choices=sorted(C.STATES))
    p.add_argument("--suite", required=True)
    p.add_argument("--tag")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("l2")
    p.add_argument("--state", required=True, choices=sorted(C.STATES))
    p.add_argument("--suite", required=True)
    p.add_argument("--tag")
    p.add_argument("--result-chars", type=int, help="CANDLEKEEP_RESULT_CHARS for the server (informational row)")
    p.add_argument("--extra-chars", type=int, help="CANDLEKEEP_RESULT_EXTRA_CHARS for the server (0 = kill switch)")
    p.add_argument("--graph-empty", action="store_true", help="serve from a ck_data copy with an empty graph")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("ci")
    p.add_argument("--state", required=True, choices=sorted(C.STATES))
    p.add_argument("--compare-only", action="store_true",
                   help="redo the benchmark comparisons of the state's last CI run without running pytest")
    p.add_argument("--pytest-k", help=argparse.SUPPRESS)  # smoke tests only: restrict the selection
    p.add_argument("--serialize-models", action="store_true",
                   help="informational run: serialise model calls (needs --results-root)")
    p = sub.add_parser("all")
    p.add_argument("--states", default="A,B,C")
    p.add_argument("--corpora", default="I01,I02,I03,I04,I05,I06,I07,I08,I09")
    p.add_argument("--skip-ci", action="store_true")
    sub.add_parser("status")
    sub.add_parser("verify", help="run verify.py with the harness's --gold-body and --ci-paths; "
                                  "other arguments go to verify.py (e.g. --all --check-doc)")
    for sp in sub.choices.values():
        C.add_hidden_args(sp)
    args, extra = ap.parse_known_args()
    if extra and args.cmd != "verify":
        ap.error(f"unrecognized arguments: {' '.join(extra)}")
    C.apply_overrides(args)
    HIDDEN.extend(C.hidden_argv(args))
    try:
        if args.cmd == "preflight":
            do_preflight()
        elif args.cmd == "env":
            for st in ([args.state] if args.state else list(C.STATES)):
                do_env(st)
        elif args.cmd == "ingest":
            do_ingest(args.corpus, args.force, args.supersede)
        elif args.cmd == "chroma-up":
            chroma_up(C.CORPORA[args.corpus])
        elif args.cmd == "chroma-down":
            chroma_down(C.CORPORA[args.corpus])
        elif args.cmd == "l1":
            do_l1(args.state, args.suite, args.tag, args.force)
        elif args.cmd == "l2":
            do_l2(args.state, args.suite, args.tag, args.result_chars, args.extra_chars, args.graph_empty, args.force)
        elif args.cmd == "ci":
            do_ci(args.state, args.pytest_k, args.compare_only, args.serialize_models)
        elif args.cmd == "all":
            do_all([s for s in args.states.split(",") if s], [c for c in args.corpora.split(",") if c], args.skip_ci)
        elif args.cmd == "status":
            do_status()
        elif args.cmd == "verify":
            do_verify(extra)
    except StepFailed as e:
        print(f"FAILED: {e}", file=sys.stderr)
        log_event("failed", cmd=args.cmd, error=str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
