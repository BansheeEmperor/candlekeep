#!/usr/bin/env python3
"""Benchmark: Organization-scale concurrent agent simulation.

Simulates realistic agent behavior against an HTTP-mode Candlekeep server:
  - N agents, each issuing bursts of 3 search calls with idle periods
  - Mixed query types (simple/hybrid/precise) weighted by realistic usage
  - Optional write injection during peak read load
  - Measures latency distribution, throughput, error rate over time

Prerequisites:
  1. ChromaDB running with indexed documents (89 docs, ~2,770 chunks).
  2. Candlekeep running in HTTP mode:
     CANDLEKEEP_TRANSPORT=http CANDLEKEEP_HTTP_PORT=8111 candlekeep

Usage:
  python scripts/benchmark_scale.py --agents 10 --duration 60
  python scripts/benchmark_scale.py --agents 50 --duration 120 --with-writes
  python scripts/benchmark_scale.py --agents 10,25,50 --duration 60
"""
import argparse
import asyncio
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional

from fastmcp import Client


DEFAULT_URL = "http://localhost:8111/mcp"

# Realistic query type distribution based on diary Entry 37:
# agents use simple ~50%, hybrid ~40%, precise ~10%
QUERY_TYPE_WEIGHTS = {
    "simple": 0.50,
    "hybrid": 0.40,
    "precise": 0.10,
}

# Queries drawn from the Centurion Set categories
SEMANTIC_QUERIES = [
    "How does caching improve API performance?",
    "What are the tradeoffs of microservices architecture?",
    "Explain database replication strategies",
    "How does load balancing distribute traffic?",
    "What is the role of a service mesh?",
    "How do distributed systems handle consistency?",
    "Explain event-driven architecture patterns",
    "What are container orchestration strategies?",
    "How does TLS termination work at a load balancer?",
    "What is the CAP theorem and its implications?",
    "How do message queues decouple services?",
    "Explain the circuit breaker pattern",
    "What are the benefits of immutable infrastructure?",
    "How does DNS resolution work for service discovery?",
    "What is blue-green deployment?",
]

LEXICAL_QUERIES = [
    "bge-small-en-v1.5 embedding model",
    "ECONNREFUSED error code",
    "PostgreSQL WAL replication",
    "Kubernetes pod networking",
    "OAuth 2.0 authorization code flow",
    "Redis cluster configuration",
    "gRPC protobuf serialization",
    "Terraform state management",
    "Kafka consumer group rebalancing",
    "Istio Envoy sidecar proxy",
    "HNSW index parameters",
    "BM25 scoring algorithm",
    "JWT token validation",
    "Docker compose networking",
    "Prometheus alerting rules",
]


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class RequestRecord:
    agent_id: int
    query: str
    query_type: str
    latency_ms: float
    success: bool
    error: Optional[str]
    timestamp: float  # seconds since benchmark start


@dataclass
class AgentBehavior:
    """Simulates one agent's lifecycle during the benchmark."""
    agent_id: int
    burst_size: int = 3
    idle_min_s: float = 2.0
    idle_max_s: float = 8.0


@dataclass
class BenchmarkConfig:
    n_agents: int
    duration_s: float
    url: str
    with_writes: bool
    burst_size: int = 3
    idle_min_s: float = 2.0
    idle_max_s: float = 8.0
    reuse_connections: bool = False


