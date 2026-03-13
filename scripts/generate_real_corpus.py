"""Generate 50-document real corpus for VLM benchmark.

50 markdown docs across 5 categories (10 each):
  1. Deployment topologies   — Graphviz directed graphs
  2. System architectures    — Graphviz directed graphs
  3. Network topologies      — Graphviz directed graphs
  4. Benchmark charts        — Matplotlib bar/line charts
  5. Incident timelines      — Matplotlib timeline charts

Design constraint: text describes the system category and purpose.
Diagram contains specific details (component names, ports, values, counts).
Text does NOT enumerate those details — they are only in the diagram.

Run: python scripts/generate_real_corpus.py
Output: tests/fixtures/real_corpus/
"""
import textwrap
from pathlib import Path

import graphviz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = Path("tests/fixtures/real_corpus")
IMGS = OUT / "images"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_gv(g: graphviz.Digraph, name: str) -> str:
    path = IMGS / name
    g.render(str(path), format="png", cleanup=True)
    return f"images/{name}.png"


def _save_fig(name: str) -> str:
    path = IMGS / f"{name}.png"
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()
    return f"images/{name}.png"


def _doc(title: str, description: str, overview: str, img_rel: str, details: str) -> str:
    # details arg is ignored — use generic text so diagram content doesn't leak into text chunks
    return textwrap.dedent(f"""\
        ---
        title: "{title}"
        description: "{description}"
        keywords:
          - architecture
          - diagram
          - technical
        category: "architecture"
        tags:
          - visual
          - benchmark
        ---

        ## Overview

        {overview}

        ![{title}]({img_rel})

        ## Details

        Refer to the diagram above for specific configuration details, component names, and measured values.
        """)


# ---------------------------------------------------------------------------
# Category 1: Deployment Topologies (10 docs)
# ---------------------------------------------------------------------------

