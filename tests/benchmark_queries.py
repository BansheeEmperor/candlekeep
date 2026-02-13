"""High-quality benchmark queries for RAG evaluation."""
from tests.benchmark import BenchmarkQuery

# Test queries with ground truth
BENCHMARK_QUERIES = [
    # EASY: Direct concept matches
    BenchmarkQuery(
        query="What is semantic search?",
        difficulty="easy",
        expected_sources=["tests/fixtures/sample_docs/semantic-search.md"],
        expected_content=["semantic search", "meaning", "intent"]
    ),
    BenchmarkQuery(
        query="vector database",
        difficulty="easy",
        expected_sources=["tests/fixtures/sample_docs/vector-databases.md"],
        expected_content=["vector", "embeddings", "similarity"]
    ),
    BenchmarkQuery(
        query="REST API design",
        difficulty="easy",
        expected_sources=["tests/fixtures/sample_docs/api-design.md"],
        expected_content=["REST", "HTTP", "endpoints"]
    ),
    BenchmarkQuery(
        query="database normalization",
        difficulty="easy",
        expected_sources=["tests/fixtures/sample_docs/database-design.md"],
        expected_content=["normalization", "1NF", "2NF", "3NF"]
    ),
    
    # MEDIUM: Requires understanding context
    BenchmarkQuery(
        query="How do I handle negation in search queries?",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/semantic-search.md"],
        expected_content=["negation", "preprocessing", "without", "not"]
    ),
    BenchmarkQuery(
        query="What are microservices communication patterns?",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/microservices.md"],
        expected_content=["synchronous", "asynchronous", "message", "REST"]
    ),
    BenchmarkQuery(
        query="How should I implement caching?",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/caching.md"],
        expected_content=["cache", "pattern", "TTL", "invalidation"]
    ),
    BenchmarkQuery(
        query="What's the difference between authentication and authorization?",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        expected_content=["authentication", "authorization", "who", "what"]
    ),
    BenchmarkQuery(
        query="When should I denormalize a database?",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/database-design.md"],
        expected_content=["denormalization", "read-heavy", "performance"]
    ),
    
    # HARD: Multi-hop reasoning or specific details
    BenchmarkQuery(
        query="How do I design a scalable API with proper caching?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/api-design.md",
            "tests/fixtures/sample_docs/caching.md"
        ],
        expected_content=["API", "cache", "performance", "scalable"]
    ),
    BenchmarkQuery(
        query="What are the security considerations for JWT tokens?",
        difficulty="hard",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        expected_content=["JWT", "security", "expiration", "HTTPS"]
    ),
    BenchmarkQuery(
        query="How do microservices handle data consistency?",
        difficulty="hard",
        expected_sources=["tests/fixtures/sample_docs/microservices.md"],
        expected_content=["saga", "consistency", "distributed", "transaction"]
    ),
    
    # EDGE CASES: Test robustness
    BenchmarkQuery(
        query="OAuth 2.0 flows",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        expected_content=["OAuth", "authorization", "flow"]
    ),
    BenchmarkQuery(
        query="cache eviction policies",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/caching.md"],
        expected_content=["LRU", "LFU", "eviction"]
    ),
    BenchmarkQuery(
        query="API versioning strategies",
        difficulty="easy",
        expected_sources=["tests/fixtures/sample_docs/api-design.md"],
        expected_content=["version", "v1", "v2"]
    ),

    # COMPLEX MULTI-PART: Spans multiple documents
    BenchmarkQuery(
        query="How do microservices handle authentication while maintaining cache consistency across distributed services?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/microservices.md",
            "tests/fixtures/sample_docs/authentication.md",
            "tests/fixtures/sample_docs/caching.md"
        ],
        expected_content=["authentication", "cache", "distributed", "service"]
    ),
    BenchmarkQuery(
        query="Compare session-based auth with JWT tokens and explain when to use each with API versioning",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/authentication.md",
            "tests/fixtures/sample_docs/api-design.md"
        ],
        expected_content=["session", "JWT", "stateless", "version"]
    ),

    # ABSTRACT/CONCEPTUAL: High-level, vocabulary mismatch likely
    BenchmarkQuery(
        query="distributed systems design principles",
        difficulty="hard",
        expected_sources=["tests/fixtures/sample_docs/microservices.md"],
        expected_content=["independent", "decentralized", "service"]
    ),
    BenchmarkQuery(
        query="trade-offs between consistency and performance in data architecture",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/database-design.md",
            "tests/fixtures/sample_docs/caching.md"
        ],
        expected_content=["denormalization", "read-heavy", "cache", "stale"]
    ),

    # ADVERSARIAL/STRESS: Edge cases
    BenchmarkQuery(
        query="quantum entanglement in photosynthesis",
        difficulty="hard",
        expected_sources=[],
        expected_content=[]
    ),
    BenchmarkQuery(
        query="I need to understand how to build a complete web application that handles user authentication with OAuth 2.0 and JWT tokens while also implementing a caching layer with proper cache invalidation strategies and designing a RESTful API with versioning and pagination for large datasets across multiple microservices",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/authentication.md",
            "tests/fixtures/sample_docs/caching.md",
            "tests/fixtures/sample_docs/api-design.md",
            "tests/fixtures/sample_docs/microservices.md"
        ],
        expected_content=["OAuth", "JWT", "cache", "REST", "pagination"]
    ),

    # NEGATION: Tests preprocessing
    BenchmarkQuery(
        query="caching strategies without Redis",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/caching.md"],
        expected_content=["cache", "pattern", "TTL"]
    ),
    BenchmarkQuery(
        query="authentication methods not using passwords",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        expected_content=["OAuth", "MFA", "biometric"]
    ),
]