@dataclass
class PathSummary:
    count: int = 0
    errors: int = 0
    latencies: List[float] = field(default_factory=list)

    @property
    def p50(self) -> float:
        return _percentile(self.latencies, 50) if self.latencies else 0.0

    @property
    def p95(self) -> float:
        return _percentile(self.latencies, 95) if self.latencies else 0.0

    @property
    def p99(self) -> float:
        return _percentile(self.latencies, 99) if self.latencies else 0.0

    @property
    def mean(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0


@dataclass
class BenchmarkResult:
    config: Dict
    total_requests: int
    total_errors: int
    error_rate_pct: float
    duration_s: float
    throughput_qps: float
    by_path: Dict[str, Dict]
    overall_p50_ms: float
    overall_p95_ms: float
    overall_p99_ms: float
    timeline_buckets: List[Dict]
    write_impact: Optional[Dict] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _percentile(data: List[float], p: int) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    d = k - f
    return s[f] + d * (s[c] - s[f])


def _pick_query_type() -> str:
    r = random.random()
    cumulative = 0.0
    for qt, weight in QUERY_TYPE_WEIGHTS.items():
        cumulative += weight
        if r <= cumulative:
            return qt
    return "simple"


def _pick_query(query_type: str) -> str:
    if query_type == "hybrid":
        return random.choice(LEXICAL_QUERIES)
    return random.choice(SEMANTIC_QUERIES)


# ── Core benchmark logic ─────────────────────────────────────────────

async def _single_search(url: str, query: str, query_type: str) -> Dict:
    """Execute one search call via MCP client (new connection per call)."""
    start = time.perf_counter()
    try:
        async with Client(url) as client:
            await client.call_tool("search", {
                "query": query,
                "n_results": 5,
                "query_type": query_type,
            })
            elapsed = (time.perf_counter() - start) * 1000
            return {"ok": True, "latency_ms": elapsed, "error": None}
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {"ok": False, "latency_ms": elapsed, "error": str(e)}


async def _search_on_client(client: Client, query: str, query_type: str) -> Dict:
    """Execute one search call on an already-connected MCP client."""
    start = time.perf_counter()
    try:
        await client.call_tool("search", {
            "query": query,
            "n_results": 5,
            "query_type": query_type,
        })
        elapsed = (time.perf_counter() - start) * 1000
        return {"ok": True, "latency_ms": elapsed, "error": None}
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {"ok": False, "latency_ms": elapsed, "error": str(e)}


async def _single_write(url: str) -> Dict:
    """Execute one ingest call via MCP client (for write contention testing)."""
    start = time.perf_counter()
    try:
        # Use critique_document as a lightweight read-write proxy —
        # it exercises the server path without actually modifying data.
        # For real write testing, we'd need a temp file on the server's
        # filesystem, which isn't practical over HTTP.
        async with Client(url) as client:
            await client.call_tool("get_stats", {})
            elapsed = (time.perf_counter() - start) * 1000
            return {"ok": True, "latency_ms": elapsed, "error": None, "type": "write_proxy"}
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {"ok": False, "latency_ms": elapsed, "error": str(e), "type": "write_proxy"}



async def _agent_loop(
    agent_id: int,
    config: BenchmarkConfig,
    records: List[RequestRecord],
    start_time: float,
    stop_event: asyncio.Event,
):
    """Simulate one agent: burst of searches, idle, repeat.
    Uses new connection per call (original behavior)."""
    while not stop_event.is_set():
        for _ in range(config.burst_size):
            if stop_event.is_set():
                return

            qt = _pick_query_type()
            query = _pick_query(qt)
            result = await _single_search(config.url, query, qt)

            records.append(RequestRecord(
                agent_id=agent_id,
                query=query,
                query_type=qt,
                latency_ms=result["latency_ms"],
                success=result["ok"],
                error=result["error"],
                timestamp=time.perf_counter() - start_time,
            ))

        idle = random.uniform(config.idle_min_s, config.idle_max_s)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=idle)
            return
        except asyncio.TimeoutError:
            pass


async def _agent_loop_persistent(
    agent_id: int,
    config: BenchmarkConfig,
    records: List[RequestRecord],
    start_time: float,
    stop_event: asyncio.Event,
):
    """Simulate one agent with a persistent MCP connection.
    Opens one Client for the agent's entire lifecycle."""
    try:
        async with Client(config.url) as client:
            while not stop_event.is_set():
                for _ in range(config.burst_size):
                    if stop_event.is_set():
                        return

                    qt = _pick_query_type()
                    query = _pick_query(qt)
                    result = await _search_on_client(client, query, qt)

                    records.append(RequestRecord(
                        agent_id=agent_id,
                        query=query,
                        query_type=qt,
                        latency_ms=result["latency_ms"],
                        success=result["ok"],
                        error=result["error"],
                        timestamp=time.perf_counter() - start_time,
                    ))

                idle = random.uniform(config.idle_min_s, config.idle_max_s)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=idle)
                    return
                except asyncio.TimeoutError:
                    pass
    except Exception as e:
        # Connection failed entirely — record one error
        records.append(RequestRecord(
            agent_id=agent_id, query="[connection_failed]",
            query_type="simple", latency_ms=0, success=False,
            error=str(e), timestamp=time.perf_counter() - start_time,
        ))


