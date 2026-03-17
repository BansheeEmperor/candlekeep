#!/usr/bin/env python3
"""HNSW parameter sweep at 10k+ chunks.

Generates a deterministic synthetic corpus of ~300 documents across diverse
technical domains, producing 10k+ chunks. Then sweeps search_ef values on
the Centurion Set queries to test whether HNSW defaults remain optimal at
scale.

The synthetic documents are noise — the Centurion Set queries target the
original 89 fixture documents. This tests whether HNSW with search_ef=10
still finds the right needles in a 10k+ chunk haystack.

Usage:
    python scripts/sweep_hnsw.py [--search-ef 10,25,50,100,200]
"""
import sys
import os
import json
import time
import random
import hashlib
import argparse
import tempfile
import shutil
from pathlib import Path

os.environ["CANDLEKEEP_DEVICE"] = "cpu"
sys.path.append(str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery


# --- Synthetic corpus generation ---

DOMAINS = {
    "networking": [
        "packet switching", "routing protocols", "BGP peering", "MPLS tunneling",
        "network address translation", "VLAN configuration", "spanning tree protocol",
        "quality of service", "network segmentation", "traffic shaping",
        "OSPF areas", "EIGRP metrics", "ARP resolution", "ICMP diagnostics",
        "multicast routing", "network bonding", "jumbo frames", "MTU discovery",
    ],
    "machine_learning": [
        "gradient descent", "backpropagation", "convolutional networks",
        "recurrent networks", "attention mechanisms", "transformer architecture",
        "batch normalization", "dropout regularization", "learning rate scheduling",
        "transfer learning", "data augmentation", "hyperparameter tuning",
        "loss functions", "activation functions", "weight initialization",
        "model pruning", "knowledge distillation", "federated learning",
    ],
    "frontend": [
        "virtual DOM", "component lifecycle", "state management", "CSS grid layout",
        "responsive design", "accessibility standards", "progressive web apps",
        "service workers", "web components", "shadow DOM", "CSS custom properties",
        "intersection observer", "web animations API", "font loading strategies",
        "image optimization", "code splitting", "tree shaking", "bundle analysis",
    ],
    "mobile": [
        "iOS app lifecycle", "Android activity stack", "push notifications",
        "offline storage", "biometric authentication", "deep linking",
        "app transport security", "background processing", "widget extensions",
        "in-app purchases", "crash reporting", "performance profiling",
        "memory leak detection", "battery optimization", "screen adaptation",
        "gesture recognition", "haptic feedback", "accessibility services",
    ],
    "devops": [
        "blue-green deployment", "canary releases", "feature flags",
        "infrastructure provisioning", "configuration drift", "secret rotation",
        "log aggregation", "metric collection", "alert fatigue",
        "runbook automation", "capacity planning", "cost allocation",
        "compliance scanning", "vulnerability patching", "incident classification",
        "post-mortem analysis", "SLO definition", "error budgets",
    ],
    "databases_advanced": [
        "write-ahead logging", "MVCC implementation", "query plan optimization",
        "index selectivity", "partition pruning", "materialized views",
        "change data capture", "logical replication slots", "vacuum strategies",
        "connection multiplexing", "prepared statement caching", "advisory locks",
        "row-level security", "column-level encryption", "audit logging",
        "temporal tables", "graph traversal queries", "full-text search ranking",
    ],
    "distributed_systems": [
        "Raft consensus", "Paxos protocol", "vector clocks", "CRDTs",
        "gossip protocols", "consistent hashing", "shard rebalancing",
        "circuit breaker pattern", "bulkhead isolation", "retry with jitter",
        "idempotency keys", "saga orchestration", "outbox pattern",
        "event sourcing snapshots", "command query separation", "backpressure",
        "flow control", "dead letter queues",
    ],
    "security_advanced": [
        "certificate pinning", "HSTS preloading", "CSP directives",
        "CORS preflight", "OAuth token rotation", "SAML assertions",
        "Kerberos delegation", "LDAP injection prevention", "XML external entities",
        "deserialization attacks", "timing side channels", "memory safety",
        "fuzzing strategies", "static analysis rules", "dependency scanning",
        "supply chain verification", "SBOM generation", "threat modeling",
    ],
}

SECTION_TEMPLATES = [
    "## Overview\n\n{topic} is a fundamental concept in {domain}. "
    "It addresses the challenge of {challenge} by providing {solution}. "
    "Modern implementations typically involve {detail1} and {detail2}.",

    "## How It Works\n\nThe core mechanism behind {topic} relies on {mechanism}. "
    "When a system needs to {action}, it first {step1}, then {step2}. "
    "This process ensures {guarantee} while maintaining {property}.",

    "## Best Practices\n\nWhen implementing {topic}, consider the following:\n\n"
    "- Always {practice1} to avoid {pitfall1}\n"
    "- Monitor {metric} to detect {issue} early\n"
    "- Use {tool} for {purpose}\n"
    "- Test {scenario} under {condition}",

    "## Common Pitfalls\n\nTeams often encounter issues with {topic} when they "
    "{mistake1}. This leads to {consequence1}. Another frequent problem is "
    "{mistake2}, which causes {consequence2}. The recommended approach is to "
    "{recommendation}.",

    "## Performance Considerations\n\n{topic} performance depends on {factor1} "
    "and {factor2}. At scale, {bottleneck} becomes the primary constraint. "
    "Benchmarks show that {metric_result} when {condition}. Optimization "
    "strategies include {optimization1} and {optimization2}.",
]

FILLERS = {
    "challenge": ["scalability", "reliability", "latency", "throughput", "consistency",
                   "availability", "durability", "observability", "maintainability"],
    "solution": ["a layered architecture", "an event-driven approach", "a declarative model",
                 "automated orchestration", "policy-based control", "adaptive algorithms"],
    "mechanism": ["state machines", "message passing", "shared memory", "lock-free structures",
                  "append-only logs", "merkle trees", "bloom filters", "skip lists"],
    "action": ["process a request", "replicate data", "recover from failure",
               "scale horizontally", "enforce a policy", "validate input"],
    "step1": ["validates the input", "acquires a lock", "checks the cache",
              "resolves dependencies", "authenticates the caller"],
    "step2": ["dispatches to a worker", "persists the state", "notifies subscribers",
              "updates the index", "releases resources"],
    "guarantee": ["consistency", "atomicity", "isolation", "durability", "linearizability"],
    "property": ["low latency", "high throughput", "fault tolerance", "backward compatibility"],
    "practice1": ["validate inputs at the boundary", "use timeouts on all I/O",
                  "implement circuit breakers", "log structured events"],
    "pitfall1": ["cascading failures", "resource exhaustion", "data corruption", "deadlocks"],
    "metric": ["p99 latency", "error rate", "queue depth", "memory usage", "CPU utilization"],
    "issue": ["degradation", "saturation", "contention", "drift", "leaks"],
    "tool": ["Prometheus", "Grafana", "Jaeger", "OpenTelemetry", "Datadog"],
    "purpose": ["real-time monitoring", "distributed tracing", "anomaly detection"],
    "scenario": ["failover", "rollback", "scale-up", "cold start", "network partition"],
    "condition": ["peak load", "degraded mode", "single-region failure", "clock skew"],
    "mistake1": ["skip capacity planning", "ignore backpressure", "hardcode configuration"],
    "consequence1": ["outages under load", "cascading timeouts", "deployment failures"],
    "mistake2": ["couple services tightly", "share databases", "use synchronous calls everywhere"],
    "consequence2": ["deployment bottlenecks", "schema migration pain", "latency amplification"],
    "recommendation": ["decouple via events and design for failure from day one"],
    "factor1": ["network latency", "disk I/O", "serialization overhead", "GC pressure"],
    "factor2": ["concurrency level", "payload size", "index cardinality", "cache hit ratio"],
    "bottleneck": ["I/O wait", "lock contention", "memory allocation", "DNS resolution"],
    "metric_result": ["throughput doubles", "p99 drops by 40%", "error rate halves"],
    "optimization1": ["batching", "connection pooling", "compression", "prefetching"],
    "optimization2": ["sharding", "caching", "lazy evaluation", "async processing"],
    "detail1": ["automated failover", "health checking", "graceful degradation"],
    "detail2": ["structured logging", "distributed tracing", "metric aggregation"],
}


def _seeded_choice(options, seed_str):
    """Deterministic choice based on a seed string."""
    idx = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % len(options)
    return options[idx]


def generate_document(domain: str, topic: str, doc_index: int) -> str:
    """Generate a single synthetic document deterministically."""
    rng = random.Random(f"{domain}:{topic}:{doc_index}")

    title = topic.replace("_", " ").title()
    description = f"Technical guide covering {topic} in the context of {domain.replace('_', ' ')}."
    keywords = f"{topic}, {domain.replace('_', ' ')}, technical guide"

    frontmatter = (
        f"---\ntitle: \"{title}\"\n"
        f"description: \"{description}\"\n"
        f"keywords: \"{keywords}\"\n---\n\n"
    )

    body = f"# {title}\n\n"

    # Pick 3-5 section templates
    n_sections = rng.randint(3, 5)
    templates = rng.sample(SECTION_TEMPLATES, min(n_sections, len(SECTION_TEMPLATES)))

    for tmpl in templates:
        section = tmpl
        # Fill in all placeholders
        for key, options in FILLERS.items():
            placeholder = "{" + key + "}"
            while placeholder in section:
                val = rng.choice(options)
                section = section.replace(placeholder, val, 1)
        section = section.replace("{topic}", topic.replace("_", " "))
        section = section.replace("{domain}", domain.replace("_", " "))
        body += section + "\n\n"

    return frontmatter + body


def generate_corpus(target_dir: Path, target_chunks: int = 10000) -> int:
    """Generate synthetic documents until we exceed target_chunks.

    Returns the number of documents generated.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    doc_count = 0

    # Each document produces ~3-8 chunks (512 chars each, 3-5 sections).
    # To reach 10k chunks we need ~1500-3000 documents.
    # Generate by cycling through domains and topics with increasing indices.
    domain_list = list(DOMAINS.items())
    topic_idx = 0

    while True:
        for domain, topics in domain_list:
            for topic in topics:
                doc_text = generate_document(domain, topic, topic_idx)
                filename = f"synth-{domain}-{topic.replace(' ', '-')}-{topic_idx:03d}.md"
                (target_dir / filename).write_text(doc_text)
                doc_count += 1

                # Rough estimate: ~5 chunks per doc
                if doc_count * 5 >= target_chunks:
                    return doc_count

        topic_idx += 1


# --- Benchmark ---

def run_sweep(search_ef_values: list[int]):
    print("=" * 60)
    print("HNSW PARAMETER SWEEP AT SCALE")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="candlekeep_hnsw_")
    synth_dir = Path(temp_dir) / "synth_docs"

    try:
        settings = Settings.from_env()
        store = ChromaVectorStore(settings)
        processor = DocumentProcessor(settings)

        # 1. Ingest original fixture documents
        fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
        print("\n📦 Ingesting original fixture documents...")
        fixture_count = 0
        for doc_dir in [fixtures / "sample_docs", fixtures / "scale_docs"]:
            for doc_path in doc_dir.glob("*"):
                if doc_path.is_file():
                    chunks = processor.process(str(doc_path))
                    store.add_documents(chunks)
                    fixture_count += 1
        
        base_stats = store.get_stats()
        base_chunks = base_stats.get("total_chunks", 0)
        print(f"  Fixture docs: {fixture_count}, chunks: {base_chunks}")

        # 2. Generate and ingest synthetic noise corpus
        target_total = 12000  # Target 12k total chunks
        target_synth = target_total - base_chunks
        print(f"\n🔧 Generating synthetic corpus (target: {target_synth} additional chunks)...")
        
        synth_count = generate_corpus(synth_dir, target_chunks=target_synth)
        print(f"  Generated {synth_count} synthetic documents.")

        print("📦 Ingesting synthetic corpus...")
        ingested = 0
        for doc_path in sorted(synth_dir.glob("*.md")):
            try:
                chunks = processor.process(str(doc_path))
                store.add_documents(chunks)
                ingested += 1
                if ingested % 100 == 0:
                    stats = store.get_stats()
                    print(f"  ... {ingested}/{synth_count} docs, "
                          f"{stats.get('total_chunks', 0)} chunks")
            except Exception:
                continue  # Skip docs that fail quality gate

        final_stats = store.get_stats()
        total_chunks = final_stats.get("total_chunks", 0)
        print(f"\n✅ Total corpus: {fixture_count + ingested} docs, {total_chunks} chunks")

        # 3. Load Centurion Set
        suite_path = fixtures / "eval_suite_100.json"
        with open(suite_path) as f:
            suite = json.load(f)

        queries = [
            EvalQuery(
                query=q["query"],
                expected_sources=q["expected_sources"],
                category=q["category"],
                difficulty=q["difficulty"]
            )
            for q in suite["queries"]
        ]

        # 4. Sweep search_ef
        print(f"\n{'=' * 60}")
        print(f"SWEEP: search_ef values = {search_ef_values}")
        print(f"{'=' * 60}")

        all_results = {}

        for ef in search_ef_values:
            # Update HNSW search_ef via collection metadata
            # ChromaDB exposes this as a collection-level setting
            try:
                store.collection.modify(metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": settings.embedding_model,
                    "hnsw:search_ef": ef,
                })
            except Exception as e:
                print(f"  ⚠ Could not set search_ef={ef}: {e}")
                print(f"    Falling back to default search_ef")

            def search_fn(query: str, k: int):
                return search_with_routing(store, query, n_results=k, query_type="hybrid")

            runner = BenchmarkRunner(search_fn)
            results = runner.run_suite(queries, k=5)
            summary = runner.summarize(results)

            print(f"\n--- search_ef = {ef} ---")
            print(f"  MRR:        {summary['mrr']:.4f}")
            print(f"  nDCG@5:     {summary['avg_ndcg_5']:.4f}")
            print(f"  Hit Rate@5: {summary['avg_hit_rate_5']:.4f}")
            print(f"  Latency:    {summary['avg_latency_ms']:.1f}ms")

            all_results[ef] = summary

        # 5. Summary table
        print(f"\n{'=' * 60}")
        print(f"SUMMARY ({total_chunks} chunks)")
        print(f"{'=' * 60}")
        print(f"{'search_ef':>10} | {'MRR':>8} | {'nDCG@5':>8} | {'HR@5':>8} | {'Latency':>10}")
        print("-" * 55)
        for ef in search_ef_values:
            s = all_results[ef]
            print(f"{ef:>10} | {s['mrr']:>8.4f} | {s['avg_ndcg_5']:>8.4f} | "
                  f"{s['avg_hit_rate_5']:>8.4f} | {s['avg_latency_ms']:>8.1f}ms")

        # 6. Save results
        output_dir = Path(__file__).parent.parent / "tests" / "results"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "hnsw_sweep_at_scale.json"
        output_path.write_text(json.dumps({
            "total_chunks": total_chunks,
            "total_docs": fixture_count + ingested,
            "search_ef_values": search_ef_values,
            "results": {str(k): v for k, v in all_results.items()},
        }, indent=2))
        print(f"\nResults saved to {output_path}")

    finally:
        shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(description="HNSW parameter sweep at 10k+ chunks")
    parser.add_argument("--search-ef", default="10,25,50,100,200",
                        help="Comma-separated search_ef values to test")
    args = parser.parse_args()

    ef_values = [int(x) for x in args.search_ef.split(",")]
    run_sweep(ef_values)


if __name__ == "__main__":
    main()
