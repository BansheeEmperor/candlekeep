```
                                    .
                                   /|\
                                  / | \
                                 /  |  \
                                /   |   \
                               /____|____\
                              |    ___    |
                              |   |   |   |
                         _____|___|___|___|_____
                        |  _    _    _    _    |
                        | |_|  |_|  |_|  |_|  |
                        |  _    _    _    _    |
                        | |_|  |_|  |_|  |_|  |
                   _____|________________________|_____
                  |  ___   ___   _______   ___   ___  |
                  | |   | |   | |       | |   | |   | |
                  | |   | |   | |       | |   | |   | |
                  | |___| |___| |_______| |___| |___| |
                  |___________________________________|
                  |  |     |     |     |     |     |  |
                  |  |     |     |     |     |     |  |
              ____|__|_____|_____|_____|_____|_____|__|____
             /________________________________________________\
            /__________________________________________________ \
```

# Candlekeep

*The great library fortress on the Sword Coast, where all knowledge is preserved.*

A RAG knowledge base server that gives AI agents the power to search, retrieve, and manage technical documentation through the Model Context Protocol. Ask a question, and the library answers — with the right scroll, expanded to full context, in milliseconds.

## The Arcane Arts

- [**Bardic Knowledge**](docs/GLOSSARY.md#bardic-knowledge) — Documents are enriched with title and description at ingestion, woven into every embedding
- [**Bardic Inspiration**](docs/GLOSSARY.md#bardic-inspiration) — Result-time metadata boosting that ensures specific technical guides outrank generic content
- [**Arcane Recall**](docs/GLOSSARY.md#arcane-recall) — Intelligent expansion using [**Scholar's Discernment**](docs/GLOSSARY.md#the-scholars-discernment) and [**Arcane Coalescence**](docs/GLOSSARY.md#arcane-coalescence) to return full sections without token waste
- [**Wild Magic**](docs/GLOSSARY.md#lexical-matching-bm25) — Hybrid retrieval merging Vector and BM25 (lexical) search, fixing "keyword blindness" for exact identifiers
- [**Divine Insight**](docs/GLOSSARY.md#cross-encoder-reranking) — Cross-encoder reranking for when precision matters more than speed
- [**The Relevance Ward**](docs/GLOSSARY.md#the-relevance-ward) — Results below a [configured threshold](docs/ARCHITECTURE.md#tuned-parameters-reference) are filtered, so the library says "I don't know" instead of guessing

## Features

- **[Adaptive Search Routing](docs/ARCHITECTURE.md#the-three-roads)**: Three paths — `simple` (Vector), `hybrid` (BM25+Vector), and `precise` (Reranked)
- **Statistical Rigor**: Validated against **The Centurion Set** (100+ multi-category queries)
- **Quality Gate**: Documents must have frontmatter and structure to enter the library
- **Embedding Protection**: Auto-detects model mismatch on remote databases
- **8 MCP Tools**: Search, ingest, critique, generate docs, and more
- **Token Auth**: Bearer token authentication for remote ChromaDB

## Quick Start

```bash
# Enter the library
pip install -e .
./scripts/setup.sh       # Download the tomes (embedding models)
./scripts/configure.sh   # Set your wards (configuration)
./scripts/start_chroma.sh # Awaken the vault (ChromaDB)
candlekeep               # Open the gates
```

### MCP Client Integration

Add to your MCP client configuration (e.g., Claude Desktop `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "candlekeep": {
      "command": "/path/to/.venv/bin/candlekeep",
      "args": [],
      "env": {
        "CANDLEKEEP_SPICE": "true"
      }
    }
  }
}
```

Set `CANDLEKEEP_SPICE` to `"true"` for the wizard sage persona, or omit for professional mode.

## The Tomes (Documentation)

- [Setup Guide](docs/SETUP.md) — Local and remote installation
- [Authentication](docs/AUTHENTICATION.md) — Token configuration
- [Architecture](docs/ARCHITECTURE.md) — System design
- [Benchmark Results](docs/BENCHMARK_RESULTS.md) — Quality and performance metrics
- [Interactive Benchmark Chart](docs/benchmark_chart.html) — Visual comparison of paths
- [Design Decisions](docs/DESIGN.md) — Why things are the way they are
- [Glossary of Retrieval](docs/GLOSSARY.md) — IR metrics explained in wizard sage style
- [Research Diary](docs/RESEARCH_DIARY.md) — The full journey, every experiment
- [The Keeper's Chronicle](docs/THE_KEEPER_OF_CANDLEKEEP.md) — The story of how the library was built

## MCP Tools

- **search** — Semantic search with adaptive routing (`simple` 22–36ms, `precise` ~1550ms)
- **list_documents** — List all indexed tomes
- **get_stats** — Library statistics
- **critique_document** — Check document quality before ingestion
- **generate_documentation** — Scan a project and create structured docs
- **ingest** — Add documents with automatic quality validation
- **delete_document** — Remove a tome from the index
- **repopulate_database** — Clear and rebuild the library

Access to write tools is managed by your database permissions (configured via `CHROMA_AUTH_TOKEN`).

## Testing

```bash
# Unit tests — no database required (~1.4s)
pytest tests/test_router.py tests/test_quality_gate.py tests/test_arcane_recall_unit.py \
       tests/test_protection.py tests/test_processor.py tests/test_search.py

# Benchmarks — requires local ChromaDB on localhost:8000
./scripts/start_chroma.sh
pytest tests/test_router_benchmark.py -v -s
```

37 unit tests covering router, quality gate, chunk expansion, embedding protection, and document processing. Benchmark tests include regression assertions that fail if precision or content match drops below 80%.

## Requirements

- Python 3.10+
- ChromaDB server (local or remote)

---

<sub>Candlekeep is a trademark of Wizards of the Coast. This project is unofficial fan content and is not endorsed by or affiliated with Wizards of the Coast.</sub>
