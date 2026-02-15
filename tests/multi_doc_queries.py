"""Multi-document complex queries for scale corpus testing.

Each query requires information from 2+ documents to answer fully.
Grounded in actual content from the generated scale_docs corpus.
"""
from tests.benchmark import BenchmarkQuery

MULTI_DOC_QUERIES = [
    # ===== 2-DOC QUERIES (moderate complexity) =====

    BenchmarkQuery(
        query="How do you terminate TLS at a load balancer and what cipher suites should you configure?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/scale_docs/tls-ssl.md",
            "tests/fixtures/scale_docs/load-balancing.md",
        ],
        expected_content=["cipher suite", "handshake", "layer 7", "certificate"],
    ),
    BenchmarkQuery(
        query="How does PostgreSQL's write-ahead log work with primary-replica replication?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/scale_docs/postgresql-internals.md",
            "tests/fixtures/scale_docs/database-replication.md",
        ],
        expected_content=["WAL", "replica", "synchronous", "pg_wal"],
    ),
    BenchmarkQuery(
        query="How do you apply seccomp profiles and AppArmor to pods running in Kubernetes?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/scale_docs/kubernetes-architecture.md",
            "tests/fixtures/scale_docs/container-security.md",
        ],
        expected_content=["seccomp", "pod", "AppArmor", "security"],
    ),
    BenchmarkQuery(
        query="How do you implement event sourcing using Kafka topics as the append-only event store?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/scale_docs/apache-kafka.md",
            "tests/fixtures/scale_docs/event-driven-architecture.md",
        ],
        expected_content=["event sourcing", "topic", "partition", "aggregate"],
    ),
    BenchmarkQuery(
        query="How do you integrate Trivy container image scanning into a CI/CD pipeline build stage?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/scale_docs/ci-cd-pipelines.md",
            "tests/fixtures/scale_docs/container-security.md",
        ],
        expected_content=["Trivy", "image", "pipeline", "vulnerability"],
    ),
    BenchmarkQuery(
        query="How does Istio's Envoy sidecar proxy collect RED metrics and enable distributed tracing?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/scale_docs/service-mesh.md",
            "tests/fixtures/scale_docs/monitoring-observability.md",
        ],
        expected_content=["Envoy", "sidecar", "RED", "tracing"],
    ),
    BenchmarkQuery(
        query="How do you inject HashiCorp Vault secrets into Kubernetes pods at runtime?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/scale_docs/secrets-management.md",
            "tests/fixtures/scale_docs/kubernetes-architecture.md",
        ],
        expected_content=["Vault", "pod", "secret", "injection"],
    ),
    BenchmarkQuery(
        query="How do Linux huge pages and NUMA topology affect PostgreSQL shared buffer performance?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/linux-memory-management.md",
            "tests/fixtures/scale_docs/postgresql-internals.md",
        ],
        expected_content=["huge pages", "NUMA", "shared", "memory"],
    ),

    # ===== 3-DOC QUERIES (complex) =====

    BenchmarkQuery(
        query="How do you handle backpressure in a Kafka-based streaming data pipeline with windowed aggregations?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/apache-kafka.md",
            "tests/fixtures/scale_docs/stream-processing.md",
            "tests/fixtures/scale_docs/data-pipeline-design.md",
        ],
        expected_content=["backpressure", "window", "partition", "consumer group"],
    ),
    BenchmarkQuery(
        query="How does mutual TLS authentication work in an Istio service mesh running rootless containers?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/tls-ssl.md",
            "tests/fixtures/scale_docs/service-mesh.md",
            "tests/fixtures/scale_docs/container-security.md",
        ],
        expected_content=["mutual TLS", "mTLS", "Istio", "rootless"],
    ),
    BenchmarkQuery(
        query="How do you implement warm standby disaster recovery with synchronous database replication and circuit breaker failover?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/disaster-recovery.md",
            "tests/fixtures/scale_docs/database-replication.md",
            "tests/fixtures/scale_docs/cloud-design-patterns.md",
        ],
        expected_content=["warm standby", "synchronous", "circuit breaker", "failover"],
    ),
    BenchmarkQuery(
        query="How do you set up canary deployments in Kubernetes with automated rollback based on error rate metrics?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/kubernetes-architecture.md",
            "tests/fixtures/scale_docs/ci-cd-pipelines.md",
            "tests/fixtures/scale_docs/monitoring-observability.md",
        ],
        expected_content=["canary", "rollback", "deployment", "metrics"],
    ),

    # ===== 4-DOC QUERIES (very complex) =====

    BenchmarkQuery(
        query="How do you prevent SQL injection in a serverless function API that retrieves database credentials from Vault and authenticates users with OAuth 2.0?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/owasp-top-10.md",
            "tests/fixtures/scale_docs/serverless-architecture.md",
            "tests/fixtures/scale_docs/secrets-management.md",
            "tests/fixtures/scale_docs/api-security.md",
        ],
        expected_content=["injection", "serverless", "Vault", "OAuth"],
    ),
    BenchmarkQuery(
        query="How do you maintain exactly-once semantics when using Kafka event sourcing with the saga pattern across replicated databases using optimistic concurrency control?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/apache-kafka.md",
            "tests/fixtures/scale_docs/event-driven-architecture.md",
            "tests/fixtures/scale_docs/database-replication.md",
            "tests/fixtures/scale_docs/concurrency-patterns.md",
        ],
        expected_content=["exactly-once", "saga", "replication", "concurrency"],
    ),

    # ===== EDGE CASES =====

    # Sounds multi-doc but really only needs one
    BenchmarkQuery(
        query="What are the different types of DNS records and their TTL behavior?",
        difficulty="easy",
        expected_sources=[
            "tests/fixtures/scale_docs/dns-resolution.md",
        ],
        expected_content=["A", "CNAME", "MX", "TTL"],
    ),
    # Uses vocabulary from many docs but has a specific answer
    BenchmarkQuery(
        query="What is the difference between L4 and L7 load balancing for gRPC services behind a CDN?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/scale_docs/load-balancing.md",
            "tests/fixtures/scale_docs/grpc-protocol.md",
            "tests/fixtures/scale_docs/cdn-architecture.md",
        ],
        expected_content=["layer 4", "layer 7", "gRPC", "edge"],
    ),
]