DEPLOY_DOCS = [
    # (slug, title, description, overview, details, nodes, edges)
    ("deploy-01", "Authentication Service Deployment",
     "Multi-region deployment topology for the authentication service.",
     "The authentication service is deployed across two availability zones in a primary region with a warm standby in a secondary region. The topology uses an active-active configuration with session replication.",
     "The diagram shows the specific instance names, replica counts, and load balancer endpoints. Port assignments and replication lag thresholds are visible in the diagram.",
     [("ALB-us-east-1", "shape=box,style=filled,fillcolor=lightblue"),
      ("auth-east-1a", "shape=box,style=filled,fillcolor=lightyellow"),
      ("auth-east-1b", "shape=box,style=filled,fillcolor=lightyellow"),
      ("redis-primary\n:6379", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("redis-replica\n:6380", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("rds-postgres\nus-east-1", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("auth-us-west-2\n(standby)", "shape=box,style=filled,fillcolor=lightyellow,style=dashed")],
     [("ALB-us-east-1", "auth-east-1a"), ("ALB-us-east-1", "auth-east-1b"),
      ("auth-east-1a", "redis-primary\n:6379"), ("auth-east-1b", "redis-primary\n:6379"),
      ("redis-primary\n:6379", "redis-replica\n:6380"),
      ("auth-east-1a", "rds-postgres\nus-east-1"), ("auth-east-1b", "rds-postgres\nus-east-1"),
      ("rds-postgres\nus-east-1", "auth-us-west-2\n(standby)")]),

    ("deploy-02", "Payment Processing Service Deployment",
     "Kubernetes deployment topology for the payment processing service.",
     "The payment processing service runs on Kubernetes with horizontal pod autoscaling enabled. The service is split into separate pods for API handling, transaction processing, and fraud detection.",
     "The diagram shows pod counts, resource limits, and inter-service communication paths. Specific CPU and memory allocations per pod type are visible in the diagram.",
     [("ingress-nginx\n:443", "shape=box,style=filled,fillcolor=lightblue"),
      ("payment-api\n3 pods", "shape=box,style=filled,fillcolor=lightyellow"),
      ("txn-processor\n5 pods", "shape=box,style=filled,fillcolor=lightyellow"),
      ("fraud-detector\n2 pods", "shape=box,style=filled,fillcolor=lightyellow"),
      ("kafka\n:9092", "shape=parallelogram,style=filled,fillcolor=lightgreen"),
      ("postgres-primary\n:5432", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("vault\n:8200", "shape=box,style=filled,fillcolor=lightgray")],
     [("ingress-nginx\n:443", "payment-api\n3 pods"),
      ("payment-api\n3 pods", "txn-processor\n5 pods"),
      ("payment-api\n3 pods", "fraud-detector\n2 pods"),
      ("txn-processor\n5 pods", "kafka\n:9092"),
      ("txn-processor\n5 pods", "postgres-primary\n:5432"),
      ("payment-api\n3 pods", "vault\n:8200")]),

    ("deploy-03", "Search Service Deployment",
     "Elasticsearch cluster deployment topology for the search service.",
     "The search service uses a dedicated Elasticsearch cluster with separate master, data, and coordinating nodes. The cluster is deployed behind a dedicated load balancer.",
     "The diagram shows the specific node roles, shard counts, and replica configuration. Heap sizes and disk allocations per node type are visible in the diagram.",
     [("search-lb\n:9200", "shape=box,style=filled,fillcolor=lightblue"),
      ("coord-node-1\n:9200", "shape=box,style=filled,fillcolor=lightyellow"),
      ("coord-node-2\n:9200", "shape=box,style=filled,fillcolor=lightyellow"),
      ("data-node-1\n32GB heap", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("data-node-2\n32GB heap", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("data-node-3\n32GB heap", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("master-node-1\n4GB heap", "shape=diamond,style=filled,fillcolor=lightsalmon"),
      ("master-node-2\n4GB heap", "shape=diamond,style=filled,fillcolor=lightsalmon"),
      ("master-node-3\n4GB heap", "shape=diamond,style=filled,fillcolor=lightsalmon")],
     [("search-lb\n:9200", "coord-node-1\n:9200"), ("search-lb\n:9200", "coord-node-2\n:9200"),
      ("coord-node-1\n:9200", "data-node-1\n32GB heap"), ("coord-node-1\n:9200", "data-node-2\n32GB heap"),
      ("coord-node-2\n:9200", "data-node-2\n32GB heap"), ("coord-node-2\n:9200", "data-node-3\n32GB heap"),
      ("master-node-1\n4GB heap", "data-node-1\n32GB heap"),
      ("master-node-2\n4GB heap", "data-node-2\n32GB heap"),
      ("master-node-3\n4GB heap", "data-node-3\n32GB heap")]),

    ("deploy-04", "Notification Service Deployment",
     "Multi-channel notification service deployment with dedicated workers.",
     "The notification service handles email, SMS, and push notifications through dedicated worker pools. Each channel has independent scaling and retry logic.",
     "The diagram shows the specific worker counts per channel, queue names, and dead-letter queue configuration. Retry limits and backoff intervals are visible in the diagram.",
     [("api-gateway\n:8080", "shape=box,style=filled,fillcolor=lightblue"),
      ("notif-router", "shape=box,style=filled,fillcolor=lightyellow"),
      ("email-queue\nSQS", "shape=parallelogram,style=filled,fillcolor=lightgreen"),
      ("sms-queue\nSQS", "shape=parallelogram,style=filled,fillcolor=lightgreen"),
      ("push-queue\nSQS", "shape=parallelogram,style=filled,fillcolor=lightgreen"),
      ("email-workers\n4 pods", "shape=box,style=filled,fillcolor=lightyellow"),
      ("sms-workers\n2 pods", "shape=box,style=filled,fillcolor=lightyellow"),
      ("push-workers\n6 pods", "shape=box,style=filled,fillcolor=lightyellow"),
      ("dlq-email", "shape=parallelogram,style=filled,fillcolor=lightsalmon"),
      ("dlq-sms", "shape=parallelogram,style=filled,fillcolor=lightsalmon")],
     [("api-gateway\n:8080", "notif-router"),
      ("notif-router", "email-queue\nSQS"), ("notif-router", "sms-queue\nSQS"), ("notif-router", "push-queue\nSQS"),
      ("email-queue\nSQS", "email-workers\n4 pods"), ("sms-queue\nSQS", "sms-workers\n2 pods"),
      ("push-queue\nSQS", "push-workers\n6 pods"),
      ("email-workers\n4 pods", "dlq-email"), ("sms-workers\n2 pods", "dlq-sms")]),

    ("deploy-05", "ML Inference Service Deployment",
     "GPU-accelerated ML inference service deployment topology.",
     "The ML inference service uses a tiered deployment with CPU-based preprocessing and GPU-based model inference. Models are loaded from a shared model registry.",
     "The diagram shows the specific GPU instance types, model versions loaded, and batch sizes. Memory allocation per GPU and model warm-up times are visible in the diagram.",
     [("inference-lb\n:8080", "shape=box,style=filled,fillcolor=lightblue"),
      ("preprocess\n8 CPU pods", "shape=box,style=filled,fillcolor=lightyellow"),
      ("gpu-node-1\np3.2xlarge", "shape=box,style=filled,fillcolor=lightgreen"),
      ("gpu-node-2\np3.2xlarge", "shape=box,style=filled,fillcolor=lightgreen"),
      ("gpu-node-3\np3.8xlarge", "shape=box,style=filled,fillcolor=lightgreen"),
      ("model-registry\nS3", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("feature-store\nRedis :6379", "shape=cylinder,style=filled,fillcolor=lightgray")],
     [("inference-lb\n:8080", "preprocess\n8 CPU pods"),
      ("preprocess\n8 CPU pods", "gpu-node-1\np3.2xlarge"),
      ("preprocess\n8 CPU pods", "gpu-node-2\np3.2xlarge"),
      ("preprocess\n8 CPU pods", "gpu-node-3\np3.8xlarge"),
      ("model-registry\nS3", "gpu-node-1\np3.2xlarge"),
      ("model-registry\nS3", "gpu-node-2\np3.2xlarge"),
      ("model-registry\nS3", "gpu-node-3\np3.8xlarge"),
      ("feature-store\nRedis :6379", "preprocess\n8 CPU pods")]),

    ("deploy-06", "API Gateway Deployment",
     "Multi-region API gateway deployment with rate limiting and caching.",
     "The API gateway is deployed in three regions with local caching and centralized rate limiting. Traffic is routed based on latency and health checks.",
     "The diagram shows the specific cache TTL values, rate limit thresholds per tier, and health check intervals. Regional failover weights are visible in the diagram.",
     [("global-lb\nRoute53", "shape=box,style=filled,fillcolor=lightblue"),
      ("gw-us-east-1\n:443", "shape=box,style=filled,fillcolor=lightyellow"),
      ("gw-eu-west-1\n:443", "shape=box,style=filled,fillcolor=lightyellow"),
      ("gw-ap-south-1\n:443", "shape=box,style=filled,fillcolor=lightyellow"),
      ("rate-limiter\nRedis cluster", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("cache-us\nTTL:300s", "shape=cylinder,style=filled,fillcolor=lightgray"),
      ("cache-eu\nTTL:300s", "shape=cylinder,style=filled,fillcolor=lightgray"),
      ("backend-services", "shape=box,style=filled,fillcolor=lightsalmon")],
     [("global-lb\nRoute53", "gw-us-east-1\n:443"),
      ("global-lb\nRoute53", "gw-eu-west-1\n:443"),
      ("global-lb\nRoute53", "gw-ap-south-1\n:443"),
      ("gw-us-east-1\n:443", "rate-limiter\nRedis cluster"),
      ("gw-eu-west-1\n:443", "rate-limiter\nRedis cluster"),
      ("gw-us-east-1\n:443", "cache-us\nTTL:300s"),
      ("gw-eu-west-1\n:443", "cache-eu\nTTL:300s"),
      ("gw-us-east-1\n:443", "backend-services"),
      ("gw-eu-west-1\n:443", "backend-services")]),

    ("deploy-07", "Data Pipeline Deployment",
     "Streaming data pipeline deployment with Kafka and Flink.",
     "The data pipeline ingests events from multiple sources, processes them through a stream processing layer, and writes results to multiple sinks.",
     "The diagram shows the specific topic names, partition counts, consumer group IDs, and sink configurations. Checkpoint intervals and parallelism settings are visible in the diagram.",
     [("producers\n12 sources", "shape=box,style=filled,fillcolor=lightblue"),
      ("kafka\nevents-raw\n24 partitions", "shape=parallelogram,style=filled,fillcolor=lightyellow"),
      ("flink-job\nenrich-v3\n8 parallelism", "shape=box,style=filled,fillcolor=lightgreen"),
      ("kafka\nevents-enriched\n12 partitions", "shape=parallelogram,style=filled,fillcolor=lightyellow"),
      ("flink-job\naggregate-v2\n4 parallelism", "shape=box,style=filled,fillcolor=lightgreen"),
      ("clickhouse\nanalytics", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("s3\ndata-lake", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("elasticsearch\nmetrics", "shape=cylinder,style=filled,fillcolor=lightsalmon")],
     [("producers\n12 sources", "kafka\nevents-raw\n24 partitions"),
      ("kafka\nevents-raw\n24 partitions", "flink-job\nenrich-v3\n8 parallelism"),
      ("flink-job\nenrich-v3\n8 parallelism", "kafka\nevents-enriched\n12 partitions"),
      ("kafka\nevents-enriched\n12 partitions", "flink-job\naggregate-v2\n4 parallelism"),
      ("flink-job\naggregate-v2\n4 parallelism", "clickhouse\nanalytics"),
      ("flink-job\nenrich-v3\n8 parallelism", "s3\ndata-lake"),
      ("flink-job\naggregate-v2\n4 parallelism", "elasticsearch\nmetrics")]),

    ("deploy-08", "CDN and Origin Deployment",
     "Content delivery network deployment with origin shield and edge caching.",
     "The CDN deployment uses a two-tier caching architecture with regional origin shields to reduce load on the origin servers.",
     "The diagram shows the specific edge PoP locations, cache hit ratio targets, and origin shield regions. TTL values per content type are visible in the diagram.",
     [("clients", "shape=box,style=filled,fillcolor=lightblue"),
      ("edge-us-east\nPoP:NYC", "shape=box,style=filled,fillcolor=lightyellow"),
      ("edge-eu-west\nPoP:AMS", "shape=box,style=filled,fillcolor=lightyellow"),
      ("edge-ap-east\nPoP:SIN", "shape=box,style=filled,fillcolor=lightyellow"),
      ("shield-us\nus-east-1", "shape=box,style=filled,fillcolor=lightgreen"),
      ("shield-eu\neu-west-1", "shape=box,style=filled,fillcolor=lightgreen"),
      ("origin-lb\n:443", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("origin-1\n:8080", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("origin-2\n:8080", "shape=box,style=filled,fillcolor=lightsalmon")],
     [("clients", "edge-us-east\nPoP:NYC"), ("clients", "edge-eu-west\nPoP:AMS"), ("clients", "edge-ap-east\nPoP:SIN"),
      ("edge-us-east\nPoP:NYC", "shield-us\nus-east-1"), ("edge-eu-west\nPoP:AMS", "shield-eu\neu-west-1"),
      ("edge-ap-east\nPoP:SIN", "shield-us\nus-east-1"),
      ("shield-us\nus-east-1", "origin-lb\n:443"), ("shield-eu\neu-west-1", "origin-lb\n:443"),
      ("origin-lb\n:443", "origin-1\n:8080"), ("origin-lb\n:443", "origin-2\n:8080")]),

    ("deploy-09", "Database Cluster Deployment",
     "PostgreSQL high-availability cluster deployment with read replicas.",
     "The database cluster uses a primary-replica configuration with synchronous replication to a hot standby and asynchronous replication to read replicas.",
     "The diagram shows the specific replication modes, replica lag thresholds, and connection pool sizes. Failover timeout and promotion criteria are visible in the diagram.",
     [("pgbouncer\n:6432\npool:100", "shape=box,style=filled,fillcolor=lightblue"),
      ("pg-primary\n:5432", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("pg-standby\nsync replica", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("pg-replica-1\nasync :5432", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("pg-replica-2\nasync :5432", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("pg-replica-3\nasync :5432", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("patroni\nHA manager", "shape=diamond,style=filled,fillcolor=lightsalmon"),
      ("etcd\n:2379", "shape=box,style=filled,fillcolor=lightgray")],
     [("pgbouncer\n:6432\npool:100", "pg-primary\n:5432"),
      ("pgbouncer\n:6432\npool:100", "pg-replica-1\nasync :5432"),
      ("pgbouncer\n:6432\npool:100", "pg-replica-2\nasync :5432"),
      ("pg-primary\n:5432", "pg-standby\nsync replica"),
      ("pg-primary\n:5432", "pg-replica-1\nasync :5432"),
      ("pg-primary\n:5432", "pg-replica-2\nasync :5432"),
      ("pg-primary\n:5432", "pg-replica-3\nasync :5432"),
      ("patroni\nHA manager", "pg-primary\n:5432"),
      ("patroni\nHA manager", "etcd\n:2379")]),

    ("deploy-10", "Microservices Mesh Deployment",
     "Service mesh deployment topology for the order management microservices.",
     "The order management system uses a service mesh for inter-service communication with mutual TLS and circuit breaking. Services are deployed with sidecar proxies.",
     "The diagram shows the specific service names, sidecar proxy versions, and circuit breaker thresholds. mTLS certificate rotation intervals are visible in the diagram.",
     [("ingress-gw\nenvoy:1.28", "shape=box,style=filled,fillcolor=lightblue"),
      ("order-svc\n+envoy:1.28", "shape=box,style=filled,fillcolor=lightyellow"),
      ("inventory-svc\n+envoy:1.28", "shape=box,style=filled,fillcolor=lightyellow"),
      ("payment-svc\n+envoy:1.28", "shape=box,style=filled,fillcolor=lightyellow"),
      ("shipping-svc\n+envoy:1.28", "shape=box,style=filled,fillcolor=lightyellow"),
      ("notification-svc\n+envoy:1.28", "shape=box,style=filled,fillcolor=lightyellow"),
      ("istiod\ncontrol plane", "shape=diamond,style=filled,fillcolor=lightsalmon")],
     [("ingress-gw\nenvoy:1.28", "order-svc\n+envoy:1.28"),
      ("order-svc\n+envoy:1.28", "inventory-svc\n+envoy:1.28"),
      ("order-svc\n+envoy:1.28", "payment-svc\n+envoy:1.28"),
      ("order-svc\n+envoy:1.28", "shipping-svc\n+envoy:1.28"),
      ("order-svc\n+envoy:1.28", "notification-svc\n+envoy:1.28"),
      ("istiod\ncontrol plane", "ingress-gw\nenvoy:1.28"),
      ("istiod\ncontrol plane", "order-svc\n+envoy:1.28")]),
]


# ---------------------------------------------------------------------------
# Category 2: System Architectures (10 docs)
# ---------------------------------------------------------------------------

ARCH_DOCS = [
    ("arch-01", "Event-Driven Order Processing Architecture",
     "Event-driven architecture for the order processing system.",
     "The order processing system uses an event-driven architecture with domain events flowing through an event bus. Each bounded context subscribes to relevant events and maintains its own read model.",
     "The diagram shows the specific event types, topic names, and consumer group assignments. Event schema versions and retention policies are visible in the diagram.",
     [("order-service", "shape=box,style=filled,fillcolor=lightblue"),
      ("event-bus\nKafka", "shape=parallelogram,style=filled,fillcolor=lightyellow"),
      ("order.created\ntopic", "shape=ellipse,style=filled,fillcolor=lightgreen"),
      ("order.paid\ntopic", "shape=ellipse,style=filled,fillcolor=lightgreen"),
      ("order.shipped\ntopic", "shape=ellipse,style=filled,fillcolor=lightgreen"),
      ("inventory-consumer\ngroup:inv-v2", "shape=box,style=filled,fillcolor=lightyellow"),
      ("billing-consumer\ngroup:bill-v1", "shape=box,style=filled,fillcolor=lightyellow"),
      ("fulfillment-consumer\ngroup:ful-v3", "shape=box,style=filled,fillcolor=lightyellow"),
      ("analytics-consumer\ngroup:ana-v1", "shape=box,style=filled,fillcolor=lightyellow")],
     [("order-service", "event-bus\nKafka"),
      ("event-bus\nKafka", "order.created\ntopic"), ("event-bus\nKafka", "order.paid\ntopic"),
      ("event-bus\nKafka", "order.shipped\ntopic"),
      ("order.created\ntopic", "inventory-consumer\ngroup:inv-v2"),
      ("order.created\ntopic", "billing-consumer\ngroup:bill-v1"),
      ("order.paid\ntopic", "fulfillment-consumer\ngroup:ful-v3"),
      ("order.shipped\ntopic", "analytics-consumer\ngroup:ana-v1")]),

    ("arch-02", "CQRS Read Model Architecture",
     "CQRS architecture with separate read and write models for the product catalog.",
     "The product catalog uses CQRS to separate write operations from read queries. Write commands update the event store, which projects into multiple optimized read models.",
     "The diagram shows the specific projector names, read model stores, and projection lag thresholds. Cache invalidation strategies per read model are visible in the diagram.",
     [("write-api", "shape=box,style=filled,fillcolor=lightblue"),
      ("command-handler", "shape=box,style=filled,fillcolor=lightyellow"),
      ("event-store\nEventDB", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("projector-search\nlag<500ms", "shape=box,style=filled,fillcolor=lightyellow"),
      ("projector-catalog\nlag<100ms", "shape=box,style=filled,fillcolor=lightyellow"),
      ("projector-recs\nlag<5s", "shape=box,style=filled,fillcolor=lightyellow"),
      ("elasticsearch\nread model", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("postgres\nread model", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("redis\nrec cache", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("read-api", "shape=box,style=filled,fillcolor=lightblue")],
     [("write-api", "command-handler"), ("command-handler", "event-store\nEventDB"),
      ("event-store\nEventDB", "projector-search\nlag<500ms"),
      ("event-store\nEventDB", "projector-catalog\nlag<100ms"),
      ("event-store\nEventDB", "projector-recs\nlag<5s"),
      ("projector-search\nlag<500ms", "elasticsearch\nread model"),
      ("projector-catalog\nlag<100ms", "postgres\nread model"),
      ("projector-recs\nlag<5s", "redis\nrec cache"),
      ("read-api", "elasticsearch\nread model"), ("read-api", "postgres\nread model")]),

    ("arch-03", "ML Feature Pipeline Architecture",
     "Feature engineering pipeline architecture for the recommendation system.",
     "The recommendation system's feature pipeline computes user and item features from raw event streams. Features are stored in an online store for low-latency serving and an offline store for training.",
     "The diagram shows the specific feature group names, computation frequencies, and store backends. Feature freshness SLAs and backfill schedules are visible in the diagram.",
     [("clickstream\nevents", "shape=parallelogram,style=filled,fillcolor=lightblue"),
      ("feature-eng\nSpark job", "shape=box,style=filled,fillcolor=lightyellow"),
      ("user-features\n1h window", "shape=box,style=filled,fillcolor=lightgreen"),
      ("item-features\n24h window", "shape=box,style=filled,fillcolor=lightgreen"),
      ("context-features\n5m window", "shape=box,style=filled,fillcolor=lightgreen"),
      ("redis\nonline store", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("s3\noffline store", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("feast\nfeature server", "shape=box,style=filled,fillcolor=lightgray"),
      ("model-server", "shape=box,style=filled,fillcolor=lightblue")],
     [("clickstream\nevents", "feature-eng\nSpark job"),
      ("feature-eng\nSpark job", "user-features\n1h window"),
      ("feature-eng\nSpark job", "item-features\n24h window"),
      ("feature-eng\nSpark job", "context-features\n5m window"),
      ("user-features\n1h window", "redis\nonline store"),
      ("item-features\n24h window", "s3\noffline store"),
      ("context-features\n5m window", "redis\nonline store"),
      ("redis\nonline store", "feast\nfeature server"),
      ("feast\nfeature server", "model-server")]),

    ("arch-04", "Zero-Trust Security Architecture",
     "Zero-trust network architecture for internal service communication.",
     "The platform uses a zero-trust architecture where every service-to-service call is authenticated and authorized. Identity is established through short-lived certificates issued by the internal CA.",
     "The diagram shows the specific certificate TTLs, policy engine endpoints, and audit log destinations. SPIFFE trust domain names and rotation schedules are visible in the diagram.",
     [("service-a\nSPIFFE ID", "shape=box,style=filled,fillcolor=lightblue"),
      ("service-b\nSPIFFE ID", "shape=box,style=filled,fillcolor=lightblue"),
      ("spire-server\n:8081", "shape=diamond,style=filled,fillcolor=lightgreen"),
      ("spire-agent\nnode attestor", "shape=box,style=filled,fillcolor=lightyellow"),
      ("opa\npolicy engine", "shape=box,style=filled,fillcolor=lightyellow"),
      ("vault-pki\nCA :8200", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("audit-log\nS3+Splunk", "shape=cylinder,style=filled,fillcolor=lightgray")],
     [("service-a\nSPIFFE ID", "spire-agent\nnode attestor"),
      ("service-b\nSPIFFE ID", "spire-agent\nnode attestor"),
      ("spire-agent\nnode attestor", "spire-server\n:8081"),
      ("spire-server\n:8081", "vault-pki\nCA :8200"),
      ("service-a\nSPIFFE ID", "opa\npolicy engine"),
      ("service-b\nSPIFFE ID", "opa\npolicy engine"),
      ("opa\npolicy engine", "audit-log\nS3+Splunk")]),

    ("arch-05", "Multi-Tenant SaaS Architecture",
     "Multi-tenant architecture for the SaaS platform with tenant isolation.",
     "The SaaS platform uses a shared infrastructure with logical tenant isolation. Each tenant has dedicated database schemas and isolated message queues.",
     "The diagram shows the specific isolation boundaries, shared service names, and tenant routing logic. Database schema naming conventions and queue prefixes are visible in the diagram.",
     [("tenant-router", "shape=box,style=filled,fillcolor=lightblue"),
      ("tenant-A\nschema:ta_prod", "shape=box,style=filled,fillcolor=lightyellow"),
      ("tenant-B\nschema:tb_prod", "shape=box,style=filled,fillcolor=lightyellow"),
      ("tenant-C\nschema:tc_prod", "shape=box,style=filled,fillcolor=lightyellow"),
      ("shared-postgres", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("shared-redis", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("billing-service\nshared", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("auth-service\nshared", "shape=box,style=filled,fillcolor=lightsalmon")],
     [("tenant-router", "tenant-A\nschema:ta_prod"),
      ("tenant-router", "tenant-B\nschema:tb_prod"),
      ("tenant-router", "tenant-C\nschema:tc_prod"),
      ("tenant-A\nschema:ta_prod", "shared-postgres"),
      ("tenant-B\nschema:tb_prod", "shared-postgres"),
      ("tenant-C\nschema:tc_prod", "shared-postgres"),
      ("tenant-A\nschema:ta_prod", "shared-redis"),
      ("tenant-router", "billing-service\nshared"),
      ("tenant-router", "auth-service\nshared")]),

    ("arch-06", "Observability Stack Architecture",
     "Observability architecture for metrics, logs, and traces collection.",
     "The observability stack collects telemetry from all services using the OpenTelemetry collector. Data is routed to specialized backends based on signal type.",
     "The diagram shows the specific collector pipeline names, sampling rates, and backend endpoints. Retention periods and storage tiers per signal type are visible in the diagram.",
     [("services\nOTel SDK", "shape=box,style=filled,fillcolor=lightblue"),
      ("otel-collector\ngRPC:4317", "shape=box,style=filled,fillcolor=lightyellow"),
      ("metrics-pipeline\nsample:100%", "shape=box,style=filled,fillcolor=lightgreen"),
      ("traces-pipeline\nsample:10%", "shape=box,style=filled,fillcolor=lightgreen"),
      ("logs-pipeline\nsample:100%", "shape=box,style=filled,fillcolor=lightgreen"),
      ("prometheus\n:9090", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("tempo\n:3200", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("loki\n:3100", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("grafana\n:3000", "shape=box,style=filled,fillcolor=lightgray")],
     [("services\nOTel SDK", "otel-collector\ngRPC:4317"),
      ("otel-collector\ngRPC:4317", "metrics-pipeline\nsample:100%"),
      ("otel-collector\ngRPC:4317", "traces-pipeline\nsample:10%"),
      ("otel-collector\ngRPC:4317", "logs-pipeline\nsample:100%"),
      ("metrics-pipeline\nsample:100%", "prometheus\n:9090"),
      ("traces-pipeline\nsample:10%", "tempo\n:3200"),
      ("logs-pipeline\nsample:100%", "loki\n:3100"),
      ("grafana\n:3000", "prometheus\n:9090"),
      ("grafana\n:3000", "tempo\n:3200"),
      ("grafana\n:3000", "loki\n:3100")]),

    ("arch-07", "CI/CD Pipeline Architecture",
     "Continuous integration and deployment pipeline architecture.",
     "The CI/CD pipeline uses a GitOps workflow with automated testing gates and progressive delivery. Deployments are promoted through environments based on test results.",
     "The diagram shows the specific test suite names, coverage thresholds, and promotion criteria. Canary traffic percentages and rollback triggers are visible in the diagram.",
     [("git-push\nmain branch", "shape=box,style=filled,fillcolor=lightblue"),
      ("build\n+unit tests", "shape=box,style=filled,fillcolor=lightyellow"),
      ("integration\ntests >85% cov", "shape=box,style=filled,fillcolor=lightyellow"),
      ("staging\ndeploy", "shape=box,style=filled,fillcolor=lightgreen"),
      ("e2e-tests\nselenium", "shape=box,style=filled,fillcolor=lightyellow"),
      ("canary\n5% traffic", "shape=box,style=filled,fillcolor=lightyellow"),
      ("production\n100% traffic", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("rollback\ntrigger", "shape=diamond,style=filled,fillcolor=lightsalmon"),
      ("argocd\nGitOps", "shape=box,style=filled,fillcolor=lightgray")],
     [("git-push\nmain branch", "build\n+unit tests"),
      ("build\n+unit tests", "integration\ntests >85% cov"),
      ("integration\ntests >85% cov", "staging\ndeploy"),
      ("staging\ndeploy", "e2e-tests\nselenium"),
      ("e2e-tests\nselenium", "canary\n5% traffic"),
      ("canary\n5% traffic", "production\n100% traffic"),
      ("canary\n5% traffic", "rollback\ntrigger"),
      ("argocd\nGitOps", "staging\ndeploy"),
      ("argocd\nGitOps", "production\n100% traffic")]),

    ("arch-08", "Distributed Cache Architecture",
     "Distributed caching architecture with tiered cache layers.",
     "The caching architecture uses a three-tier approach with local in-process caches, a distributed Redis cluster, and a regional CDN cache for static assets.",
     "The diagram shows the specific cache sizes, eviction policies, and hit rate targets per tier. TTL values and invalidation propagation paths are visible in the diagram.",
     [("application\ninstances", "shape=box,style=filled,fillcolor=lightblue"),
      ("L1-cache\nCaffeine 256MB", "shape=cylinder,style=filled,fillcolor=lightgreen"),
      ("L2-cache\nRedis cluster", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("redis-node-1\n8GB", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("redis-node-2\n8GB", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("redis-node-3\n8GB", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("L3-cache\nCDN edge", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("origin\ndatabase", "shape=cylinder,style=filled,fillcolor=lightgray")],
     [("application\ninstances", "L1-cache\nCaffeine 256MB"),
      ("L1-cache\nCaffeine 256MB", "L2-cache\nRedis cluster"),
      ("L2-cache\nRedis cluster", "redis-node-1\n8GB"),
      ("L2-cache\nRedis cluster", "redis-node-2\n8GB"),
      ("L2-cache\nRedis cluster", "redis-node-3\n8GB"),
      ("L2-cache\nRedis cluster", "origin\ndatabase"),
      ("L3-cache\nCDN edge", "L2-cache\nRedis cluster")]),

    ("arch-09", "Saga Pattern Architecture",
     "Distributed transaction management using the saga pattern.",
     "The checkout flow uses the saga pattern to coordinate distributed transactions across multiple services. Each step has a corresponding compensating transaction for rollback.",
     "The diagram shows the specific saga step names, compensation actions, and timeout values. Idempotency key formats and retry limits per step are visible in the diagram.",
     [("checkout-saga\norchestrator", "shape=diamond,style=filled,fillcolor=lightblue"),
      ("reserve-inventory\ntimeout:5s", "shape=box,style=filled,fillcolor=lightyellow"),
      ("charge-payment\ntimeout:10s", "shape=box,style=filled,fillcolor=lightyellow"),
      ("create-shipment\ntimeout:3s", "shape=box,style=filled,fillcolor=lightyellow"),
      ("send-confirmation\ntimeout:2s", "shape=box,style=filled,fillcolor=lightyellow"),
      ("release-inventory\ncompensate", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("refund-payment\ncompensate", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("cancel-shipment\ncompensate", "shape=box,style=filled,fillcolor=lightsalmon")],
     [("checkout-saga\norchestrator", "reserve-inventory\ntimeout:5s"),
      ("reserve-inventory\ntimeout:5s", "charge-payment\ntimeout:10s"),
      ("charge-payment\ntimeout:10s", "create-shipment\ntimeout:3s"),
      ("create-shipment\ntimeout:3s", "send-confirmation\ntimeout:2s"),
      ("reserve-inventory\ntimeout:5s", "release-inventory\ncompensate"),
      ("charge-payment\ntimeout:10s", "refund-payment\ncompensate"),
      ("create-shipment\ntimeout:3s", "cancel-shipment\ncompensate")]),

    ("arch-10", "API Rate Limiting Architecture",
     "Token bucket rate limiting architecture for the public API.",
     "The API rate limiting system uses a token bucket algorithm with per-customer quotas stored in Redis. Quota enforcement happens at the API gateway layer.",
     "The diagram shows the specific bucket sizes, refill rates per tier, and quota storage keys. Burst allowances and penalty box durations are visible in the diagram.",
     [("api-clients", "shape=box,style=filled,fillcolor=lightblue"),
      ("api-gateway", "shape=box,style=filled,fillcolor=lightyellow"),
      ("rate-limiter\nmiddleware", "shape=box,style=filled,fillcolor=lightgreen"),
      ("redis-quota", "shape=cylinder,style=filled,fillcolor=lightyellow"),
      ("free-tier\n100 req/min", "shape=box,style=filled,fillcolor=lightyellow"),
      ("pro-tier\n1000 req/min", "shape=box,style=filled,fillcolor=lightyellow"),
      ("enterprise-tier\n10000 req/min", "shape=box,style=filled,fillcolor=lightyellow"),
      ("penalty-box\nTTL:3600s", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("backend-services", "shape=box,style=filled,fillcolor=lightgray")],
     [("api-clients", "api-gateway"),
      ("api-gateway", "rate-limiter\nmiddleware"),
      ("rate-limiter\nmiddleware", "redis-quota"),
      ("redis-quota", "free-tier\n100 req/min"),
      ("redis-quota", "pro-tier\n1000 req/min"),
      ("redis-quota", "enterprise-tier\n10000 req/min"),
      ("rate-limiter\nmiddleware", "penalty-box\nTTL:3600s"),
      ("rate-limiter\nmiddleware", "backend-services")]),
]


# ---------------------------------------------------------------------------
# Category 3: Network Topologies (10 docs)
# ---------------------------------------------------------------------------

NET_DOCS = [
    ("net-01", "VPC Network Topology",
     "AWS VPC network topology for the production environment.",
     "The production environment uses a multi-AZ VPC with public and private subnets. Network traffic flows through NAT gateways and a transit gateway for cross-VPC communication.",
     "The diagram shows the specific CIDR ranges, subnet IDs, and routing table configurations. Security group rules and NACLs per subnet tier are visible in the diagram.",
     [("internet-gw\nigw-0a1b2c3d", "shape=box,style=filled,fillcolor=lightblue"),
      ("public-subnet-1a\n10.0.1.0/24", "shape=box,style=filled,fillcolor=lightyellow"),
      ("public-subnet-1b\n10.0.2.0/24", "shape=box,style=filled,fillcolor=lightyellow"),
      ("nat-gw-1a\n:443", "shape=box,style=filled,fillcolor=lightgreen"),
      ("nat-gw-1b\n:443", "shape=box,style=filled,fillcolor=lightgreen"),
      ("private-subnet-1a\n10.0.10.0/24", "shape=box,style=filled,fillcolor=lightyellow"),
      ("private-subnet-1b\n10.0.11.0/24", "shape=box,style=filled,fillcolor=lightyellow"),
      ("db-subnet-1a\n10.0.20.0/24", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("tgw-0x9y8z7w\ntransit gw", "shape=diamond,style=filled,fillcolor=lightgray")],
     [("internet-gw\nigw-0a1b2c3d", "public-subnet-1a\n10.0.1.0/24"),
      ("internet-gw\nigw-0a1b2c3d", "public-subnet-1b\n10.0.2.0/24"),
      ("public-subnet-1a\n10.0.1.0/24", "nat-gw-1a\n:443"),
      ("public-subnet-1b\n10.0.2.0/24", "nat-gw-1b\n:443"),
      ("nat-gw-1a\n:443", "private-subnet-1a\n10.0.10.0/24"),
      ("nat-gw-1b\n:443", "private-subnet-1b\n10.0.11.0/24"),
      ("private-subnet-1a\n10.0.10.0/24", "db-subnet-1a\n10.0.20.0/24"),
      ("private-subnet-1a\n10.0.10.0/24", "tgw-0x9y8z7w\ntransit gw")]),

    ("net-02", "Kubernetes Cluster Network Topology",
     "Kubernetes cluster network topology with CNI plugin configuration.",
     "The Kubernetes cluster uses a Calico CNI plugin with BGP routing between nodes. Pod-to-pod communication uses an overlay network with VXLAN encapsulation.",
     "The diagram shows the specific pod CIDR ranges, node IP assignments, and BGP peer configurations. Network policy enforcement points and VXLAN tunnel IDs are visible in the diagram.",
     [("node-1\n192.168.1.10", "shape=box,style=filled,fillcolor=lightblue"),
      ("node-2\n192.168.1.11", "shape=box,style=filled,fillcolor=lightblue"),
      ("node-3\n192.168.1.12", "shape=box,style=filled,fillcolor=lightblue"),
      ("pod-cidr-1\n10.244.1.0/24", "shape=ellipse,style=filled,fillcolor=lightyellow"),
      ("pod-cidr-2\n10.244.2.0/24", "shape=ellipse,style=filled,fillcolor=lightyellow"),
      ("pod-cidr-3\n10.244.3.0/24", "shape=ellipse,style=filled,fillcolor=lightyellow"),
      ("calico-bgp\nAS:64512", "shape=diamond,style=filled,fillcolor=lightgreen"),
      ("kube-proxy\niptables mode", "shape=box,style=filled,fillcolor=lightsalmon")],
     [("node-1\n192.168.1.10", "pod-cidr-1\n10.244.1.0/24"),
      ("node-2\n192.168.1.11", "pod-cidr-2\n10.244.2.0/24"),
      ("node-3\n192.168.1.12", "pod-cidr-3\n10.244.3.0/24"),
      ("calico-bgp\nAS:64512", "node-1\n192.168.1.10"),
      ("calico-bgp\nAS:64512", "node-2\n192.168.1.11"),
      ("calico-bgp\nAS:64512", "node-3\n192.168.1.12"),
      ("kube-proxy\niptables mode", "node-1\n192.168.1.10"),
      ("kube-proxy\niptables mode", "node-2\n192.168.1.11")]),

    ("net-03", "Service Mesh Network Topology",
     "Istio service mesh network topology with traffic management.",
     "The service mesh controls all east-west traffic between services using Envoy sidecar proxies. Traffic policies define routing rules, retries, and circuit breakers.",
     "The diagram shows the specific virtual service names, destination rule configurations, and circuit breaker thresholds. mTLS modes and certificate rotation intervals are visible in the diagram.",
     [("virtual-svc\nproduct-api", "shape=box,style=filled,fillcolor=lightblue"),
      ("dest-rule\nproduct-api\ncb:5xx>50%", "shape=box,style=filled,fillcolor=lightyellow"),
      ("product-v1\n80% weight", "shape=box,style=filled,fillcolor=lightgreen"),
      ("product-v2\n20% weight", "shape=box,style=filled,fillcolor=lightgreen"),
      ("envoy-sidecar\nproduct-v1", "shape=box,style=filled,fillcolor=lightyellow"),
      ("envoy-sidecar\nproduct-v2", "shape=box,style=filled,fillcolor=lightyellow"),
      ("istiod\n:15010", "shape=diamond,style=filled,fillcolor=lightsalmon"),
      ("prometheus\nmetrics", "shape=cylinder,style=filled,fillcolor=lightgray")],
     [("virtual-svc\nproduct-api", "dest-rule\nproduct-api\ncb:5xx>50%"),
      ("dest-rule\nproduct-api\ncb:5xx>50%", "product-v1\n80% weight"),
      ("dest-rule\nproduct-api\ncb:5xx>50%", "product-v2\n20% weight"),
      ("product-v1\n80% weight", "envoy-sidecar\nproduct-v1"),
      ("product-v2\n20% weight", "envoy-sidecar\nproduct-v2"),
      ("istiod\n:15010", "envoy-sidecar\nproduct-v1"),
      ("istiod\n:15010", "envoy-sidecar\nproduct-v2"),
      ("envoy-sidecar\nproduct-v1", "prometheus\nmetrics")]),

    ("net-04", "Multi-Region Network Topology",
     "Multi-region network topology with global load balancing.",
     "The platform operates across three AWS regions with global load balancing and cross-region replication. Each region has an independent failure domain.",
     "The diagram shows the specific region codes, inter-region latencies, and replication lag thresholds. Failover DNS TTLs and health check intervals are visible in the diagram.",
     [("global-lb\nCloudFront", "shape=box,style=filled,fillcolor=lightblue"),
      ("us-east-1\nprimary", "shape=box,style=filled,fillcolor=lightgreen"),
      ("eu-west-1\nsecondary", "shape=box,style=filled,fillcolor=lightyellow"),
      ("ap-southeast-1\ntertiary", "shape=box,style=filled,fillcolor=lightyellow"),
      ("rds-primary\nus-east-1", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("rds-replica\neu-west-1\nlag<1s", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("rds-replica\nap-se-1\nlag<3s", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("route53\nDNS TTL:60s", "shape=diamond,style=filled,fillcolor=lightgray")],
     [("global-lb\nCloudFront", "us-east-1\nprimary"),
      ("global-lb\nCloudFront", "eu-west-1\nsecondary"),
      ("global-lb\nCloudFront", "ap-southeast-1\ntertiary"),
      ("us-east-1\nprimary", "rds-primary\nus-east-1"),
      ("rds-primary\nus-east-1", "rds-replica\neu-west-1\nlag<1s"),
      ("rds-primary\nus-east-1", "rds-replica\nap-se-1\nlag<3s"),
      ("route53\nDNS TTL:60s", "us-east-1\nprimary"),
      ("route53\nDNS TTL:60s", "eu-west-1\nsecondary")]),

    ("net-05", "Zero-Downtime Deployment Network Topology",
     "Blue-green deployment network topology for zero-downtime releases.",
     "The deployment uses a blue-green strategy with weighted DNS routing to shift traffic between environments. Health checks gate traffic promotion.",
     "The diagram shows the specific environment names, traffic weights, and health check endpoints. Rollback trigger thresholds and DNS propagation times are visible in the diagram.",
     [("route53\nweighted routing", "shape=diamond,style=filled,fillcolor=lightblue"),
      ("blue-env\n90% weight", "shape=box,style=filled,fillcolor=lightblue"),
      ("green-env\n10% weight", "shape=box,style=filled,fillcolor=lightgreen"),
      ("blue-alb\n:443", "shape=box,style=filled,fillcolor=lightblue"),
      ("green-alb\n:443", "shape=box,style=filled,fillcolor=lightgreen"),
      ("blue-asg\n10 instances", "shape=box,style=filled,fillcolor=lightblue"),
      ("green-asg\n10 instances", "shape=box,style=filled,fillcolor=lightgreen"),
      ("health-check\n/health :8080", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("shared-rds\n:5432", "shape=cylinder,style=filled,fillcolor=lightgray")],
     [("route53\nweighted routing", "blue-env\n90% weight"),
      ("route53\nweighted routing", "green-env\n10% weight"),
      ("blue-env\n90% weight", "blue-alb\n:443"),
      ("green-env\n10% weight", "green-alb\n:443"),
      ("blue-alb\n:443", "blue-asg\n10 instances"),
      ("green-alb\n:443", "green-asg\n10 instances"),
      ("health-check\n/health :8080", "blue-asg\n10 instances"),
      ("health-check\n/health :8080", "green-asg\n10 instances"),
      ("blue-asg\n10 instances", "shared-rds\n:5432"),
      ("green-asg\n10 instances", "shared-rds\n:5432")]),

    ("net-06", "On-Premises to Cloud Network Topology",
     "Hybrid network topology connecting on-premises datacenter to AWS.",
     "The hybrid network uses AWS Direct Connect with a VPN backup for connectivity between the on-premises datacenter and the AWS VPC.",
     "The diagram shows the specific Direct Connect circuit IDs, BGP ASNs, and VPN tunnel endpoints. Bandwidth allocations and failover priorities are visible in the diagram.",
     [("on-prem-dc\n10.0.0.0/8", "shape=box,style=filled,fillcolor=lightblue"),
      ("direct-connect\ndxcon-abc123\n1Gbps", "shape=box,style=filled,fillcolor=lightgreen"),
      ("vpn-backup\nvpn-xyz789", "shape=box,style=filled,fillcolor=lightyellow"),
      ("vgw\nvgw-0a1b2c\nAS:64513", "shape=diamond,style=filled,fillcolor=lightyellow"),
      ("vpc-prod\n172.16.0.0/16", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("vpc-dev\n172.17.0.0/16", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("tgw\ntgw-0x1y2z", "shape=diamond,style=filled,fillcolor=lightgray")],
     [("on-prem-dc\n10.0.0.0/8", "direct-connect\ndxcon-abc123\n1Gbps"),
      ("on-prem-dc\n10.0.0.0/8", "vpn-backup\nvpn-xyz789"),
      ("direct-connect\ndxcon-abc123\n1Gbps", "vgw\nvgw-0a1b2c\nAS:64513"),
      ("vpn-backup\nvpn-xyz789", "vgw\nvgw-0a1b2c\nAS:64513"),
      ("vgw\nvgw-0a1b2c\nAS:64513", "tgw\ntgw-0x1y2z"),
      ("tgw\ntgw-0x1y2z", "vpc-prod\n172.16.0.0/16"),
      ("tgw\ntgw-0x1y2z", "vpc-dev\n172.17.0.0/16")]),

    ("net-07", "DNS Resolution Topology",
     "Internal DNS resolution topology for service discovery.",
     "The internal DNS system uses a hierarchical resolver topology with local caching resolvers in each AZ and a central authoritative server.",
     "The diagram shows the specific resolver IP addresses, cache TTLs, and zone delegation paths. DNSSEC signing keys and negative cache TTLs are visible in the diagram.",
     [("clients", "shape=box,style=filled,fillcolor=lightblue"),
      ("local-resolver-1a\n10.0.1.2:53", "shape=box,style=filled,fillcolor=lightyellow"),
      ("local-resolver-1b\n10.0.2.2:53", "shape=box,style=filled,fillcolor=lightyellow"),
      ("central-resolver\n10.0.0.2:53\nTTL:300s", "shape=box,style=filled,fillcolor=lightgreen"),
      ("auth-server\ninternal.corp\n10.0.0.10:53", "shape=cylinder,style=filled,fillcolor=lightsalmon"),
      ("route53-resolver\noutbound", "shape=box,style=filled,fillcolor=lightgray"),
      ("public-dns\n8.8.8.8", "shape=box,style=filled,fillcolor=lightgray")],
     [("clients", "local-resolver-1a\n10.0.1.2:53"),
      ("clients", "local-resolver-1b\n10.0.2.2:53"),
      ("local-resolver-1a\n10.0.1.2:53", "central-resolver\n10.0.0.2:53\nTTL:300s"),
      ("local-resolver-1b\n10.0.2.2:53", "central-resolver\n10.0.0.2:53\nTTL:300s"),
      ("central-resolver\n10.0.0.2:53\nTTL:300s", "auth-server\ninternal.corp\n10.0.0.10:53"),
      ("central-resolver\n10.0.0.2:53\nTTL:300s", "route53-resolver\noutbound"),
      ("route53-resolver\noutbound", "public-dns\n8.8.8.8")]),

    ("net-08", "Load Balancer Topology",
     "Multi-tier load balancing topology for the web application.",
     "The web application uses a three-tier load balancing architecture with a global load balancer, regional application load balancers, and service-level load balancers.",
     "The diagram shows the specific load balancer names, health check paths, and sticky session configurations. Connection draining timeouts and idle connection limits are visible in the diagram.",
     [("cloudfront\ndist-E1A2B3C4", "shape=box,style=filled,fillcolor=lightblue"),
      ("alb-us-east\narn:aws:elb:...", "shape=box,style=filled,fillcolor=lightyellow"),
      ("alb-eu-west\narn:aws:elb:...", "shape=box,style=filled,fillcolor=lightyellow"),
      ("nlb-internal\n:8080", "shape=box,style=filled,fillcolor=lightgreen"),
      ("web-tg\n/health :80\nsticky:1h", "shape=box,style=filled,fillcolor=lightyellow"),
      ("api-tg\n/api/health :8080", "shape=box,style=filled,fillcolor=lightyellow"),
      ("web-instances\n6 hosts", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("api-instances\n4 hosts", "shape=box,style=filled,fillcolor=lightsalmon")],
     [("cloudfront\ndist-E1A2B3C4", "alb-us-east\narn:aws:elb:..."),
      ("cloudfront\ndist-E1A2B3C4", "alb-eu-west\narn:aws:elb:..."),
      ("alb-us-east\narn:aws:elb:...", "web-tg\n/health :80\nsticky:1h"),
      ("alb-us-east\narn:aws:elb:...", "nlb-internal\n:8080"),
      ("nlb-internal\n:8080", "api-tg\n/api/health :8080"),
      ("web-tg\n/health :80\nsticky:1h", "web-instances\n6 hosts"),
      ("api-tg\n/api/health :8080", "api-instances\n4 hosts")]),

    ("net-09", "Container Network Topology",
     "Docker Swarm overlay network topology for the microservices cluster.",
     "The Docker Swarm cluster uses overlay networks to isolate service communication. Frontend services communicate with backend services through a dedicated overlay network.",
     "The diagram shows the specific overlay network names, subnet allocations, and service endpoint IPs. VXLAN IDs and encryption settings per network are visible in the diagram.",
     [("swarm-manager\n192.168.0.10", "shape=diamond,style=filled,fillcolor=lightblue"),
      ("worker-1\n192.168.0.11", "shape=box,style=filled,fillcolor=lightyellow"),
      ("worker-2\n192.168.0.12", "shape=box,style=filled,fillcolor=lightyellow"),
      ("worker-3\n192.168.0.13", "shape=box,style=filled,fillcolor=lightyellow"),
      ("frontend-net\n10.10.0.0/24\nVXLAN:4097", "shape=ellipse,style=filled,fillcolor=lightgreen"),
      ("backend-net\n10.20.0.0/24\nVXLAN:4098", "shape=ellipse,style=filled,fillcolor=lightgreen"),
      ("ingress-net\n10.0.0.0/24", "shape=ellipse,style=filled,fillcolor=lightsalmon")],
     [("swarm-manager\n192.168.0.10", "worker-1\n192.168.0.11"),
      ("swarm-manager\n192.168.0.10", "worker-2\n192.168.0.12"),
      ("swarm-manager\n192.168.0.10", "worker-3\n192.168.0.13"),
      ("worker-1\n192.168.0.11", "frontend-net\n10.10.0.0/24\nVXLAN:4097"),
      ("worker-2\n192.168.0.12", "frontend-net\n10.10.0.0/24\nVXLAN:4097"),
      ("worker-1\n192.168.0.11", "backend-net\n10.20.0.0/24\nVXLAN:4098"),
      ("worker-3\n192.168.0.13", "backend-net\n10.20.0.0/24\nVXLAN:4098"),
      ("swarm-manager\n192.168.0.10", "ingress-net\n10.0.0.0/24")]),

    ("net-10", "Firewall and Security Group Topology",
     "Network security topology with firewall rules and security groups.",
     "The network security architecture uses layered controls with AWS security groups, NACLs, and a WAF. Traffic inspection is performed at each layer.",
     "The diagram shows the specific security group IDs, allowed port ranges, and WAF rule set names. NACL rule numbers and evaluation order are visible in the diagram.",
     [("internet", "shape=box,style=filled,fillcolor=lightblue"),
      ("waf\naws-managed-rules", "shape=box,style=filled,fillcolor=lightgreen"),
      ("alb-sg\nsg-0a1b2c3d\n:443 inbound", "shape=box,style=filled,fillcolor=lightyellow"),
      ("nacl-public\nrule:100 allow\n:443,80", "shape=box,style=filled,fillcolor=lightyellow"),
      ("app-sg\nsg-0e4f5g6h\n:8080 from alb-sg", "shape=box,style=filled,fillcolor=lightyellow"),
      ("nacl-private\nrule:100 allow\n:8080", "shape=box,style=filled,fillcolor=lightyellow"),
      ("db-sg\nsg-0i7j8k9l\n:5432 from app-sg", "shape=box,style=filled,fillcolor=lightsalmon"),
      ("nacl-db\nrule:100 allow\n:5432", "shape=box,style=filled,fillcolor=lightsalmon")],
     [("internet", "waf\naws-managed-rules"),
      ("waf\naws-managed-rules", "alb-sg\nsg-0a1b2c3d\n:443 inbound"),
      ("alb-sg\nsg-0a1b2c3d\n:443 inbound", "nacl-public\nrule:100 allow\n:443,80"),
      ("nacl-public\nrule:100 allow\n:443,80", "app-sg\nsg-0e4f5g6h\n:8080 from alb-sg"),
      ("app-sg\nsg-0e4f5g6h\n:8080 from alb-sg", "nacl-private\nrule:100 allow\n:8080"),
      ("nacl-private\nrule:100 allow\n:8080", "db-sg\nsg-0i7j8k9l\n:5432 from app-sg"),
      ("db-sg\nsg-0i7j8k9l\n:5432 from app-sg", "nacl-db\nrule:100 allow\n:5432")]),
]


# ---------------------------------------------------------------------------
# Category 4: Benchmark Charts (10 docs) — matplotlib
# ---------------------------------------------------------------------------

BENCH_DOCS = [
    ("bench-01", "Database Query Performance Benchmark",
     "Query performance comparison across database configurations.",
     "The database team benchmarked query performance across four configurations varying index strategy and connection pool size. Results are measured in queries per second at p99 latency.",
     "The diagram shows the specific QPS values, p99 latency measurements, and configuration labels. Error bars and statistical significance markers are visible in the diagram.",
     {"type": "bar", "labels": ["no-index\npool:10", "btree-index\npool:10", "btree-index\npool:50", "partial-index\npool:50"],
      "values": [142, 1847, 2103, 3891], "ylabel": "Queries/sec (p99<50ms)", "colors": ["#E74C3C", "#F39C12", "#2ECC71", "#3498DB"]}),

    ("bench-02", "API Gateway Latency Benchmark",
     "API gateway latency comparison across routing configurations.",
     "The platform team measured end-to-end API latency across five routing configurations. Measurements were taken under sustained load of 1000 RPS.",
     "The diagram shows the specific latency values in milliseconds per configuration and percentile. The configuration with the lowest p99 latency is highlighted in the diagram.",
     {"type": "grouped_bar", "groups": ["p50", "p95", "p99", "p999"],
      "series": {"direct": [8, 22, 45, 120], "1-hop": [12, 31, 67, 189], "2-hop": [19, 48, 98, 287], "cached": [3, 8, 15, 42]},
      "ylabel": "Latency (ms)"}),

    ("bench-03", "Cache Hit Rate Benchmark",
     "Cache hit rate comparison across eviction policies and cache sizes.",
     "The caching team evaluated four eviction policies across three cache sizes. Hit rates were measured over a 24-hour production traffic replay.",
     "The diagram shows the specific hit rate percentages per policy and cache size combination. The optimal policy-size combination is marked in the diagram.",
     {"type": "heatmap",
      "rows": ["LRU", "LFU", "ARC", "SLRU"],
      "cols": ["256MB", "512MB", "1GB"],
      "values": [[0.71, 0.82, 0.89], [0.68, 0.79, 0.87], [0.74, 0.85, 0.92], [0.76, 0.87, 0.94]]}),

    ("bench-04", "Message Queue Throughput Benchmark",
     "Message queue throughput comparison across broker configurations.",
     "The infrastructure team benchmarked message throughput for four queue configurations. Tests used 1KB messages with acknowledgment required.",
     "The diagram shows the specific throughput values in messages per second and the producer/consumer counts per configuration. Disk I/O utilization per configuration is visible in the diagram.",
     {"type": "bar", "labels": ["kafka-1p\n1 consumer", "kafka-3p\n3 consumers", "kafka-6p\n6 consumers", "kafka-12p\n12 consumers"],
      "values": [45000, 128000, 247000, 412000], "ylabel": "Messages/sec", "colors": ["#3498DB", "#2ECC71", "#F39C12", "#E74C3C"]}),

    ("bench-05", "ML Model Inference Latency Benchmark",
     "Model inference latency comparison across hardware configurations.",
     "The ML team benchmarked inference latency for the recommendation model across five hardware configurations. Batch size was fixed at 32 samples.",
     "The diagram shows the specific latency values in milliseconds and throughput in samples per second per hardware configuration. GPU memory utilization percentages are visible in the diagram.",
     {"type": "bar", "labels": ["CPU\n32-core", "T4 GPU\n1x", "T4 GPU\n2x", "A100 GPU\n1x", "A100 GPU\n2x"],
      "values": [847, 124, 68, 31, 18], "ylabel": "Inference latency (ms, batch=32)", "colors": ["#E74C3C", "#F39C12", "#F39C12", "#2ECC71", "#2ECC71"]}),

    ("bench-06", "Storage I/O Benchmark",
     "Storage I/O performance comparison across volume types.",
     "The storage team measured read and write IOPS for five EBS volume configurations. Tests used 4KB random I/O with queue depth 32.",
     "The diagram shows the specific read and write IOPS values per volume type and the cost per IOPS. Throughput limits and burst credits are visible in the diagram.",
     {"type": "grouped_bar", "groups": ["gp2\n1TB", "gp3\n1TB", "io1\n1TB\n3000 IOPS", "io2\n1TB\n10000 IOPS", "io2\n1TB\n64000 IOPS"],
      "series": {"read IOPS": [3000, 16000, 3000, 10000, 64000], "write IOPS": [3000, 16000, 3000, 10000, 64000]},
      "ylabel": "IOPS (4KB random, QD=32)"}),

    ("bench-07", "Network Bandwidth Benchmark",
     "Network bandwidth utilization across instance types.",
     "The networking team measured achievable network bandwidth for six EC2 instance types under sustained TCP traffic. Tests used iperf3 with 8 parallel streams.",
     "The diagram shows the specific bandwidth values in Gbps per instance type and the baseline vs burst bandwidth. Cost per Gbps per instance type is visible in the diagram.",
     {"type": "bar", "labels": ["t3.large\n0.5Gbps", "m5.xlarge\n10Gbps", "m5.4xlarge\n10Gbps", "c5n.xlarge\n25Gbps", "c5n.9xlarge\n50Gbps", "c5n.18xlarge\n100Gbps"],
      "values": [0.5, 9.8, 9.9, 24.7, 49.3, 98.1], "ylabel": "Achieved bandwidth (Gbps)", "colors": ["#E74C3C", "#F39C12", "#F39C12", "#2ECC71", "#2ECC71", "#3498DB"]}),

    ("bench-08", "Search Index Performance Benchmark",
     "Search index query performance across shard configurations.",
     "The search team benchmarked query latency and throughput for the product search index across four shard configurations. Tests used a mix of simple and complex queries.",
     "The diagram shows the specific QPS and p99 latency values per shard configuration. Index size and memory usage per configuration are visible in the diagram.",
     {"type": "grouped_bar", "groups": ["1 shard", "3 shards", "6 shards", "12 shards"],
      "series": {"simple query p99 (ms)": [45, 28, 19, 22], "complex query p99 (ms)": [312, 187, 134, 156]},
      "ylabel": "Query latency p99 (ms)"}),

    ("bench-09", "Container Startup Time Benchmark",
     "Container startup time comparison across base image configurations.",
     "The platform team measured container cold start times for five base image configurations. Times include image pull, container creation, and application ready state.",
     "The diagram shows the specific startup times in seconds per phase and base image. Image sizes and layer counts per configuration are visible in the diagram.",
     {"type": "stacked_bar",
      "labels": ["ubuntu:22.04\n+JRE", "alpine:3.18\n+JRE", "distroless\n+JRE", "custom-jre\nalpine", "native-image\nGraalVM"],
      "series": {"image pull (s)": [8.2, 3.1, 2.8, 1.9, 1.2], "container init (s)": [1.1, 0.8, 0.6, 0.5, 0.3], "app ready (s)": [4.2, 4.1, 4.0, 3.8, 0.4]}}),

    ("bench-10", "CDN Cache Performance Benchmark",
     "CDN cache performance comparison across origin configurations.",
     "The CDN team measured cache hit rates and origin offload percentages for five content configurations. Tests used 30 days of production traffic patterns.",
     "The diagram shows the specific hit rates, origin offload percentages, and bandwidth savings per content type. TTL values and cache key configurations are visible in the diagram.",
     {"type": "bar", "labels": ["static-assets\nTTL:86400s", "api-responses\nTTL:60s", "images\nTTL:3600s", "video-segments\nTTL:300s", "html-pages\nTTL:30s"],
      "values": [0.97, 0.43, 0.89, 0.94, 0.31], "ylabel": "Cache hit rate", "colors": ["#2ECC71", "#E74C3C", "#2ECC71", "#2ECC71", "#E74C3C"]}),
]

# ---------------------------------------------------------------------------
# Category 5: Incident Timelines (10 docs) — matplotlib
# ---------------------------------------------------------------------------

INCIDENT_DOCS = [
    ("inc-01", "Database Failover Incident Timeline",
     "Timeline of the database failover incident on 2024-03-15.",
     "A database failover incident occurred due to a storage volume degradation. The incident affected the primary database and required a manual failover to the standby replica.",
     "The diagram shows the specific timestamps, affected components, and recovery actions. Alert thresholds that triggered each notification and the exact failover duration are visible in the diagram.",
     {"events": [
         (0, "14:23:07", "Storage I/O latency spike\nrds-primary: >500ms", "warning"),
         (8, "14:31:12", "CloudWatch alarm\nDiskQueueDepth>100", "warning"),
         (15, "14:38:45", "Primary DB unresponsive\nconnection timeout:30s", "critical"),
         (22, "14:45:00", "PagerDuty alert\nP1 triggered", "critical"),
         (28, "14:51:33", "Manual failover initiated\npatronid promote standby", "action"),
         (35, "14:58:07", "Standby promoted\nrds-replica-1 → primary", "action"),
         (42, "15:05:22", "Application reconnected\nconnection pool reset", "recovery"),
         (50, "15:13:00", "Incident resolved\nRTO: 49m 53s", "resolved"),
     ]}),

    ("inc-02", "CDN Outage Incident Timeline",
     "Timeline of the CDN configuration error incident on 2024-04-02.",
     "A CDN outage was caused by an incorrect cache invalidation rule that purged all cached content simultaneously. The incident caused a 10x spike in origin traffic.",
     "The diagram shows the specific traffic volumes, error rates, and the sequence of configuration changes. Origin server CPU utilization at each stage is visible in the diagram.",
     {"events": [
         (0, "09:14:00", "CDN config deploy\ncache-rules-v2.3 pushed", "action"),
         (3, "09:17:22", "Cache hit rate drops\n97% → 2%", "warning"),
         (7, "09:21:45", "Origin CPU spike\n15% → 94%", "critical"),
         (12, "09:26:00", "Error rate rises\n0.1% → 23%", "critical"),
         (18, "09:32:11", "Config rollback initiated\ncache-rules-v2.2 restored", "action"),
         (25, "09:39:00", "Cache warming begins\nhit rate recovering", "recovery"),
         (35, "09:49:30", "Hit rate restored\n94% cache hit rate", "recovery"),
         (42, "09:56:00", "Incident resolved\nDuration: 42 minutes", "resolved"),
     ]}),

    ("inc-03", "Memory Leak Incident Timeline",
     "Timeline of the memory leak incident in the recommendation service on 2024-05-10.",
     "A memory leak in the recommendation service caused gradual memory exhaustion across all pods. The incident required a rolling restart and a hotfix deployment.",
     "The diagram shows the specific memory usage values at each stage and the pod restart sequence. The commit hash of the hotfix and deployment duration are visible in the diagram.",
     {"events": [
         (0, "02:00:00", "Memory usage baseline\nrec-svc: 2.1GB/4GB", "info"),
         (120, "04:00:00", "Memory usage elevated\nrec-svc: 3.2GB/4GB", "warning"),
         (180, "05:00:00", "OOMKilled: pod-1\nrec-svc-7d9f8b-xk2p1", "critical"),
         (195, "05:15:00", "OOMKilled: pod-2\nrec-svc-7d9f8b-mn4q7", "critical"),
         (210, "05:30:00", "Rolling restart initiated\nkubectl rollout restart", "action"),
         (225, "05:45:00", "Hotfix deployed\ncommit:a3f7c9e2", "action"),
         (240, "06:00:00", "Memory stabilized\nrec-svc: 2.3GB/4GB", "recovery"),
         (255, "06:15:00", "Incident resolved\nDuration: 4h 15m", "resolved"),
     ]}),

    ("inc-04", "Network Partition Incident Timeline",
     "Timeline of the network partition incident affecting the Kafka cluster on 2024-06-18.",
     "A network partition isolated one Kafka broker from the cluster, causing consumer lag to accumulate and triggering downstream processing delays.",
     "The diagram shows the specific consumer lag values, broker IDs affected, and the partition duration. Messages that required reprocessing and the lag recovery rate are visible in the diagram.",
     {"events": [
         (0, "11:42:00", "Network partition detected\nbroker-3 unreachable", "critical"),
         (5, "11:47:00", "Consumer lag spike\ntopic:orders lag=47,832", "warning"),
         (10, "11:52:00", "Leader election\nbroker-3 partitions → broker-1", "action"),
         (18, "12:00:00", "Lag peak reached\ntopic:orders lag=183,291", "critical"),
         (25, "12:07:00", "Network restored\nbroker-3 rejoins cluster", "recovery"),
         (35, "12:17:00", "Lag decreasing\ntopic:orders lag=89,441", "recovery"),
         (55, "12:37:00", "Lag cleared\ntopic:orders lag=0", "resolved"),
         (60, "12:42:00", "Incident resolved\nDuration: 60 minutes", "resolved"),
     ]}),

    ("inc-05", "Certificate Expiry Incident Timeline",
     "Timeline of the TLS certificate expiry incident on 2024-07-22.",
     "A TLS certificate for the payment API expired due to a failed auto-renewal. The incident caused all payment transactions to fail with SSL handshake errors.",
     "The diagram shows the specific certificate serial numbers, expiry timestamps, and the renewal sequence. The number of failed transactions during the outage window is visible in the diagram.",
     {"events": [
         (0, "00:00:00", "Certificate expired\npayment-api.internal\nserial:4A:B2:C3:D4", "critical"),
         (3, "00:03:22", "SSL errors detected\n100% payment failures", "critical"),
         (8, "00:08:45", "PagerDuty P1 alert\npayment-api SSL error", "critical"),
         (15, "00:15:00", "On-call engineer paged\nresponse time: 7m", "action"),
         (22, "00:22:11", "Emergency cert issued\nLet's Encrypt manual", "action"),
         (28, "00:28:33", "Certificate deployed\nnew serial:5E:F6:G7:H8", "action"),
         (32, "00:32:00", "Payment API restored\n0% error rate", "recovery"),
         (35, "00:35:00", "Incident resolved\nDuration: 35 minutes\n1,847 failed transactions", "resolved"),
     ]}),

    ("inc-06", "Deployment Rollback Incident Timeline",
     "Timeline of the failed deployment and rollback on 2024-08-05.",
     "A deployment of the user service introduced a regression in the session management code. The deployment was rolled back after error rates exceeded the SLO threshold.",
     "The diagram shows the specific error rates, deployment versions, and the rollback trigger threshold. The canary traffic percentage at each stage is visible in the diagram.",
     {"events": [
         (0, "15:30:00", "Deployment started\nuser-svc v2.4.1 → v2.4.2\ncanary: 5%", "action"),
         (10, "15:40:00", "Error rate elevated\ncanary: 0.8% errors\nthreshold: 0.5%", "warning"),
         (15, "15:45:00", "Canary paused\nauto-pause triggered", "warning"),
         (20, "15:50:00", "Investigation started\nsession timeout errors", "action"),
         (30, "16:00:00", "Rollback initiated\nv2.4.2 → v2.4.1", "action"),
         (38, "16:08:00", "Rollback complete\nall pods on v2.4.1", "recovery"),
         (42, "16:12:00", "Error rate normalized\n0.02% baseline", "recovery"),
         (45, "16:15:00", "Incident resolved\nDuration: 45 minutes", "resolved"),
     ]}),

    ("inc-07", "DDoS Attack Incident Timeline",
     "Timeline of the DDoS attack and mitigation on 2024-09-12.",
     "A volumetric DDoS attack targeted the public API endpoint. The attack was mitigated through a combination of WAF rules and rate limiting.",
     "The diagram shows the specific attack traffic volumes, mitigation rule names, and the traffic reduction at each stage. The geographic distribution of attack sources is visible in the diagram.",
     {"events": [
         (0, "08:15:00", "Traffic spike detected\n2.3M req/min (baseline: 45K)", "critical"),
         (5, "08:20:00", "WAF rate limit triggered\nrule: ip-rate-limit-1000", "action"),
         (8, "08:23:00", "Attack traffic: 8.7M req/min\norigin CPU: 98%", "critical"),
         (12, "08:27:00", "AWS Shield Advanced\nauto-mitigation activated", "action"),
         (18, "08:33:00", "Traffic scrubbing\n94% attack traffic blocked", "recovery"),
         (25, "08:40:00", "Traffic normalized\n52K req/min", "recovery"),
         (30, "08:45:00", "WAF rules updated\n47 new IP blocks added", "action"),
         (35, "08:50:00", "Incident resolved\nDuration: 35 minutes", "resolved"),
     ]}),

    ("inc-08", "Data Pipeline Lag Incident Timeline",
     "Timeline of the data pipeline lag incident on 2024-10-03.",
     "A data pipeline lag incident occurred when a Spark job failed due to an out-of-memory error. The lag caused downstream dashboards to show stale data.",
     "The diagram shows the specific lag values in minutes, job failure timestamps, and the recovery sequence. The Spark executor memory settings before and after the fix are visible in the diagram.",
     {"events": [
         (0, "06:00:00", "Spark job OOM failure\nenrich-v3 executor killed\nmem:4GB limit", "critical"),
         (5, "06:05:00", "Pipeline lag: 12 minutes\nevents-enriched topic", "warning"),
         (15, "06:15:00", "Lag: 47 minutes\ndownstream dashboards stale", "critical"),
         (20, "06:20:00", "Job restarted\nmem limit: 4GB → 8GB", "action"),
         (30, "06:30:00", "Lag: 89 minutes\njob processing backlog", "warning"),
         (60, "07:00:00", "Lag decreasing\n34 minutes remaining", "recovery"),
         (90, "07:30:00", "Lag cleared\npipeline current", "resolved"),
         (95, "07:35:00", "Incident resolved\nDuration: 95 minutes", "resolved"),
     ]}),

    ("inc-09", "Secret Rotation Incident Timeline",
     "Timeline of the secret rotation failure incident on 2024-11-14.",
     "An automated secret rotation job failed to update the database credentials in all services. Several services began failing with authentication errors after the old credentials expired.",
     "The diagram shows the specific service names affected, credential expiry timestamps, and the manual rotation sequence. The number of failed requests per service during the incident is visible in the diagram.",
     {"events": [
         (0, "03:00:00", "Rotation job started\ndb-credentials-prod", "action"),
         (5, "03:05:00", "Rotation job failed\nvault-agent timeout", "critical"),
         (60, "04:00:00", "Old credentials expired\ndb-password-v12", "critical"),
         (62, "04:02:00", "Auth errors: order-svc\n847 failed requests", "critical"),
         (65, "04:05:00", "Auth errors: payment-svc\n1,203 failed requests", "critical"),
         (70, "04:10:00", "Manual rotation started\nvault write db/rotate-root", "action"),
         (78, "04:18:00", "Credentials updated\nall services restarted", "action"),
         (82, "04:22:00", "Incident resolved\nDuration: 82 minutes", "resolved"),
     ]}),

    ("inc-10", "Cascading Failure Incident Timeline",
     "Timeline of the cascading failure incident affecting multiple services on 2024-12-01.",
     "A cascading failure was triggered by a slow database query that caused connection pool exhaustion in the order service, which then propagated to dependent services.",
     "The diagram shows the specific connection pool sizes, timeout values, and the cascade propagation sequence. The circuit breaker states and trip thresholds are visible in the diagram.",
     {"events": [
         (0, "19:45:00", "Slow query detected\norders table full scan\n>30s execution", "warning"),
         (3, "19:48:00", "Connection pool exhausted\norder-svc pool:50/50", "critical"),
         (6, "19:51:00", "order-svc timeout\ndownstream: inventory-svc", "critical"),
         (9, "19:54:00", "inventory-svc CB open\nthreshold: 50% errors", "critical"),
         (12, "19:57:00", "payment-svc degraded\norder-svc dependency", "critical"),
         (15, "20:00:00", "Query killed\nkill query 48291", "action"),
         (20, "20:05:00", "Connection pool draining\norder-svc recovering", "recovery"),
         (28, "20:13:00", "CBs closed\nall services recovered", "recovery"),
         (32, "20:17:00", "Incident resolved\nDuration: 32 minutes", "resolved"),
     ]}),
]


# ---------------------------------------------------------------------------
# Diagram renderers
# ---------------------------------------------------------------------------

def _render_graphviz(nodes, edges, title: str, name: str) -> str:
    g = graphviz.Digraph(comment=title)
    g.attr(rankdir="LR", label=title, labelloc="t", fontsize="14", fontname="Helvetica")
    g.attr("node", fontname="Helvetica", fontsize="10")
    # Use index-based IDs to avoid Graphviz interpreting colons as port specs
    id_map = {}
    for i, (node_label, attrs) in enumerate(nodes):
        node_id = f"n{i}"
        id_map[node_label] = node_id
        attr_dict = dict(a.split("=", 1) for a in attrs.split(","))
        # Replace \n: with \nport: so VLM reads port numbers correctly
        display_label = node_label.replace("\n:", "\nport:")
        attr_dict["label"] = display_label
        g.node(node_id, **attr_dict)
    for src, dst in edges:
        g.edge(id_map[src], id_map[dst])
    return _save_gv(g, name)


def _render_bar(data: dict, name: str) -> str:
    chart_type = data["type"]
    fig, ax = plt.subplots(figsize=(9, 5))

    if chart_type == "bar":
        colors = data.get("colors", ["#3498DB"] * len(data["labels"]))
        bars = ax.bar(data["labels"], data["values"], color=colors, edgecolor="black", linewidth=0.8)
        for bar, val in zip(bars, data["values"]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.01,
                    f"{val:,}" if isinstance(val, int) else f"{val:.2f}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.set_ylabel(data["ylabel"], fontsize=11)
        ax.set_ylim(0, max(data["values"]) * 1.2)

    elif chart_type == "grouped_bar":
        groups = data["groups"]
        series = data["series"]
        x = np.arange(len(groups))
        width = 0.8 / len(series)
        colors = ["#3498DB", "#E74C3C", "#2ECC71", "#F39C12"]
        for i, (label, vals) in enumerate(series.items()):
            offset = (i - len(series) / 2 + 0.5) * width
            bars = ax.bar(x + offset, vals, width, label=label, color=colors[i % len(colors)], edgecolor="black", linewidth=0.6)
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.01,
                        str(val), ha="center", va="bottom", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(groups, fontsize=9)
        ax.set_ylabel(data["ylabel"], fontsize=11)
        ax.legend(fontsize=9)

    elif chart_type == "stacked_bar":
        labels = data["labels"]
        series = data["series"]
        x = np.arange(len(labels))
        colors = ["#3498DB", "#E74C3C", "#2ECC71"]
        bottom = np.zeros(len(labels))
        for i, (label, vals) in enumerate(series.items()):
            ax.bar(x, vals, bottom=bottom, label=label, color=colors[i % len(colors)], edgecolor="black", linewidth=0.6)
            for j, (b, v) in enumerate(zip(bottom, vals)):
                if v > 0.3:
                    ax.text(j, b + v / 2, f"{v:.1f}s", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
            bottom += np.array(vals)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel("Time (seconds)", fontsize=11)
        ax.legend(fontsize=9)

    elif chart_type == "heatmap":
        vals = np.array(data["values"])
        im = ax.imshow(vals, cmap="RdYlGn", vmin=0.6, vmax=1.0)
        ax.set_xticks(range(len(data["cols"])))
        ax.set_yticks(range(len(data["rows"])))
        ax.set_xticklabels(data["cols"], fontsize=11)
        ax.set_yticklabels(data["rows"], fontsize=11)
        for i in range(len(data["rows"])):
            for j in range(len(data["cols"])):
                ax.text(j, i, f"{vals[i,j]:.0%}", ha="center", va="center", fontsize=12, fontweight="bold")
        plt.colorbar(im, ax=ax, label="Hit Rate")

    ax.set_title(name.replace("-", " ").title(), fontsize=13, fontweight="bold", pad=10)
    plt.tight_layout()
    return _save_fig(name)


def _render_timeline(data: dict, name: str) -> str:
    events = data["events"]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(-5, max(e[0] for e in events) + 10)
    ax.set_ylim(-1, 1)
    ax.axis("off")

    colors = {"info": "#3498DB", "warning": "#F39C12", "critical": "#E74C3C",
              "action": "#9B59B6", "recovery": "#2ECC71", "resolved": "#27AE60"}

    ax.axhline(0, color="gray", linewidth=2, zorder=1)

    for i, (minutes, timestamp, label, severity) in enumerate(events):
        color = colors.get(severity, "#95A5A6")
        ax.scatter(minutes, 0, s=200, color=color, zorder=3, edgecolors="black", linewidth=1)
        y_offset = 0.35 if i % 2 == 0 else -0.35
        ax.annotate(f"{timestamp}\n{label}", xy=(minutes, 0), xytext=(minutes, y_offset),
                    ha="center", va="bottom" if y_offset > 0 else "top",
                    fontsize=7.5, fontweight="bold" if severity in ("critical", "resolved") else "normal",
                    arrowprops=dict(arrowstyle="-", color=color, lw=1),
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=color, alpha=0.3, edgecolor=color))

    legend_patches = [mpatches.Patch(color=c, label=s) for s, c in colors.items()]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=8, ncol=3)
    ax.set_title(name.replace("-", " ").title(), fontsize=13, fontweight="bold")
    plt.tight_layout()
    return _save_fig(name)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    IMGS.mkdir(exist_ok=True)

    docs_written = 0

    # Category 1: Deployment topologies
    for slug, title, description, overview, details, nodes, edges in DEPLOY_DOCS:
        img_rel = _render_graphviz(nodes, edges, title, slug)
        content = _doc(title, description, overview, img_rel, details)
        (OUT / f"{slug}.md").write_text(content)
        docs_written += 1

    # Category 2: System architectures
    for slug, title, description, overview, details, nodes, edges in ARCH_DOCS:
        img_rel = _render_graphviz(nodes, edges, title, slug)
        content = _doc(title, description, overview, img_rel, details)
        (OUT / f"{slug}.md").write_text(content)
        docs_written += 1

    # Category 3: Network topologies
    for slug, title, description, overview, details, nodes, edges in NET_DOCS:
        img_rel = _render_graphviz(nodes, edges, title, slug)
        content = _doc(title, description, overview, img_rel, details)
        (OUT / f"{slug}.md").write_text(content)
        docs_written += 1

    # Category 4: Benchmark charts
    for slug, title, description, overview, details, chart_data in BENCH_DOCS:
        img_rel = _render_bar(chart_data, slug)
        content = _doc(title, description, overview, img_rel, details)
        (OUT / f"{slug}.md").write_text(content)
        docs_written += 1

    # Category 5: Incident timelines
    for slug, title, description, overview, details, timeline_data in INCIDENT_DOCS:
        img_rel = _render_timeline(timeline_data, slug)
        content = _doc(title, description, overview, img_rel, details)
        (OUT / f"{slug}.md").write_text(content)
        docs_written += 1

    print(f"✅ Generated {docs_written} documents in {OUT}")
    print(f"   Images: {len(list(IMGS.glob('*.png')))} PNGs in {IMGS}")


if __name__ == "__main__":
    generate()
