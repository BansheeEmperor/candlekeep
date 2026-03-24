# Track 2 Benchmark Annotation Request

## Background

We are benchmarking two retrieval systems — Candlekeep and Amazon Bedrock Knowledge Bases — on their ability to surface related documents that are not directly mentioned in a query (entity/concept expansion).

The current Track 2 benchmark uses queries that were generated programmatically from the corpus, which introduces bias toward one system. We need human-annotated queries to make the comparison neutral.

## Corpus

88 technical software documentation files covering topics including:
- Kubernetes, containers, service mesh
- Databases (PostgreSQL, Redis, Elasticsearch)
- Security (OWASP, zero-trust, container security)
- Cloud architecture (AWS, CDN, multi-region)
- Data pipelines, stream processing, Kafka
- CI/CD, infrastructure as code, monitoring

Files are in `tests/fixtures/scale_docs/` and `tests/fixtures/sample_docs/`.

## What We Need

**20–30 multi-hop questions** where answering the question fully requires reading at least two documents that cover related but distinct concepts.

A good question:
- Can be answered by reading doc A, but a *complete* answer also requires doc B
- Does not mention the specific technical term that appears only in doc B
- Is a realistic question a developer would actually ask

**Example of a good question:**
> "What should I consider when designing a system that needs to handle both real-time event processing and long-term data storage?"

This requires connecting stream processing concepts (Kafka, Flink) with data warehouse/lake concepts — two separate document areas.

**Example of a bad question:**
> "How does Kafka integrate with data lakes?"

This is bad because it explicitly names both concepts, making it a direct retrieval question rather than a multi-hop one.

## Deliverables

A JSON file with the following structure:

```json
[
  {
    "query": "What should I consider when designing a system that needs to handle both real-time event processing and long-term data storage?",
    "supporting_docs": [
      "stream-processing.md",
      "data-lake-architecture.md"
    ],
    "notes": "Requires connecting Kafka/Flink concepts with data lake storage patterns"
  }
]
```

Each entry must have:
- `query`: the question (written without looking at entity graphs or system internals)
- `supporting_docs`: 2–4 filenames from the corpus that together answer the question
- `notes`: brief explanation of why multiple docs are needed

## Constraints

- Do **not** look at any system's entity graph or co-occurrence data before writing queries
- Read the documents directly and write questions based on what you find
- At least one supporting doc per query should not be findable by a simple keyword search on the query text
- Aim for variety across topic areas — don't cluster all questions around security or all around databases
