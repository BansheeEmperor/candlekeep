#!/usr/bin/env python3
"""Performance of the MPS model-call lock, measured through the MCP server.

Runs one state of the code (a src directory) through the scenarios below. Each
scenario gets its own fresh throwaway Chroma server and Candlekeep HTTP server on
MPS (rate limits off), so a crash in one does not affect the others. Every server
first ingests the corpus, which is measured each time:

  ingest       ingest tests/fixtures/scale_docs. Measures the call's duration
               and the time until the background normalisation map exists.
  sequential   one client, the 108 Centurion queries per path. Measures latency.
  concurrent-<path>  16 sessions at once, the 108 queries spread over them.
               Measures throughput and latency.
  overlap      re-ingest scale_docs while 4 sessions keep searching (hybrid),
               then keep searching for 20 s more. Records crashes, failed
               searches and search latency.

    python scripts/benchmark_model_lock.py --src <checkout>/src --label B-lock --out result.json

Run the states to be compared alternately: run-to-run drift on a laptop is of
the same order as small effects.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from fastmcp import Client

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
PATHS = ("hybrid", "precise", "explore")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))]


def summary(lat: list[float]) -> dict:
    return {"n": len(lat), "p50_ms": pct(lat, 0.5), "p95_ms": pct(lat, 0.95), "max_ms": max(lat) if lat else None,
            "mean_ms": statistics.mean(lat) if lat else None}


async def call(url: str, tool: str, args: dict, timeout: float = 60) -> tuple[str, float]:
    t0 = time.perf_counter()
    async with Client(url, timeout=timeout) as c:
        r = await c.call_tool(tool, args)
    return r.content[0].text, (time.perf_counter() - t0) * 1000


async def wait_ready(url: str) -> None:
    for _ in range(240):
        try:
            text, _ = await call(url, "get_stats", {}, timeout=30)
            if "Loading" not in text:
                return
        except Exception:
            pass
        await asyncio.sleep(0.5)
    raise SystemExit("server did not become ready")


def variants(stats: str) -> int:
    for line in stats.splitlines():
        if "Normalisation map variants" in line:
            return int(line.rsplit(":", 1)[1].strip().replace(",", ""))
    return 0


async def scenario_ingest(url: str, path: str) -> dict:
    t0 = time.perf_counter()
    text, ms = await call(url, "ingest", {"path": path}, timeout=900)
    t1 = time.perf_counter()
    while True:
        stats, _ = await call(url, "get_stats", {})
        if variants(stats) > 0 or time.perf_counter() - t1 > 300:
            break
        await asyncio.sleep(0.25)
    return {"ingest_ms": ms, "rebuild_ms": (time.perf_counter() - t1) * 1000,
            "total_ms": (time.perf_counter() - t0) * 1000, "result": text.splitlines()[0][:120]}


async def scenario_sequential(url: str, queries: list[str]) -> dict:
    out = {}
    for path in PATHS:
        for q in queries[:5]:                       # warm-up
            await call(url, "search", {"query": q, "query_type": path})
        lat = [(await call(url, "search", {"query": q, "query_type": path}))[1] for q in queries]
        out[path] = summary(lat)
    return out


async def scenario_concurrent(url: str, queries: list[str], path: str, workers: int = 16) -> dict:
    out = {}
    for path in (path,):
        lat: list[float] = []

        async def worker(k: int):
            async with Client(url, timeout=60) as c:
                for q in queries[k::workers]:
                    t0 = time.perf_counter()
                    await c.call_tool("search", {"query": q, "query_type": path})
                    lat.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        await asyncio.gather(*(worker(k) for k in range(workers)))
        wall = time.perf_counter() - t0
        out[path] = {**summary(lat), "wall_s": wall, "qps": len(lat) / wall}
    return out


async def scenario_overlap(url: str, path: str, queries: list[str], searchers: int = 4, after_s: float = 20) -> dict:
    state = {"stop": False, "during": [], "after": [], "failed": 0, "first_error": None, "phase": "during"}

    async def searcher(k: int):
        i = k
        while not state["stop"]:
            q = queries[i % len(queries)] + f" ({i})"   # distinct text: no embedding-cache hits
            i += searchers
            try:
                _, ms = await call(url, "search", {"query": q, "query_type": "hybrid"}, timeout=60)
                state[state["phase"]].append(ms)
            except Exception as e:
                state["failed"] += 1
                state["first_error"] = state["first_error"] or repr(e)[:200]
                await asyncio.sleep(0.5)

    tasks = [asyncio.create_task(searcher(k)) for k in range(searchers)]
    await asyncio.sleep(1)
    t0 = time.perf_counter()
    try:
        text, ms = await call(url, "ingest", {"path": path}, timeout=900)
    except Exception as e:
        text, ms = f"ingest failed: {e!r}"[:200], (time.perf_counter() - t0) * 1000
    state["phase"] = "after"
    await asyncio.sleep(after_s)
    state["stop"] = True
    await asyncio.gather(*tasks, return_exceptions=True)
    return {"ingest_ms": ms, "ingest_result": text.splitlines()[0][:160], "failed_searches": state["failed"],
            "first_error": state["first_error"], "during_ingest": summary(state["during"]),
            "after_ingest": summary(state["after"])}


# Diagnostic only (--lock-stats): replaces candlekeep.model_lock._MPS_LOCK in the server
# with a timing wrapper. Callers are classified from the stack; stats are written every second.
LOCK_STATS_PATCH = (
    "import json as _j, os as _o, threading as _t, time as _tm, traceback as _tb\n"
    "import candlekeep.model_lock as _ml\n"
    "class _Timed:\n"
    "    def __init__(s, inner): s.inner, s.mu, s.loc, s.stats = inner, _t.Lock(), _t.local(), {}\n"
    "    def _kind(s):\n"
    "        names = ' '.join(f.name for f in _tb.extract_stack(limit=40))\n"
    "        for k, w in (('rebuild', '_rebuild_worker'), ('ingest', 'add_documents'), ('search', 'search_with_routing'),\n"
    "                     ('calibration', '_calibrate_semaphore'), ('warmup', 'warm_up'), ('warmup', '_background_init')):\n"
    "            if w in names: return k\n"
    "        return 'other'\n"
    "    def __enter__(s):\n"
    "        d = getattr(s.loc, 'd', 0)\n"
    "        if d == 0: s.loc.k = s._kind()\n"
    "        t0 = _tm.perf_counter(); s.inner.acquire(); t1 = _tm.perf_counter()\n"
    "        s.loc.d = d + 1\n"
    "        if d == 0:\n"
    "            s.loc.t1 = t1\n"
    "            with s.mu:\n"
    "                st = s.stats.setdefault(s.loc.k, {'n': 0, 'wait_s': 0.0, 'max_wait_s': 0.0, 'hold_s': 0.0, 'max_hold_s': 0.0})\n"
    "                st['n'] += 1; st['wait_s'] += t1 - t0; st['max_wait_s'] = max(st['max_wait_s'], t1 - t0)\n"
    "        return s\n"
    "    def __exit__(s, *a):\n"
    "        s.loc.d -= 1\n"
    "        if s.loc.d == 0:\n"
    "            h = _tm.perf_counter() - s.loc.t1\n"
    "            with s.mu:\n"
    "                st = s.stats[s.loc.k]; st['hold_s'] += h; st['max_hold_s'] = max(st['max_hold_s'], h)\n"
    "        s.inner.release()\n"
    "_ml._MPS_LOCK = _Timed(_ml._MPS_LOCK)\n"
    "def _dump():\n"
    "    while True:\n"
    "        _tm.sleep(1)\n"
    "        with _ml._MPS_LOCK.mu: data = _j.dumps(_ml._MPS_LOCK.stats)\n"
    "        open(_o.environ['BENCH_LOCK_STATS'] + '.tmp', 'w').write(data)\n"
    "        _o.replace(_o.environ['BENCH_LOCK_STATS'] + '.tmp', _o.environ['BENCH_LOCK_STATS'])\n"
    "_t.Thread(target=_dump, daemon=True).start()\n"
)


def run_on_fresh_server(src: Path, name: str, corpus: str, run, lock_stats: bool = False) -> dict:
    """Start Chroma and a Candlekeep server on src, ingest corpus, run one scenario."""
    tmp = Path(tempfile.mkdtemp(prefix="ck_lock_bench_"))
    cport, sport = free_port(), free_port()
    chroma = subprocess.Popen([str(Path(PY).parent / "chroma"), "run", "--host", "127.0.0.1", "--port", str(cport),
                               "--path", str(tmp / "chroma")], stdout=open(tmp / "chroma.log", "w"), stderr=subprocess.STDOUT)
    env = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME", "TMPDIR", "LANG") if k in os.environ}
    env.update({"PATH": "/usr/bin:/bin", "PYTHONPATH": str(src.resolve()), "PYTHONUNBUFFERED": "1",
                "ANONYMIZED_TELEMETRY": "False", "CHROMA_URL": f"http://127.0.0.1:{cport}",
                "CANDLEKEEP_DATA_DIR": str(tmp / "data"), "CANDLEKEEP_TRANSPORT": "http",
                "CANDLEKEEP_HTTP_HOST": "127.0.0.1", "CANDLEKEEP_HTTP_PORT": str(sport), "CANDLEKEEP_DEVICE": "mps",
                "CANDLEKEEP_RATE_LIMIT_SEARCH": "0", "CANDLEKEEP_RATE_LIMIT_WRITE": "0", "PYTHONHASHSEED": "20261018"})
    code = ("import faulthandler, importlib, candlekeep, sys; faulthandler.enable(); "
            "print('candlekeep from', candlekeep.__file__, file=sys.stderr); "
            + (LOCK_STATS_PATCH if lock_stats else "") +
            "importlib.import_module('candlekeep.mcp.server').main()")
    if lock_stats:
        env["BENCH_LOCK_STATS"] = str(tmp / "lock_stats.json")
    time.sleep(4)
    server = subprocess.Popen([PY, "-c", code], env=env, cwd=tmp, stdout=open(tmp / "server.log", "w"),
                              stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{sport}/mcp"
    out: dict = {"status": "ok"}
    async def watched(coro):
        """Run coro, but stop as soon as the server process exits (its clients would wait for their timeouts)."""
        task = asyncio.ensure_future(coro)
        while not task.done():
            if server.poll() is not None:
                task.cancel()
                raise RuntimeError(f"server exited with {server.poll()}")
            await asyncio.sleep(0.5)
        return task.result()

    try:
        asyncio.run(watched(wait_ready(url)))
        out["ingest"] = asyncio.run(watched(scenario_ingest(url, corpus)))
        out["result"] = asyncio.run(watched(run(url)))
    except BaseException as e:   # a crashed server surfaces as a client timeout or connection error
        out["status"] = f"error: {e!r}"[:300]
    finally:
        time.sleep(1)
        out["server_exit_code"] = server.poll()
        if out["server_exit_code"] is not None:
            out["status"] = "server crashed" + (f" ({out['status']})" if out["status"] != "ok" else "")
        log = (tmp / "server.log").read_text(errors="replace")
        lines = log.splitlines()
        out["crash"] = [l for l in lines if "failed assertion" in l or "Fatal Python" in l][:3]
        out["crash_stack"] = next((lines[i + 2:i + 6] for i, l in enumerate(lines) if l.startswith("Current thread")), None)
        out["imported_from"] = next((l for l in lines if l.startswith("candlekeep from")), None)
        time.sleep(1.5)                     # one more stats write after the scenario ends
        server.terminate()
        chroma.terminate()
        for p in (server, chroma):
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
        if lock_stats and (tmp / "lock_stats.json").exists():
            try:
                out["lock_stats"] = json.loads((tmp / "lock_stats.json").read_text())
            except ValueError as e:
                out["lock_stats"] = {"error": repr(e)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, type=Path, help="the src directory of the code to measure")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--only", help="comma-separated scenario names to run (default: all)")
    ap.add_argument("--lock-stats", action="store_true",
                    help="diagnostic: run only the overlap scenario, timing every MPS-lock acquisition by caller")
    args = ap.parse_args()
    queries = [q["query"] for q in json.loads((REPO / "tests/fixtures/eval_suite_100.json").read_text())["queries"]]
    corpus = str(REPO / "tests/fixtures/scale_docs")
    result = {"label": args.label, "src": str(args.src), "scenarios": {}}
    scenarios = {
        "sequential": lambda url: scenario_sequential(url, queries),
        **{f"concurrent-{p}": (lambda url, p=p: scenario_concurrent(url, queries, p)) for p in PATHS},
        "overlap": lambda url: scenario_overlap(url, corpus, queries),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.lock_stats:
        scenarios = {"overlap": scenarios["overlap"]}
    if args.only:
        scenarios = {k: v for k, v in scenarios.items() if k in args.only.split(",")}
    for name, run in scenarios.items():
        result["scenarios"][name] = run_on_fresh_server(args.src, name, corpus, run, lock_stats=args.lock_stats)
        print(f"{args.label} {name}: {json.dumps(result['scenarios'][name].get('status'))}", flush=True)
        args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")   # after every scenario
    return 0


if __name__ == "__main__":
    sys.exit(main())
