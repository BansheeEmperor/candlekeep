"""Candlekeep MCP Server with authentication and conditional tool registration."""
import sys
import threading
from pathlib import Path
from fastmcp import FastMCP
import chromadb.errors

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor

# Global state
_settings = Settings.from_env()
_store = None
_processor = None
_loading = True
_read_access = False
_write_access = False

# Concurrency controls (safe in both stdio and HTTP modes)
_write_lock = threading.Lock()
_reranker_semaphore = threading.Semaphore(3)  # Cap concurrent precise-path queries (see benchmark results)


class _QueryCounter:
    """Thread-safe in-memory query counter. Replaces file-based metrics."""
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._count += 1

    @property
    def count(self):
        return self._count


_query_counter = _QueryCounter()


def get_store():
    global _store
    if _store is None:
        _store = ChromaVectorStore(_settings)
    return _store


def get_processor():
    global _processor
    if _processor is None:
        _processor = DocumentProcessor(_settings)
    return _processor


def _verify_read_access() -> bool:
    try:
        get_store().collection.count()
        return True
    except chromadb.errors.AuthorizationError as e:
        print(f"[candlekeep] ❌ Read access denied: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[candlekeep] ❌ Connection failed: {e}", file=sys.stderr)
        return False


def _verify_write_access() -> bool:
    try:
        store = get_store()
        test_id = "__auth_test__"
        store.collection.add(ids=[test_id], documents=["test"], metadatas=[{"source": "__test__"}])
        store.collection.delete(ids=[test_id])
        return True
    except Exception:
        return False


def _background_init():
    global _loading, _read_access, _write_access
    _read_access = _verify_read_access()
    if not _read_access:
        print("[candlekeep] ❌ Authentication failed. Check CHROMA_URL and CHROMA_AUTH_TOKEN", file=sys.stderr)
        _loading = False
        return
    print(f"[candlekeep] ✓ Connected to {_settings.chroma_url}", file=sys.stderr)
    print(f"[candlekeep] ✓ Device: {_settings.device}", file=sys.stderr)
    _write_access = _verify_write_access()
    if _write_access:
        print("[candlekeep] ✓ Write access enabled", file=sys.stderr)
    else:
        print("[candlekeep] ⚠ Read-only mode (write access denied)", file=sys.stderr)
    
    # Warm up models
    print("[candlekeep] 🕯 Warming up the tomes...", file=sys.stderr)
    get_store().embedder.get_model()
    from candlekeep.rag.reranker import warm_up
    warm_up(_settings.device)
    
    get_store()
    _loading = False


threading.Thread(target=_background_init, daemon=True).start()

# --- Quality gate for ingestion ---

def check_document_quality(path: Path) -> list[str]:
    """Check document quality for RAG suitability. Returns list of issues (empty = OK)."""
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    words = len(content.split())
    issues = []

    if not content.startswith("---"):
        issues.append("Missing YAML frontmatter (title, description, keywords, category, tags)")
    if sum(1 for l in lines if l.startswith("#")) < 2:
        issues.append("Insufficient structure (fewer than 2 markdown headers)")
    if words < 100:
        issues.append("Too short (< 100 words) — consider combining with related content")
    if words > 10000:
        issues.append("Too long (> 10k words) — consider splitting into focused documents")
    if content.count("```") % 2 != 0:
        issues.append("Unclosed code block (mismatched ``` markers)")

    return issues


# --- MCP server setup ---

if _settings.spice:
    instructions = """Greetings, seeker of knowledge. I am the Keeper of Candlekeep, guardian of ancient wisdom and arcane lore.

Speak thy query, and I shall divine the wisdom thou seekest from the vast repositories under my stewardship. The library's power is at thy command, though remember — with great knowledge comes great responsibility. Use these tools wisely, young scholar."""
else:
    instructions = """RAG knowledge base server for semantic search and document management.

Use this server for searching technical documentation and managing document collections."""


def _create_mcp() -> FastMCP:
    """Create the FastMCP instance with optional auth for HTTP mode."""
    if _settings.transport == "http" and _settings.mcp_token:
        from fastmcp.server.auth import StaticTokenVerifier
        auth = StaticTokenVerifier(
            tokens={_settings.mcp_token: {"client_id": "candlekeep-agent", "scopes": []}}
        )
        print("[candlekeep] ✓ Bearer token auth enabled", file=sys.stderr)
        return FastMCP("candlekeep", instructions=instructions, auth=auth)
    
    if _settings.transport == "http":
        print("[candlekeep] ⚠ No auth configured (set CANDLEKEEP_MCP_TOKEN to enable)", file=sys.stderr)
    
    return FastMCP("candlekeep", instructions=instructions)


