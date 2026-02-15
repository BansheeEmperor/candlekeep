import json
from pathlib import Path

# Base queries from existing benchmark
queries = [
    {
        "query": "What is semantic search?",
        "difficulty": "easy",
        "expected_sources": ["tests/fixtures/sample_docs/semantic-search.md"],
        "category": "semantic"
    },
    {
        "query": "vector database",
        "difficulty": "easy",
        "expected_sources": ["tests/fixtures/sample_docs/vector-databases.md"],
        "category": "semantic"
    },
    {
        "query": "REST API design",
        "difficulty": "easy",
        "expected_sources": ["tests/fixtures/sample_docs/api-design.md"],
        "category": "semantic"
    },
    {
        "query": "database normalization",
        "difficulty": "easy",
        "expected_sources": ["tests/fixtures/sample_docs/database-design.md"],
        "category": "semantic"
    }
]

# Lexical Hard (30%) - Focus on versioning, specific tech names, codes
lexical_queries = [
    {"query": "HTTP/2 vs HTTP/3 performance", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/http2-http3.md"], "category": "lexical"},
    {"query": "PostgreSQL 15 internals", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/postgresql-internals.md"], "category": "lexical"},
    {"query": "Apache Kafka 3.0 features", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/apache-kafka.md"], "category": "lexical"},
    {"query": "TLS 1.3 handshake process", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/tls-ssl.md"], "category": "lexical"},
    {"query": "Kubernetes v1.24 removal of dockershim", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/kubernetes-architecture.md"], "category": "lexical"},
    {"query": "gRPC over HTTP/2", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/grpc-protocol.md"], "category": "lexical"},
    {"query": "Redis 7.0 Multi-part AOF", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/redis-data-structures.md"], "category": "lexical"},
    {"query": "Elasticsearch 8.x security changes", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/elasticsearch-basics.md"], "category": "lexical"},
    {"query": "OWASP Top 10 2021", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/owasp-top-10.md"], "category": "lexical"},
    {"query": "AVX-512 vector instructions", "difficulty": "hard", "expected_sources": ["docs/HARDWARE_ACCEL.md"], "category": "lexical"},
    {"query": "TCP/IP layer 4", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/tcp-ip-fundamentals.md"], "category": "lexical"},
    {"query": "IPv6 address format", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/cloud-networking.md"], "category": "lexical"},
    {"query": "UUID v4 generation", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/data-serialization.md"], "category": "lexical"},
    {"query": "0xEF hex code", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/cryptography-basics.md"], "category": "lexical"},
    {"query": "Python 3.10 match statement", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/functional-programming.md"], "category": "lexical"},
    {"query": "ISO 27001 compliance", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/compliance-frameworks.md"], "category": "lexical"},
    {"query": "SOC2 Type II audit", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/compliance-frameworks.md"], "category": "lexical"},
    {"query": "BGE-small-en-v1.5 model", "difficulty": "medium", "expected_sources": ["docs/ARCHITECTURE.md"], "category": "lexical"},
    {"query": "ChromaDB v0.4.0", "difficulty": "medium", "expected_sources": ["docs/DESIGN.md"], "category": "lexical"},
    {"query": "MS-MARCO MiniLM L-6-v2", "difficulty": "hard", "expected_sources": ["docs/RESEARCH_DIARY.md"], "category": "lexical"},
    {"query": "JWT RS256 signing", "difficulty": "hard", "expected_sources": ["tests/fixtures/sample_docs/authentication.md"], "category": "lexical"},
    {"query": "OAuth 2.0 PKCE flow", "difficulty": "hard", "expected_sources": ["tests/fixtures/sample_docs/authentication.md"], "category": "lexical"},
    {"query": "RAID 6 configurations", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/database-backup-recovery.md"], "category": "lexical"},
    {"query": "SQL-92 standards", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/sql-query-optimization.md"], "category": "lexical"},
    {"query": "POSIX thread management", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/linux-process-management.md"], "category": "lexical"},
    {"query": "systemd unit files", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/systemd-services.md"], "category": "lexical"},
    {"query": "EXT4 filesystem limits", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/linux-filesystem.md"], "category": "lexical"},
    {"query": "YAML 1.2 syntax", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/configuration-management.md"], "category": "lexical"},
    {"query": "Docker Compose v2", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/container-fundamentals.md"], "category": "lexical"},
    {"query": "AWS IAM policies", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/api-security.md"], "category": "lexical"},
]

# Semantic Soft (40%) - Concepts from scale_docs
semantic_queries = [
    {"query": "how to implement chaos engineering", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/chaos-engineering.md"], "category": "semantic"},
    {"query": "benefits of event-driven architecture", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/event-driven-architecture.md"], "category": "semantic"},
    {"query": "serverless vs containers", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/serverless-architecture.md"], "category": "semantic"},
    {"query": "microservices data consistency", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/microservices.md"], "category": "semantic"},
    {"query": "data lakehouse architecture", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/data-lake-architecture.md"], "category": "semantic"},
    {"query": "zero trust security principles", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/zero-trust-architecture.md"], "category": "semantic"},
    {"query": "continuous integration best practices", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/ci-cd-pipelines.md"], "category": "semantic"},
    {"query": "database sharding strategies", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/database-sharding.md"], "category": "semantic"},
    {"query": "load balancing algorithms", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/load-balancing.md"], "category": "semantic"},
    {"query": "content delivery network optimization", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/cdn-architecture.md"], "category": "semantic"},
    {"query": "service mesh advantages", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/service-mesh.md"], "category": "semantic"},
    {"query": "infrastructure as code tools", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/infrastructure-as-code.md"], "category": "semantic"},
    {"query": "monitoring vs observability", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/monitoring-observability.md"], "category": "semantic"},
    {"query": "auto scaling in the cloud", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/auto-scaling.md"], "category": "semantic"},
    {"query": "disaster recovery planning", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/disaster-recovery.md"], "category": "semantic"},
    {"query": "api gateway patterns", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/api-gateway-patterns.md"], "category": "semantic"},
    {"query": "cloud storage options", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/cloud-storage-options.md"], "category": "semantic"},
    {"query": "data serialization formats", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/data-serialization.md"], "category": "semantic"},
    {"query": "message queue patterns", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/event-driven-architecture.md"], "category": "semantic"},
    {"query": "functional programming concepts", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/functional-programming.md"], "category": "semantic"},
    {"query": "linux memory management", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/linux-memory-management.md"], "category": "semantic"},
    {"query": "dns resolution process", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/dns-resolution.md"], "category": "semantic"},
    {"query": "connection pooling benefits", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/connection-pooling.md"], "category": "semantic"},
    {"query": "cryptography basics", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/cryptography-basics.md"], "category": "semantic"},
    {"query": "distributed transactions", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/concurrency-patterns.md"], "category": "semantic"},
    {"query": "container security hardening", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/container-security.md"], "category": "semantic"},
    {"query": "well architected framework", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/well-architected-framework.md"], "category": "semantic"},
    {"query": "cost optimization strategies", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/cost-optimization.md"], "category": "semantic"},
    {"query": "incident response steps", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/incident-response.md"], "category": "semantic"},
    {"query": "multi-region deployment", "difficulty": "hard", "expected_sources": ["tests/fixtures/scale_docs/multi-region-deployment.md"], "category": "semantic"},
    {"query": "ssh configuration security", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/ssh-configuration.md"], "category": "semantic"},
    {"query": "vpn tunneling protocols", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/vpn-tunneling.md"], "category": "semantic"},
    {"query": "websocket protocol overview", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/websocket-protocol.md"], "category": "semantic"},
    {"query": "helm charts fundamentals", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/helm-charts.md"], "category": "semantic"},
    {"query": "linux process management", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/linux-process-management.md"], "category": "semantic"},
    {"query": "network troubleshooting tools", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/network-troubleshooting.md"], "category": "semantic"},
    {"query": "database replication types", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/database-replication.md"], "category": "semantic"},
    {"query": "nosql design patterns", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/nosql-patterns.md"], "category": "semantic"},
    {"query": "sql query optimization", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/sql-query-optimization.md"], "category": "semantic"},
    {"query": "data pipeline design", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/data-pipeline-design.md"], "category": "semantic"},
    {"query": "testing strategies for software", "difficulty": "easy", "expected_sources": ["tests/fixtures/scale_docs/testing-strategies.md"], "category": "semantic"},
    {"query": "dependency injection benefits", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/dependency-injection.md"], "category": "semantic"},
    {"query": "behavioral design patterns", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/design-patterns-behavioral.md"], "category": "semantic"},
    {"query": "creational design patterns", "difficulty": "medium", "expected_sources": ["tests/fixtures/scale_docs/design-patterns-creational.md"], "category": "semantic"},
]

# Adversarial/Noise (30%) - Should hit the 0.75 threshold
adversarial_queries = [
    {"query": "how to bake sourdough in a kubernetes cluster", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "best brand of hiking boots for Mars", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "quantum entanglement in photosynthesis", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "the secret to eternal life according to python docs", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "where did I leave my keys", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "recipe for disaster in distributed systems", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "blue whales vs sperm whales", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "history of the Roman Empire", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "how to play the banjo", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "why is the sky blue", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "symptoms of a cold", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "movie recommendations for tonight", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "stock market predictions for 2026", "difficulty": "hard", "expected_sources": [], "category": "adversarial"},
    {"query": "philosophy of mind and AI", "difficulty": "hard", "expected_sources": [], "category": "adversarial"},
    {"query": "meaning of life 42", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "how to win friends and influence people", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "yoga for beginners", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "best coffee shops in London", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "gardening tips for summer", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "how to repair a flat tire", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "history of the internet", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "space travel in the future", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "the art of war summary", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "meditation techniques", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "learning a new language fast", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "climate change impacts", "difficulty": "medium", "expected_sources": [], "category": "adversarial"},
    {"query": "renewable energy sources", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "healthy eating habits", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "travel tips for Japan", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
    {"query": "basics of photography", "difficulty": "easy", "expected_sources": [], "category": "adversarial"},
]

all_queries = queries + lexical_queries + semantic_queries + adversarial_queries

output = {
    "metadata": {
        "name": "Centurion Set",
        "version": "1.0",
        "total_queries": len(all_queries),
        "categories": ["lexical", "semantic", "adversarial"]
    },
    "queries": all_queries
}

with open("tests/fixtures/eval_suite_100.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Generated {len(all_queries)} queries in tests/fixtures/eval_suite_100.json")