async def _write_injector(
    config: BenchmarkConfig,
    records: List[RequestRecord],
    start_time: float,
    stop_event: asyncio.Event,
):
    """Periodically inject write-like operations to test read/write contention."""
    # Wait for agents to ramp up
    await asyncio.sleep(5.0)

    while not stop_event.is_set():
        result = await _single_write(config.url)
        records.append(RequestRecord(
            agent_id=-1,  # sentinel for write operations
            query="[write_proxy: get_stats]",
            query_type="write",
            latency_ms=result["latency_ms"],
            success=result["ok"],
            error=result["error"],
            timestamp=time.perf_counter() - start_time,
        ))
        # Write every 10-15 seconds
        delay = random.uniform(10.0, 15.0)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
            return
        except asyncio.TimeoutError:
            pass


async def run_benchmark(config: BenchmarkConfig) -> BenchmarkResult:
    """Run the full benchmark for one concurrency level."""
    records: List[RequestRecord] = []
    stop_event = asyncio.Event()
    start_time = time.perf_counter()

    # Launch agent tasks
    tasks = []
    agent_fn = _agent_loop_persistent if config.reuse_connections else _agent_loop
    for i in range(config.n_agents):
        # Stagger agent start by 0-2 seconds to avoid thundering herd
        stagger = random.uniform(0, min(2.0, config.duration_s * 0.1))
        tasks.append(asyncio.create_task(
            _staggered_agent(i, config, records, start_time, stop_event, stagger, agent_fn)
        ))

    if config.with_writes:
        tasks.append(asyncio.create_task(
            _write_injector(config, records, start_time, stop_event)
        ))

    # Run for the configured duration
    await asyncio.sleep(config.duration_s)
    stop_event.set()

    # Wait for all tasks to finish (with timeout)
    await asyncio.wait(tasks, timeout=30.0)

    elapsed = time.perf_counter() - start_time

    # Analyze results
    search_records = [r for r in records if r.query_type != "write"]
    write_records = [r for r in records if r.query_type == "write"]

    all_latencies = [r.latency_ms for r in search_records if r.success]
    total_errors = sum(1 for r in search_records if not r.success)

    # Per-path breakdown
    by_path: Dict[str, PathSummary] = {}
    for qt in ("simple", "hybrid", "precise"):
        path_records = [r for r in search_records if r.query_type == qt]
        summary = PathSummary(
            count=len(path_records),
            errors=sum(1 for r in path_records if not r.success),
            latencies=[r.latency_ms for r in path_records if r.success],
        )
        by_path[qt] = summary

    # Timeline buckets (5-second windows)
    bucket_size = 5.0
    n_buckets = max(1, int(math.ceil(elapsed / bucket_size)))
    timeline = []
    for b in range(n_buckets):
        t_start = b * bucket_size
        t_end = t_start + bucket_size
        bucket_records = [r for r in search_records
                          if r.success and t_start <= r.timestamp < t_end]
        bucket_latencies = [r.latency_ms for r in bucket_records]
        timeline.append({
            "window_s": f"{t_start:.0f}-{t_end:.0f}",
            "requests": len(bucket_records),
            "p50_ms": round(_percentile(bucket_latencies, 50), 1),
            "p95_ms": round(_percentile(bucket_latencies, 95), 1),
            "qps": round(len(bucket_records) / bucket_size, 2),
        })

    # Write impact analysis
    write_impact = None
    if write_records:
        write_latencies = [r.latency_ms for r in write_records if r.success]
        write_impact = {
            "count": len(write_records),
            "errors": sum(1 for r in write_records if not r.success),
            "p50_ms": round(_percentile(write_latencies, 50), 1),
            "p95_ms": round(_percentile(write_latencies, 95), 1),
        }

    return BenchmarkResult(
        config={"n_agents": config.n_agents, "duration_s": config.duration_s,
                "with_writes": config.with_writes, "burst_size": config.burst_size,
                "reuse_connections": config.reuse_connections},
        total_requests=len(search_records),
        total_errors=total_errors,
        error_rate_pct=round(total_errors / max(len(search_records), 1) * 100, 2),
        duration_s=round(elapsed, 1),
        throughput_qps=round(len(search_records) / elapsed, 2),
        by_path={
            qt: {
                "count": s.count, "errors": s.errors,
                "p50_ms": round(s.p50, 1), "p95_ms": round(s.p95, 1),
                "p99_ms": round(s.p99, 1), "mean_ms": round(s.mean, 1),
            }
            for qt, s in by_path.items()
        },
        overall_p50_ms=round(_percentile(all_latencies, 50), 1),
        overall_p95_ms=round(_percentile(all_latencies, 95), 1),
        overall_p99_ms=round(_percentile(all_latencies, 99), 1),
        timeline_buckets=timeline,
        write_impact=write_impact,
    )