mcp = _create_mcp()


def _check_ready() -> str | None:
    if _loading:
        return "⏳ Loading models, try again in a few seconds..."
    if not _read_access:
        return "❌ Database connection failed. Check configuration."
    return None


# ============================================================
# READ-ONLY TOOLS (always registered)
# ============================================================

@mcp.tool
def search(
    query: str,
    n_results: int = 5,
    category: str | None = None,
    query_type: str = "simple",
) -> str:
    """Search knowledge base for relevant documents.

    Automatically handles negation queries (e.g., "without", "not", "except").

    Args:
        query: Search query text
        n_results: Number of results to return (default: 5)
        category: Optional category filter
        query_type: Controls search strategy. One of:
            - "simple": Fast lookup with expanded context (default)
            - "precise": High accuracy, expands + reranks (slower)
            - "hybrid": Lexical (BM25) + Vector (Semantic) fusion

        For complex multi-part questions, make multiple simple searches
        (one per sub-question) and synthesize the results yourself.
    """
    if msg := _check_ready():
        return msg

    from candlekeep.rag.router import search_with_routing
    if query_type == "precise":
        with _reranker_semaphore:
            results = search_with_routing(get_store(), query, n_results, category, query_type=query_type)
    else:
        results = search_with_routing(get_store(), query, n_results, category, query_type=query_type)
    _query_counter.increment()

    if not results:
        return "No results found."

    output = []
    for r in results:
        output.append(f"**Score: {r.score:.3f}** | Source: {r.metadata['filename']}")
        output.append(f"```\n{r.text[:500]}{'...' if len(r.text) > 500 else ''}\n```\n")
    return "\n".join(output)


@mcp.tool
def list_documents() -> str:
    """List all indexed documents with their source and chunk count."""
    if msg := _check_ready():
        return msg

    docs = get_store().list_documents()
    if not docs:
        return "No documents indexed."

    output = ["| Source | Collection | Chunks |", "|--------|------------|--------|"]
    for d in docs:
        output.append(f"| {d['source']} | {d['collection']} | {d['chunks']} |")
    return "\n".join(output)


@mcp.tool
def get_stats() -> str:
    """Get knowledge base statistics: document count, tokens, context savings."""
    if msg := _check_ready():
        return msg

    stats = get_store().get_stats()
    queries = _query_counter.count
    tokens_per_query = stats['tokens_per_query']
    tokens_saved = queries * (stats['estimated_tokens'] - tokens_per_query)

    return f"""**Knowledge Base Statistics**
- Total chunks: {stats['total_chunks']}
- Total documents: {stats['total_documents']}
- Database size: {stats['database_size_human']}
- Total characters: {stats['total_characters']:,}
- Estimated tokens: {stats['estimated_tokens']:,}

**Context Efficiency**
- Tokens per query: ~{tokens_per_query:,} (5 chunks)
- Savings ratio: {stats['context_savings_ratio']:.0f}x smaller per query

**Usage (this session)**
- Total queries: {queries}
- Tokens saved: ~{tokens_saved:,}"""


@mcp.tool
def critique_document(path: str) -> str:
    """Critique a document for RAG suitability before ingestion.

    Checks frontmatter, structure, length, and code blocks.
    Use this to pre-check documents before calling ingest().
    """
    if msg := _check_ready():
        return msg

    p = Path(path)
    if not p.exists():
        return f"Error: File not found: {path}"

    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    words = len(content.split())
    chars = len(content)
    headers = [l for l in lines if l.startswith("#")]
    code_blocks = content.count("```")

    issues = check_document_quality(p)

    output = [f"**DOCUMENT CRITIQUE: {p.name}**\n"]
    output.append(f"**Metrics:**")
    output.append(f"- Size: {chars:,} chars, {words:,} words, {len(lines):,} lines")
    output.append(f"- Structure: {len(headers)} headers, {code_blocks // 2} code blocks")
    output.append(f"- Frontmatter: {'✓ Present' if content.startswith('---') else '✗ Missing'}\n")

    if issues:
        output.append(f"**Issues ({len(issues)}):**")
        for issue in issues:
            output.append(f"- ⚠️  {issue}")
        output.append(f"\n**Status:** ⚠️  Fix issues before ingesting")
    else:
        output.append("**Status:** ✓ Ready for ingestion")

    return "\n".join(output)


