"""High-quality benchmark queries for RAG evaluation."""
from tests.benchmark import BenchmarkQuery

# Test queries with ground truth
BENCHMARK_QUERIES = [
    # EASY: Direct concept matches
    BenchmarkQuery(
        query="What is semantic search?",
        difficulty="easy",
        expected_sources=[
            "tests/fixtures/sample_docs/semantic-search.md",
            "tests/fixtures/sample_docs/vector-databases.md"
        ],
        expected_content=["semantic search", "meaning", "intent"],
        category="core"
    ),
    BenchmarkQuery(
        query="vector database",
        difficulty="easy",
        expected_sources=[
            "tests/fixtures/sample_docs/vector-databases.md",
            "tests/fixtures/sample_docs/semantic-search.md"
        ],
        expected_content=["vector", "embeddings", "similarity"],
        category="core"
    ),
    BenchmarkQuery(
        query="REST API design",
        difficulty="easy",
        expected_sources=[
            "tests/fixtures/sample_docs/api-design.md",
            "tests/fixtures/sample_docs/microservices.md"
        ],
        expected_content=["REST", "HTTP", "endpoints"],
        category="core"
    ),
    BenchmarkQuery(
        query="database normalization",
        difficulty="easy",
        expected_sources=[
            "tests/fixtures/sample_docs/database-design.md",
            "tests/fixtures/sample_docs/vector-databases.md"
        ],
        expected_content=["normalization", "1NF", "2NF", "3NF"],
        category="core"
    ),
    
    # MEDIUM: Requires understanding context
    BenchmarkQuery(
        query="How do I handle negation in search queries?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/sample_docs/semantic-search.md"
        ],
        expected_content=["negation", "preprocessing", "without", "not"],
        category="core"
    ),
    BenchmarkQuery(
        query="What are microservices communication patterns?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/sample_docs/microservices.md",
            "tests/fixtures/sample_docs/api-design.md"
        ],
        expected_content=["synchronous", "asynchronous", "message", "REST"],
        category="core"
    ),
    BenchmarkQuery(
        query="How should I implement caching?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/sample_docs/caching.md",
            "tests/fixtures/sample_docs/semantic-search.md"
        ],
        expected_content=["cache", "pattern", "TTL", "invalidation"],
        category="core"
    ),
    BenchmarkQuery(
        query="What's the difference between authentication and authorization?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/sample_docs/authentication.md",
            "tests/fixtures/sample_docs/api-design.md"
        ],
        expected_content=["authentication", "authorization", "who", "what"],
        category="core"
    ),
    BenchmarkQuery(
        query="When should I denormalize a database?",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/sample_docs/database-design.md",
            "tests/fixtures/sample_docs/caching.md"
        ],
        expected_content=["denormalization", "read-heavy", "performance"],
        category="core"
    ),
    
    # HARD: Multi-hop reasoning or specific details
    BenchmarkQuery(
        query="How do I design a scalable API with proper caching?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/api-design.md",
            "tests/fixtures/sample_docs/caching.md",
            "tests/fixtures/sample_docs/microservices.md"
        ],
        expected_content=["API", "cache", "performance", "scalable"],
        category="core"
    ),
    BenchmarkQuery(
        query="What are the security considerations for JWT tokens?",
        difficulty="hard",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        expected_content=["JWT", "security", "expiration", "HTTPS"],
        category="core"
    ),
    BenchmarkQuery(
        query="How do microservices handle data consistency?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/microservices.md",
            "tests/fixtures/sample_docs/database-design.md"
        ],
        expected_content=["saga", "consistency", "distributed", "transaction"],
        category="core"
    ),
    
    # EDGE CASES: Test robustness
    BenchmarkQuery(
        query="OAuth 2.0 flows",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/sample_docs/authentication.md",
            "tests/fixtures/sample_docs/api-design.md"
        ],
        expected_content=["OAuth", "authorization", "flow"],
        category="core"
    ),
    BenchmarkQuery(
        query="cache eviction policies",
        difficulty="medium",
        expected_sources=[
            "tests/fixtures/sample_docs/caching.md",
            "tests/fixtures/sample_docs/semantic-search.md"
        ],
        expected_content=["LRU", "LFU", "eviction"],
        category="core"
    ),
    BenchmarkQuery(
        query="API versioning strategies",
        difficulty="easy",
        expected_sources=[
            "tests/fixtures/sample_docs/api-design.md",
            "tests/fixtures/sample_docs/authentication.md"
        ],
        expected_content=["version", "v1", "v2"],
        category="core"
    ),

    # AGENT: Complex multi-part (MOCKING DECOMPOSITION)
    BenchmarkQuery(
        query="How do microservices handle authentication while maintaining cache consistency across distributed services?",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/microservices.md",
            "tests/fixtures/sample_docs/authentication.md",
            "tests/fixtures/sample_docs/caching.md"
        ],
        expected_content=["authentication", "cache", "distributed", "service"],
        category="agent",
        sub_queries=[
            "microservices authentication patterns",
            "maintaining cache consistency in distributed systems",
            "authentication and caching in microservices"
        ]
    ),
    BenchmarkQuery(
        query="Compare session-based auth with JWT tokens and explain when to use each with API versioning",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/authentication.md",
            "tests/fixtures/sample_docs/api-design.md"
        ],
        expected_content=["session", "JWT", "stateless", "version"],
        category="agent",
        sub_queries=[
            "compare session-based vs JWT authentication",
            "API versioning strategies with authentication",
            "when to use JWT vs session cookies"
        ]
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
        expected_content=["OAuth", "JWT", "cache", "REST", "pagination"],
        category="agent",
        sub_queries=[
            "user authentication with OAuth 2.0 and JWT",
            "caching strategies and invalidation patterns",
            "REST API design with versioning and pagination",
            "building microservices for web applications"
        ]
    ),

    # ABSTRACT/CONCEPTUAL: High-level
    BenchmarkQuery(
        query="distributed systems design principles",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/microservices.md",
            "tests/fixtures/sample_docs/api-design.md",
            "tests/fixtures/sample_docs/vector-databases.md"
        ],
        expected_content=["independent", "decentralized", "service"],
        category="core"
    ),
    BenchmarkQuery(
        query="trade-offs between consistency and performance in data architecture",
        difficulty="hard",
        expected_sources=[
            "tests/fixtures/sample_docs/database-design.md",
            "tests/fixtures/sample_docs/caching.md"
        ],
        expected_content=["denormalization", "read-heavy", "cache", "stale"],
        category="core"
    ),

    # ADVERSARIAL: Robustness (Success = 0 results)
    BenchmarkQuery(
        query="quantum entanglement in photosynthesis",
        difficulty="hard",
        expected_sources=[],
        expected_content=[],
        category="core"
    ),

    # NEGATION: Tests preprocessing
    BenchmarkQuery(
        query="caching strategies without Redis",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/caching.md"],
        expected_content=["cache", "pattern", "TTL"],
        category="core"
    ),
    BenchmarkQuery(
        query="authentication methods not using passwords",
        difficulty="medium",
        expected_sources=["tests/fixtures/sample_docs/authentication.md"],
        expected_content=["OAuth", "MFA", "biometric"],
        category="core"
    ),
]
