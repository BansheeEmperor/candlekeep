#!/usr/bin/env python3
"""Benchmark real agent decomposition behavior on multi-document queries.

Spawns a CLI-based MCP agent, sends complex multi-document queries, and
measures whether the agent decomposes them into multiple search calls.
Records decomposition patterns, source coverage, and content keyword hits.

Prerequisites:
  - Candlekeep HTTP server running on localhost:8111
  - CLI agent available and configured with candlekeep MCP server
  - Scale corpus ingested (89 docs, ~2,770 chunks)

Usage:
  python scripts/benchmark_agent_decomposition.py [--queries N] [--output PATH]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional


# ── Query definitions ────────────────────────────────────────────────

@dataclass
class AgentQuery:
    """A complex query with expected decomposition behavior."""
    query: str
    expected_sources: List[str]
    expected_keywords: List[str]
    expected_min_searches: int
    difficulty: str


AGENT_QUERIES = [
    # 2-doc queries
    AgentQuery(
        query=(
            "How do you terminate TLS at a load balancer and what cipher "
            "suites should you configure? Use the candlekeep search tool to "
            "find the answer. List the source filenames from the results."
        ),
        expected_sources=[
            "tls-ssl.md",
            "load-balancing.md",
        ],
        expected_keywords=["cipher", "handshake", "layer 7", "certificate"],
        expected_min_searches=2,
        difficulty="medium",
    ),
    AgentQuery(
        query=(
            "How does PostgreSQL's write-ahead log work with primary-replica "
            "replication? Use the candlekeep search tool to find the answer. "
            "List the source filenames from the results."
        ),
        expected_sources=[
            "postgresql-internals.md",
            "database-replication.md",
        ],
        expected_keywords=["WAL", "replica", "synchronous"],
        expected_min_searches=2,
        difficulty="medium",
    ),
    AgentQuery(
        query=(
            "How do you implement event sourcing using Kafka topics as the "
            "append-only event store? Use the candlekeep search tool to find "
            "the answer. List the source filenames from the results."
        ),
        expected_sources=[
            "apache-kafka.md",
            "event-driven-architecture.md",
        ],
        expected_keywords=["event sourcing", "topic", "partition"],
        expected_min_searches=2,
        difficulty="medium",
    ),
    AgentQuery(
        query=(
            "How does Istio's Envoy sidecar proxy collect RED metrics and "
            "enable distributed tracing? Use the candlekeep search tool to "
            "find the answer. List the source filenames from the results."
        ),
        expected_sources=[
            "service-mesh.md",
            "monitoring-observability.md",
        ],
        expected_keywords=["Envoy", "sidecar", "tracing"],
        expected_min_searches=2,
        difficulty="medium",
    ),
    # 3-doc queries
    AgentQuery(
        query=(
            "How do you handle backpressure in a Kafka-based streaming data "
            "pipeline with windowed aggregations? Use the candlekeep search "
            "tool to find the answer. List the source filenames from the results."
        ),
        expected_sources=[
            "apache-kafka.md",
            "stream-processing.md",
            "data-pipeline-design.md",
        ],
        expected_keywords=["backpressure", "window", "partition", "consumer"],
        expected_min_searches=2,
        difficulty="hard",
    ),
    AgentQuery(
        query=(
            "How does mutual TLS authentication work in an Istio service mesh "
            "running rootless containers? Use the candlekeep search tool to "
            "find the answer. List the source filenames from the results."
        ),
        expected_sources=[
            "tls-ssl.md",
            "service-mesh.md",
            "container-security.md",
        ],
        expected_keywords=["mutual TLS", "mTLS", "Istio", "rootless"],
        expected_min_searches=2,
        difficulty="hard",
    ),
    # 4-doc queries
    AgentQuery(
        query=(
            "How do you prevent SQL injection in a serverless function API "
            "that retrieves database credentials from Vault and authenticates "
            "users with OAuth 2.0? Use the candlekeep search tool to find "
            "the answer. List the source filenames from the results."
        ),
        expected_sources=[
            "owasp-top-10.md",
            "serverless-architecture.md",
            "secrets-management.md",
            "api-security.md",
        ],
        expected_keywords=["injection", "serverless", "Vault", "OAuth"],
        expected_min_searches=3,
        difficulty="hard",
    ),
    AgentQuery(
        query=(
            "How do you maintain exactly-once semantics when using Kafka event "
            "sourcing with the saga pattern across replicated databases using "
            "optimistic concurrency control? Use the candlekeep search tool to "
            "find the answer. List the source filenames from the results."
        ),
        expected_sources=[
            "apache-kafka.md",
            "event-driven-architecture.md",
            "database-replication.md",
            "concurrency-patterns.md",
        ],
        expected_keywords=["exactly-once", "saga", "replication", "concurrency"],
        expected_min_searches=3,
        difficulty="hard",
    ),
]


# ── Output parsing ───────────────────────────────────────────────────

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]*[a-zA-Z]')

# Matches: Running tool search with the param (from mcp server: candlekeep)
_TOOL_CALL_RE = re.compile(
    r'Running tool (\w+) with the param \(from mcp server: candlekeep\)'
)

# Matches:  ⋮    "query": "some text"
_QUERY_PARAM_RE = re.compile(r'"query":\s*"([^"]+)"')

# Matches:  ⋮    "query_type": "hybrid"
_QUERY_TYPE_RE = re.compile(r'"query_type":\s*"([^"]+)"')

# Matches:  - Completed in 0.190s
_LATENCY_RE = re.compile(r'Completed in ([\d.]+)s')

# Matches: Source: some-file.md (both literal newlines and escaped \n in JSON blobs)
_SOURCE_RE = re.compile(r'Source:\s*(\S+\.md)')

# Matches filenames like tls-ssl.md, apache-kafka.md mentioned anywhere in text
_FILENAME_RE = re.compile(r'\b([a-z][a-z0-9-]+\.md)\b')


@dataclass
class SearchCall:
    query: str
    query_type: str
    latency_s: float


@dataclass
class QueryResult:
    original_query: str
    difficulty: str
    search_calls: List[SearchCall]
    sources_found: List[str]
    expected_sources: List[str]
    keywords_found: List[str]
    expected_keywords: List[str]
    decomposed: bool
    source_coverage: float
    keyword_coverage: float
    search_latency_s: float  # max of call latencies (parallel = wall time)
    search_latency_total_s: float  # sum of call latencies (server-side cost)
    wall_time_s: float  # full agent session including LLM inference
    raw_output: str = ""
    agent_error: Optional[str] = None


def parse_agent_output(raw: str) -> tuple[list[SearchCall], list[str]]:
    """Extract search calls and source files from CLI agent output."""
    # Strip ANSI escape codes — the CLI emits colored output
    raw = _ANSI_RE.sub('', raw)
    lines = raw.split('\n')
    calls: list[SearchCall] = []
    sources: list[str] = []

    current_query = ""
    current_type = "hybrid"

    for i, line in enumerate(lines):
        # Detect tool call start
        if _TOOL_CALL_RE.search(line):
            current_query = ""
            current_type = "hybrid"
            # Scan ahead for params and completion
            for j in range(i + 1, min(i + 15, len(lines))):
                qm = _QUERY_PARAM_RE.search(lines[j])
                if qm:
                    current_query = qm.group(1)
                tm = _QUERY_TYPE_RE.search(lines[j])
                if tm:
                    current_type = tm.group(1)
                lm = _LATENCY_RE.search(lines[j])
                if lm:
                    calls.append(SearchCall(
                        query=current_query,
                        query_type=current_type,
                        latency_s=float(lm.group(1)),
                    ))
                    break

    # Collect sources from the entire raw output. Try structured "Source: x.md"
    # first, fall back to any .md filename mentioned in the output.
    for m in _SOURCE_RE.finditer(raw):
        src = m.group(1)
        if src not in sources:
            sources.append(src)

    if not sources:
        for m in _FILENAME_RE.finditer(raw):
            src = m.group(1)
            if src not in sources:
                sources.append(src)

    return calls, sources


# ── Agent invocation ─────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a research assistant. When asked a technical question, use the "
    "candlekeep search tool to find answers. For complex multi-part questions, "
    "make multiple focused searches (one per sub-topic) and synthesize the "
    "results. Always use the search tool — do not answer from memory."
)

CLI_CMD = "kiro-cli"


def run_agent_query(query: str, timeout: int = 120) -> tuple[str, float]:
    """Run a single query through the CLI agent. Returns (output, wall_time)."""
    start = time.monotonic()
    try:
        result = subprocess.run(
            [
                CLI_CMD, "chat",
                "--no-interactive",
                "--trust-all-tools",
                "--require-mcp-startup",
                query,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start
        # Combine stdout and stderr — tool call output goes to stdout,
        # timing info goes to stderr
        return result.stdout + "\n" + result.stderr, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return f"TIMEOUT after {timeout}s", elapsed


def check_keywords(raw: str, keywords: list[str]) -> list[str]:
    """Return which expected keywords appear in the agent output."""
    lower = _ANSI_RE.sub('', raw).lower()
    return [k for k in keywords if k.lower() in lower]


# ── Main benchmark loop ─────────────────────────────────────────────

def run_benchmark(queries: list[AgentQuery], verbose: bool = False) -> list[QueryResult]:
    results: list[QueryResult] = []

    for i, aq in enumerate(queries):
        label = f"[{i+1}/{len(queries)}]"
        print(f"{label} {aq.difficulty.upper():6s} | {aq.query[:70]}...", file=sys.stderr)

        raw, wall_time = run_agent_query(aq.query)

        if verbose:
            print(f"  Raw output length: {len(raw)} chars", file=sys.stderr)

        calls, sources = parse_agent_output(raw)
        kw_found = check_keywords(raw, aq.expected_keywords)

        # Source coverage: what fraction of expected sources were found
        expected_basenames = [Path(s).name for s in aq.expected_sources]
        sources_hit = [s for s in expected_basenames if s in sources]
        source_cov = len(sources_hit) / len(expected_basenames) if expected_basenames else 0.0
        kw_cov = len(kw_found) / len(aq.expected_keywords) if aq.expected_keywords else 0.0

        call_latencies = [c.latency_s for c in calls]
        search_max = max(call_latencies) if call_latencies else 0.0
        search_total = sum(call_latencies)

        qr = QueryResult(
            original_query=re.sub(
                r'\s*Use the candlekeep search tool.*$', '', aq.query
            ),
            difficulty=aq.difficulty,
            search_calls=[asdict(c) for c in calls],
            sources_found=sources,
            expected_sources=expected_basenames,
            keywords_found=kw_found,
            expected_keywords=aq.expected_keywords,
            decomposed=len(calls) >= 2,
            source_coverage=round(source_cov, 4),
            keyword_coverage=round(kw_cov, 4),
            search_latency_s=round(search_max, 3),
            search_latency_total_s=round(search_total, 3),
            wall_time_s=round(wall_time, 2),
            raw_output=_ANSI_RE.sub('', raw),
        )
        results.append(qr)

        n_calls = len(calls)
        decomp = "✓ decomposed" if qr.decomposed else "✗ single search"
        print(
            f"  {decomp} ({n_calls} calls) | "
            f"sources: {len(sources_hit)}/{len(expected_basenames)} | "
            f"keywords: {len(kw_found)}/{len(aq.expected_keywords)} | "
            f"search: {search_max*1000:.0f}ms",
            file=sys.stderr,
        )

    return results


def print_summary(results: list[QueryResult]):
    """Print aggregate metrics to stderr."""
    n = len(results)
    if not n:
        return

    decomposed = sum(1 for r in results if r.decomposed)
    avg_calls = sum(len(r.search_calls) for r in results) / n
    avg_src_cov = sum(r.source_coverage for r in results) / n
    avg_kw_cov = sum(r.keyword_coverage for r in results) / n
    avg_search = sum(r.search_latency_s for r in results) / n
    full_cov = sum(1 for r in results if r.source_coverage == 1.0)

    print("\n" + "=" * 60, file=sys.stderr)
    print("AGENT DECOMPOSITION BENCHMARK RESULTS", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Queries tested:        {n}", file=sys.stderr)
    print(f"  Decomposed:            {decomposed}/{n} ({100*decomposed/n:.0f}%)", file=sys.stderr)
    print(f"  Avg search calls:      {avg_calls:.1f}", file=sys.stderr)
    print(f"  Avg source coverage:   {100*avg_src_cov:.1f}%", file=sys.stderr)
    print(f"  Full source coverage:  {full_cov}/{n} ({100*full_cov/n:.0f}%)", file=sys.stderr)
    print(f"  Avg keyword coverage:  {100*avg_kw_cov:.1f}%", file=sys.stderr)
    print(f"  Avg search latency:    {1000*avg_search:.0f}ms (max per query)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # By difficulty
    for diff in ("medium", "hard"):
        subset = [r for r in results if r.difficulty == diff]
        if not subset:
            continue
        sn = len(subset)
        sd = sum(1 for r in subset if r.decomposed)
        sc = sum(r.source_coverage for r in subset) / sn
        print(f"  {diff.upper():8s}  decomposed={sd}/{sn}  "
              f"source_cov={100*sc:.0f}%  "
              f"avg_calls={sum(len(r.search_calls) for r in subset)/sn:.1f}  "
              f"search={1000*sum(r.search_latency_s for r in subset)/sn:.0f}ms",
              file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark real agent decomposition on multi-doc queries."
    )
    parser.add_argument(
        "--queries", "-n", type=int, default=len(AGENT_QUERIES),
        help=f"Number of queries to run (default: all {len(AGENT_QUERIES)})",
    )
    parser.add_argument(
        "--output", "-o", type=str, default="tests/results/agent_decomposition.json",
        help="Output JSON path",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    queries = AGENT_QUERIES[:args.queries]

    # Preflight: verify CLI agent and MCP server are reachable
    print("Preflight: checking CLI agent and candlekeep MCP...", file=sys.stderr)
    raw, _ = run_agent_query(
        "Use the candlekeep get_stats tool and show me the result.",
        timeout=60,
    )
    if "Running tool" not in raw or "candlekeep" not in raw:
        print("ERROR: CLI agent did not call candlekeep tools.", file=sys.stderr)
        print("Check that the candlekeep HTTP server is running on :8111", file=sys.stderr)
        print("and the CLI agent has candlekeep configured in mcp.json.", file=sys.stderr)
        sys.exit(1)
    print("Preflight passed.\n", file=sys.stderr)

    results = run_benchmark(queries, verbose=args.verbose)
    print_summary(results)

    # Save results
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "queries": len(results),
            "agent": "frontier LLM via MCP CLI client",
            "transport": "HTTP (localhost:8111)",
        },
        "summary": {
            "decomposition_rate": sum(1 for r in results if r.decomposed) / len(results),
            "avg_search_calls": sum(len(r.search_calls) for r in results) / len(results),
            "avg_source_coverage": sum(r.source_coverage for r in results) / len(results),
            "avg_keyword_coverage": sum(r.keyword_coverage for r in results) / len(results),
            "full_source_coverage_rate": sum(
                1 for r in results if r.source_coverage == 1.0
            ) / len(results),
            "avg_search_latency_ms": 1000 * sum(r.search_latency_s for r in results) / len(results),
            "avg_search_latency_total_ms": 1000 * sum(r.search_latency_total_s for r in results) / len(results),
        },
        "results": [asdict(r) for r in results],
    }
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nResults saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