@mcp.tool
def generate_documentation(directory_path: str) -> str:
    """Analyze a project directory and prompt you to create structured documentation.

    Scans the directory, samples key files, and returns a documentation request.
    Write the docs as markdown with YAML frontmatter, then use ingest() to add them.
    """
    if msg := _check_ready():
        return msg

    p = Path(directory_path)
    if not p.exists():
        return f"Error: Path not found: {directory_path}"

    files = list(p.rglob("*"))
    code_files = [f for f in files if f.is_file() and f.suffix in {
        ".py", ".js", ".ts", ".java", ".c", ".h", ".cpp", ".go", ".rs",
        ".sh", ".md", ".txt", ".yaml", ".yml", ".json", ".toml"
    }]

    samples = []
    for pf in ["README.md", "readme.md", "pyproject.toml", "package.json", "Cargo.toml"]:
        for f in code_files:
            if f.name == pf:
                content = f.read_text(encoding="utf-8", errors="replace")[:2000]
                samples.append(f"=== {f.name} ===\n{content}\n")
                break

    file_tree = "\n".join(str(f.relative_to(p)) for f in code_files[:100])

    return f"""**PROJECT DOCUMENTATION REQUEST**

Generate documentation for: **{directory_path}**

### Directory Structure (first 100 files)
```
{file_tree}
```

### Key Files
{chr(10).join(samples[:5])}

---

**YOUR TASK:**

1. Analyze the project structure and identify main components
2. Create documentation files with YAML frontmatter (title, description, keywords, category, tags)
3. Cover: overview, architecture, setup, usage, API reference
4. Save as markdown files, then use ingest() to add to knowledge base

Each document must have frontmatter and section headers for proper chunking."""


# ============================================================
# WRITE TOOLS (serialized with _write_lock)
# ============================================================

@mcp.tool
def ingest(path: str) -> str:
    """Ingest a file or directory into the knowledge base.

    Validates document quality before ingestion. Documents must have:
    - YAML frontmatter (title, description, keywords)
    - At least 2 markdown headers
    - Between 100 and 10,000 words

    Supports: txt, md, pdf, rst, json, yaml files.
    """
    if msg := _check_ready():
        return msg

    with _write_lock:
        try:
            p = Path(path)
            if not p.exists():
                return f"Error: Path not found: {path}"

            # Quality gate for individual files
            if p.is_file() and p.suffix in (".md", ".txt", ".rst"):
                issues = check_document_quality(p)
                if issues:
                    msg = f"❌ Document rejected — {len(issues)} quality issue(s):\n"
                    msg += "\n".join(f"  - {i}" for i in issues)
                    msg += "\n\nFix these issues or use critique_document() to review first."
                    return msg

            if p.is_file():
                chunks = get_processor().process(p)
            else:
                chunks = get_processor().process_directory(p)

            if not chunks:
                return "No content found to ingest."

            count = get_store().add_documents(chunks, collection="default")
            return f"✓ Ingested {count} chunks from {path}"
        except chromadb.errors.AuthorizationError as e:
            return f"❌ Write permission denied: {e}"
        except Exception as e:
            return f"❌ Error: {e}"

@mcp.tool
def delete_document(source: str) -> str:
    """Delete all chunks from a source file."""
    if msg := _check_ready():
        return msg

    with _write_lock:
        try:
            count = get_store().delete_by_source(source)
            if count:
                return f"✓ Deleted {count} chunks from {source}"
            return f"No chunks found for {source}"
        except chromadb.errors.AuthorizationError as e:
            return f"❌ Write permission denied: {e}"
        except Exception as e:
            return f"❌ Error: {e}"

@mcp.tool
def repopulate_database() -> str:
    """Clear and rebuild the entire database.

    WARNING: This deletes all existing data.
    """
    if msg := _check_ready():
        return msg

    with _write_lock:
        try:
            get_store().clear()
            return "✓ Database cleared. Use ingest() to add documents."
        except chromadb.errors.AuthorizationError as e:
            return f"❌ Write permission denied: {e}"
        except Exception as e:
            return f"❌ Error: {e}"


# ASGI entrypoint for production deployments (uvicorn candlekeep.mcp.server:app)
app = mcp.http_app()


def main():
    """Entry point for candlekeep command."""
    if _settings.transport == "http":
        print(f"[candlekeep] 🌐 Starting HTTP server on {_settings.http_host}:{_settings.http_port}", file=sys.stderr)
        mcp.run(transport="http", host=_settings.http_host, port=_settings.http_port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
