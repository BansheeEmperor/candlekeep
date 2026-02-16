#!/usr/bin/env python3
"""Benchmark cross-encoder (precise path) under concurrent load.

Measures latency distribution when N agents fire precise-path queries
simultaneously against an HTTP-mode Candlekeep server.

Prerequisites:
  1. ChromaDB running with indexed documents.
  2. Candlekeep running in HTTP mode:
     CANDLEKEEP_TRANSPORT=http CANDLEKEEP_HTTP_PORT=8111 candlekeep

Usage:
  python scripts/benchmark_concurrent.py [--url URL] [--concurrency N,N,N]

Example:
  python scripts/benchmark_concurrent.py --concurrency 1,2,3,5,10
"""
import argparse
import asyncio
import json
import sys
import time

from fastmcp import Client

DEFAULT_URL = "http://localhost:8111/mcp"

# Sample queries for precise-path benchmarking
QUERIES = [
    "Compare authentication methods for microservices and recommend one",
    "What are the tradeoffs between SQL and NoSQL for session storage",
    "How does vector similarity search work with HNSW indexing",
    "Explain the difference between BM25 and semantic search",
    "What caching strategies work best for read-heavy APIs",
    "How to implement rate limiting in a distributed system",
    "Compare REST and GraphQL for mobile API design",
    "What are the security implications of JWT vs session tokens",
    "How does database sharding affect query performance",
    "Explain eventual consistency and its tradeoffs",
]


async def call_search(url: str, query: str) -> dict:
    """Call the MCP search tool via FastMCP client and return timing info."""
    start = time.perf_counter()
    try:
        async with Client(url) as client:
            result = await client.call_tool("search", {
                "query": query,
                "n_results": 5,
                "query_type": "precise",
            })
            elapsed = time.perf_counter() - start
            return {"ok": True, "latency_ms": elapsed * 1000}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"ok": False, "latency_ms": elapsed * 1000, "error": str(e)}


async def run_concurrent(url: str, n: int) -> list[dict]:
    """Fire n concurrent precise-path queries and collect results."""
    tasks = []
    for i in range(n):
        query = QUERIES[i % len(QUERIES)]
        tasks.append(call_search(url, query))
    return await asyncio.gather(*tasks)


def percentile(data: list[float], p: int) -> float:
    """Calculate percentile."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


async def main_async():
    parser = argparse.ArgumentParser(description="Benchmark concurrent precise-path queries")
    parser.add_argument("--url", default=DEFAULT_URL, help="MCP server URL")
    parser.add_argument("--concurrency", default="1,2,3,5", help="Comma-separated concurrency levels")
    parser.add_argument("--warmup", type=int, default=2, help="Warmup queries before benchmark")
    args = parser.parse_args()

    levels = [int(x) for x in args.concurrency.split(",")]

    # Warmup
    print(f"Warming up with {args.warmup} sequential queries...", file=sys.stderr)
    for i in range(args.warmup):
        result = await call_search(args.url, QUERIES[i % len(QUERIES)])
        if not result["ok"]:
            print(f"Warmup failed: {result.get('error', 'unknown')}", file=sys.stderr)
            print("Is the server running? Start with: CANDLEKEEP_TRANSPORT=http candlekeep", file=sys.stderr)
            sys.exit(1)
        print(f"  warmup {i+1}: {result['latency_ms']:.0f}ms", file=sys.stderr)
    print("Warmup complete.\n", file=sys.stderr)

    # Benchmark
    all_results = {}
    baseline_p50 = None

    for n in levels:
        print(f"Running N={n} concurrent precise queries...", file=sys.stderr)
        results = await run_concurrent(args.url, n)

        latencies = [r["latency_ms"] for r in results if r["ok"]]
        errors = [r for r in results if not r["ok"]]

        if not latencies:
            print(f"  All {n} queries failed.", file=sys.stderr)
            for e in errors:
                print(f"    {e.get('error', 'unknown')}", file=sys.stderr)
            continue

        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        p99 = percentile(latencies, 99)
        total_time_s = max(latencies) / 1000
        throughput = len(latencies) / total_time_s if total_time_s > 0 else 0

        if baseline_p50 is None:
            baseline_p50 = p50

        ratio = p95 / baseline_p50 if baseline_p50 > 0 else 0

        all_results[n] = {
            "concurrency": n,
            "queries": len(latencies),
            "errors": len(errors),
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
            "throughput_qps": round(throughput, 2),
            "p95_vs_baseline_p50": round(ratio, 2),
        }

        status = "PASS" if ratio < 3.0 else "FAIL"
        print(f"  p50={p50:.0f}ms  p95={p95:.0f}ms  p99={p99:.0f}ms  "
              f"throughput={throughput:.1f}qps  ratio={ratio:.1f}x  [{status}]",
              file=sys.stderr)

    # Output JSON results
    print("\n" + json.dumps(all_results, indent=2))

    # Summary
    print("\n--- Summary ---", file=sys.stderr)
    if baseline_p50:
        print(f"Baseline p50 (N=1): {baseline_p50:.0f}ms", file=sys.stderr)
        print(f"Pass criteria: p95 at max concurrency < 3x baseline p50 ({baseline_p50 * 3:.0f}ms)", file=sys.stderr)

        max_level = max(levels)
        if max_level in all_results:
            ratio = all_results[max_level]["p95_vs_baseline_p50"]
            if ratio < 3.0:
                print(f"Result: PASS (ratio={ratio:.1f}x at N={max_level})", file=sys.stderr)
            else:
                print(f"Result: FAIL (ratio={ratio:.1f}x at N={max_level}). "
                      f"Consider adding threading.Semaphore.", file=sys.stderr)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
