"""Multi-document queries with simulated agent decomposition.

In production, the MCP search tool handles ONE focused query at a time.
Complex multi-document questions are the agent's responsibility to decompose
into multiple search calls, then synthesize the results.

This benchmark simulates that pattern: each multi-doc question is paired with
the sub-queries an agent would generate, and we measure the COMBINED coverage
across all sub-query results. This tests the system the way it's actually used.

Compare with test_multi_doc_benchmark.py which tests single-search on the same
questions — that measures the baseline before agent decomposition.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class DecomposedQuery:
    """A complex query with its agent-decomposed sub-queries."""
    original: str
    sub_queries: List[str]
    expected_sources: List[str]
    expected_content: List[str]
    difficulty: str


DECOMPOSED_QUERIES = [
    # ===== 2-DOC QUERIES =====

    DecomposedQuery(
        original="How do you terminate TLS at a load balancer and what cipher suites should you configure?",
        sub_queries=[
            "TLS termination cipher suite configuration",
            "load balancer L7 TLS offloading",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/tls-ssl.md",
            "tests/fixtures/scale_docs/load-balancing.md",
        ],
        expected_content=["cipher suite", "handshake", "layer 7", "certificate"],
        difficulty="medium",
    ),
    DecomposedQuery(
        original="How does PostgreSQL's write-ahead log work with primary-replica replication?",
        sub_queries=[
            "PostgreSQL WAL write-ahead log segments",
            "primary-replica database replication process",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/postgresql-internals.md",
            "tests/fixtures/scale_docs/database-replication.md",
        ],
        expected_content=["WAL", "replica", "synchronous", "pg_wal"],
        difficulty="medium",
    ),
    DecomposedQuery(
        original="How do you implement event sourcing using Kafka topics as the append-only event store?",
        sub_queries=[
            "Kafka topics partitions append-only log",
            "event sourcing aggregate event store projection",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/apache-kafka.md",
            "tests/fixtures/scale_docs/event-driven-architecture.md",
        ],
        expected_content=["event sourcing", "topic", "partition", "aggregate"],
        difficulty="medium",
    ),
    DecomposedQuery(
        original="How do you integrate Trivy container image scanning into a CI/CD pipeline build stage?",
        sub_queries=[
            "Trivy container image vulnerability scanning",
            "CI/CD pipeline build stage Docker image",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/ci-cd-pipelines.md",
            "tests/fixtures/scale_docs/container-security.md",
        ],
        expected_content=["Trivy", "image", "pipeline", "vulnerability"],
        difficulty="medium",
    ),
    DecomposedQuery(
        original="How does Istio's Envoy sidecar proxy collect RED metrics and enable distributed tracing?",
        sub_queries=[
            "Istio Envoy sidecar proxy traffic management",
            "RED metrics rate errors duration distributed tracing",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/service-mesh.md",
            "tests/fixtures/scale_docs/monitoring-observability.md",
        ],
        expected_content=["Envoy", "sidecar", "RED", "tracing"],
        difficulty="medium",
    ),

    # ===== 3-DOC QUERIES =====

    DecomposedQuery(
        original="How do you handle backpressure in a Kafka-based streaming data pipeline with windowed aggregations?",
        sub_queries=[
            "Kafka consumer group backpressure handling",
            "stream processing windowed aggregation tumbling sliding",
            "data pipeline backpressure flow control",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/apache-kafka.md",
            "tests/fixtures/scale_docs/stream-processing.md",
            "tests/fixtures/scale_docs/data-pipeline-design.md",
        ],
        expected_content=["backpressure", "window", "partition", "consumer group"],
        difficulty="hard",
    ),
    DecomposedQuery(
        original="How does mutual TLS authentication work in an Istio service mesh running rootless containers?",
        sub_queries=[
            "mutual TLS mTLS certificate authentication",
            "Istio service mesh mTLS sidecar",
            "rootless containers security runtime",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/tls-ssl.md",
            "tests/fixtures/scale_docs/service-mesh.md",
            "tests/fixtures/scale_docs/container-security.md",
        ],
        expected_content=["mutual TLS", "mTLS", "Istio", "rootless"],
        difficulty="hard",
    ),
    DecomposedQuery(
        original="How do you set up canary deployments in Kubernetes with automated rollback based on error rate metrics?",
        sub_queries=[
            "Kubernetes deployment strategy canary rollout",
            "CI/CD canary deployment automated rollback",
            "error rate metrics monitoring alerting SLO",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/kubernetes-architecture.md",
            "tests/fixtures/scale_docs/ci-cd-pipelines.md",
            "tests/fixtures/scale_docs/monitoring-observability.md",
        ],
        expected_content=["canary", "rollback", "deployment", "metrics"],
        difficulty="hard",
    ),

    # ===== 4-DOC QUERIES =====

    DecomposedQuery(
        original="How do you prevent SQL injection in a serverless function API that retrieves database credentials from Vault and authenticates users with OAuth 2.0?",
        sub_queries=[
            "SQL injection prevention parameterized queries",
            "serverless function event sources",
            "HashiCorp Vault secret retrieval rotation",
            "OAuth 2.0 authentication flow PKCE",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/owasp-top-10.md",
            "tests/fixtures/scale_docs/serverless-architecture.md",
            "tests/fixtures/scale_docs/secrets-management.md",
            "tests/fixtures/scale_docs/api-security.md",
        ],
        expected_content=["injection", "serverless", "Vault", "OAuth"],
        difficulty="hard",
    ),
    DecomposedQuery(
        original="How do you maintain exactly-once semantics when using Kafka event sourcing with the saga pattern across replicated databases using optimistic concurrency control?",
        sub_queries=[
            "Kafka exactly-once semantics idempotent producer",
            "event sourcing saga pattern compensating transactions",
            "database replication conflict resolution",
            "optimistic concurrency control lock-free",
        ],
        expected_sources=[
            "tests/fixtures/scale_docs/apache-kafka.md",
            "tests/fixtures/scale_docs/event-driven-architecture.md",
            "tests/fixtures/scale_docs/database-replication.md",
            "tests/fixtures/scale_docs/concurrency-patterns.md",
        ],
        expected_content=["exactly-once", "saga", "replication", "concurrency"],
        difficulty="hard",
    ),
]