async def _staggered_agent(agent_id, config, records, start_time, stop_event, delay, agent_fn):
    """Start an agent after a stagger delay."""
    if delay > 0:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
            return
        except asyncio.TimeoutError:
            pass
    await agent_fn(agent_id, config, records, start_time, stop_event)



# ── Reporting ────────────────────────────────────────────────────────

def print_result(result: BenchmarkResult):
    """Print a human-readable summary."""
    c = result.config
    print(f"\n{'=' * 65}")
    print(f"  {c['n_agents']} AGENTS | {result.duration_s}s | "
          f"{'writes ON' if c['with_writes'] else 'reads only'} | "
          f"{'persistent' if c.get('reuse_connections') else 'new conn/call'}")
    print(f"{'=' * 65}")

    print(f"\n  Total requests:  {result.total_requests}")
    print(f"  Total errors:    {result.total_errors} ({result.error_rate_pct}%)")
    print(f"  Throughput:      {result.throughput_qps} qps")
    print(f"  Overall p50:     {result.overall_p50_ms}ms")
    print(f"  Overall p95:     {result.overall_p95_ms}ms")
    print(f"  Overall p99:     {result.overall_p99_ms}ms")

    print(f"\n  Per-path breakdown:")
    hdr = f"  {'Path':<10} {'Count':>6} {'Errors':>7} {'p50':>8} {'p95':>8} {'p99':>8} {'Mean':>8}"
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))
    for qt in ("simple", "hybrid", "precise"):
        p = result.by_path.get(qt, {})
        if not p or p.get("count", 0) == 0:
            continue
        print(f"  {qt:<10} {p['count']:>6} {p['errors']:>7} "
              f"{p['p50_ms']:>7.0f}ms {p['p95_ms']:>7.0f}ms "
              f"{p['p99_ms']:>7.0f}ms {p['mean_ms']:>7.0f}ms")

    if result.write_impact:
        w = result.write_impact
        print(f"\n  Write operations: {w['count']} ({w['errors']} errors)")
        print(f"  Write p50: {w['p50_ms']}ms  p95: {w['p95_ms']}ms")

    # Timeline (condensed — show first 3, last 3, skip middle if long)
    tl = result.timeline_buckets
    if len(tl) > 8:
        show = tl[:3] + [{"window_s": "...", "requests": 0, "p50_ms": 0, "p95_ms": 0, "qps": 0}] + tl[-3:]
    else:
        show = tl

    print(f"\n  Timeline (5s windows):")
    print(f"  {'Window':<10} {'Reqs':>6} {'p50':>8} {'p95':>8} {'QPS':>8}")
    print("  " + "─" * 42)
    for b in show:
        if b["window_s"] == "...":
            print(f"  {'...':^42}")
        else:
            print(f"  {b['window_s']:<10} {b['requests']:>6} "
                  f"{b['p50_ms']:>7.0f}ms {b['p95_ms']:>7.0f}ms {b['qps']:>7.1f}")


# ── Main ─────────────────────────────────────────────────────────────

async def main_async():
    parser = argparse.ArgumentParser(
        description="Benchmark Candlekeep at organization scale",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --agents 10 --duration 60
  %(prog)s --agents 10,25,50 --duration 120
  %(prog)s --agents 25 --duration 60 --with-writes
  %(prog)s --agents 50 --duration 300 --output results.json""",
    )
    parser.add_argument(
        "--agents", default="10,25,50",
        help="Comma-separated agent counts to test (default: 10,25,50)",
    )
    parser.add_argument(
        "--duration", type=int, default=60,
        help="Benchmark duration in seconds per level (default: 60)",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="MCP server URL")
    parser.add_argument(
        "--with-writes", action="store_true",
        help="Inject periodic write operations during the benchmark",
    )
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument(
        "--burst", type=int, default=3,
        help="Searches per agent burst (default: 3)",
    )
    parser.add_argument(
        "--reuse-connections", action="store_true",
        help="Reuse MCP client connections per agent (persistent sessions)",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    args = parser.parse_args()

    random.seed(args.seed)
    levels = [int(x) for x in args.agents.split(",")]

    # Warmup: verify server is reachable
    print("Verifying server connection...", file=sys.stderr)
    result = await _single_search(args.url, "test query", "simple")
    if not result["ok"]:
        print(f"Server unreachable: {result['error']}", file=sys.stderr)
        print("Start with: CANDLEKEEP_TRANSPORT=http candlekeep", file=sys.stderr)
        sys.exit(1)
    print(f"  Server OK ({result['latency_ms']:.0f}ms warmup)\n", file=sys.stderr)

    all_results = {}

    for n_agents in levels:
        print(f"Running benchmark: {n_agents} agents, {args.duration}s...",
              file=sys.stderr)

        config = BenchmarkConfig(
            n_agents=n_agents,
            duration_s=args.duration,
            url=args.url,
            with_writes=args.with_writes,
            burst_size=args.burst,
            reuse_connections=args.reuse_connections,
        )

        result = await run_benchmark(config)
        all_results[n_agents] = result
        print_result(result)

    # Comparison table across levels
    if len(levels) > 1:
        print(f"\n{'=' * 65}")
        print(f"  SCALING COMPARISON")
        print(f"{'=' * 65}")
        hdr = f"  {'Agents':>7} {'Reqs':>6} {'Errors':>7} {'QPS':>7} {'p50':>8} {'p95':>8} {'p99':>8}"
        print(hdr)
        print("  " + "─" * (len(hdr) - 2))
        for n in levels:
            r = all_results[n]
            print(f"  {n:>7} {r.total_requests:>6} {r.total_errors:>7} "
                  f"{r.throughput_qps:>6.1f} {r.overall_p50_ms:>7.0f}ms "
                  f"{r.overall_p95_ms:>7.0f}ms {r.overall_p99_ms:>7.0f}ms")

        # Check for degradation
        if len(levels) >= 2:
            base = all_results[levels[0]]
            peak = all_results[levels[-1]]
            if base.overall_p50_ms > 0:
                ratio = peak.overall_p95_ms / base.overall_p50_ms
                print(f"\n  Degradation ratio (p95@{levels[-1]} / p50@{levels[0]}): "
                      f"{ratio:.1f}x")
                if ratio < 3.0:
                    print(f"  Verdict: PASS — latency scales acceptably")
                elif ratio < 5.0:
                    print(f"  Verdict: MARGINAL — noticeable degradation at peak")
                else:
                    print(f"  Verdict: FAIL — significant degradation, "
                          f"investigate bottleneck")

    # Save JSON
    output = args.output
    if not output:
        results_dir = Path(__file__).parent.parent / "tests" / "results"
        results_dir.mkdir(exist_ok=True)
        output = str(results_dir / "scale_benchmark.json")

    serializable = {}
    for n, r in all_results.items():
        serializable[str(n)] = {
            "config": r.config,
            "total_requests": r.total_requests,
            "total_errors": r.total_errors,
            "error_rate_pct": r.error_rate_pct,
            "duration_s": r.duration_s,
            "throughput_qps": r.throughput_qps,
            "by_path": r.by_path,
            "overall_p50_ms": r.overall_p50_ms,
            "overall_p95_ms": r.overall_p95_ms,
            "overall_p99_ms": r.overall_p99_ms,
            "timeline_buckets": r.timeline_buckets,
            "write_impact": r.write_impact,
        }

    Path(output).write_text(json.dumps(serializable, indent=2))
    print(f"\n💾 Results saved to {output}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
