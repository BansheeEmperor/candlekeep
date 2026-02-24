"""Candlekeep MCP Server with authentication and conditional tool registration."""
import sys
import time
import threading
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.dependencies import CurrentContext
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

# Timeout for write lock acquisition in HTTP mode. If another write is
# in progress (e.g. a long repopulate_database), fail fast instead of
# queuing indefinitely. stdio mode uses blocking acquire (single agent).
_WRITE_LOCK_TIMEOUT = 10.0  # seconds


class _WriteLockTimeout(Exception):
    """Raised when the write lock cannot be acquired within the timeout."""
    pass


class _write_guard:
    """Context manager that acquires _write_lock with a timeout in HTTP mode."""

    def __enter__(self):
        if _settings.transport == "http":
            acquired = _write_lock.acquire(timeout=_WRITE_LOCK_TIMEOUT)
            if not acquired:
                raise _WriteLockTimeout(
                    "⚠ Server busy — another write operation (ingest, delete, "
                    "or repopulate) is currently running and holds the write lock. "
                    f"Could not acquire it within {_WRITE_LOCK_TIMEOUT:.0f}s. "
                    "Retry after a short delay, or check if a repopulate_database "
                    "call is in progress (these can take minutes on large corpora)."
                )
        else:
            _write_lock.acquire()
        return self

    def __exit__(self, *exc):
        _write_lock.release()
        return False

def _estimate_semaphore_value() -> int:
    """Estimate optimal precise-path concurrency from CPU core count.

    The cross-encoder is CPU-bound and GIL-contended. Benchmarks on a
    10-core Apple M2 Pro show throughput peaks at N=3 (~cores/3). This
    heuristic generalizes that ratio.

    Used immediately for stdio mode (no boot cost). HTTP mode refines
    this via _calibrate_semaphore() during background init.
    """
    import os
    cores = os.cpu_count() or 4
    return max(1, cores // 3)

_reranker_semaphore = threading.Semaphore(_estimate_semaphore_value())


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


# --- Per-session rate limiting (HTTP mode only) ---

class _RateLimiter:
    """Per-session sliding window rate limiter.

    Tracks call timestamps per MCP session ID. A call is allowed if the
    number of calls within the sliding window is below the configured max.
    Setting max_calls=0 disables the limiter (all calls allowed).
    """

    def __init__(self, max_calls: int, window_seconds: float):
        self._max = max_calls
        self._window = window_seconds
        self._sessions: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._max > 0

    def check(self, session_id: str) -> bool:
        """Return True if the call is allowed, False if rate-limited."""
        if not self.enabled:
            return True
        now = time.monotonic()
        with self._lock:
            timestamps = self._sessions.get(session_id, [])
            timestamps = [t for t in timestamps if now - t < self._window]
            if len(timestamps) >= self._max:
                self._sessions[session_id] = timestamps
                return False
            timestamps.append(now)
            self._sessions[session_id] = timestamps
            return True

    def cleanup(self, max_idle_seconds: float = 600.0):
        """Remove sessions with no activity in the last max_idle_seconds."""
        now = time.monotonic()
        with self._lock:
            stale = [s for s, ts in self._sessions.items()
                     if not ts or now - ts[-1] > max_idle_seconds]
            for s in stale:
                del self._sessions[s]


_search_limiter = _RateLimiter(_settings.rate_limit_search, _settings.rate_limit_window)
_write_limiter = _RateLimiter(_settings.rate_limit_write, _settings.rate_limit_window)


def _rate_check(limiter: _RateLimiter, ctx: Context) -> str | None:
    """Check rate limit for the current session. Returns error message or None."""
    if _settings.transport != "http":
        return None
    if not limiter.enabled:
        return None
    try:
        session_id = ctx.session_id
    except Exception:
        # session_id unavailable (e.g. during init) — allow the call
        return None
    if not limiter.check(session_id):
        return "⚠ Rate limit exceeded. Try again shortly."
    return None


def _rate_limit_cleanup_loop():
    """Periodically evict stale session entries from rate limiters."""
    while True:
        time.sleep(300)
        _search_limiter.cleanup()
        _write_limiter.cleanup()


if _settings.transport == "http":
    threading.Thread(target=_rate_limit_cleanup_loop, daemon=True).start()


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


def _calibrate_semaphore():
    """Calibrate the precise-path semaphore by measuring cross-encoder throughput.

    Tests concurrency levels from 1 up to cores//2 (scaled to hardware),
    picks the N with the highest throughput. Stops early when throughput
    drops. Runs during HTTP-mode background init after models are warm.
    """
    import os
    import time
    import concurrent.futures
    global _reranker_semaphore

    from candlekeep.rag.reranker import rerank_results
    from candlekeep.database.interface import SearchResult

    dummy_results = [
        SearchResult(text=f"Test document number {i} about technical topics.",
                     metadata={}, score=0.8, doc_id=f"doc{i}")
        for i in range(10)
    ]
    device = _settings.device

    def _run_one():
        rerank_results("test query about systems", dummy_results, top_k=5, device=device)

    # Warm the code path
    _run_one()

    cores = os.cpu_count() or 4
    max_n = max(2, cores // 2)  # e.g. 4 cores → test up to 2, 10 cores → up to 5, 64 cores → up to 32
    candidates = [n for n in range(1, max_n + 1)]

    best_n = _estimate_semaphore_value()
    best_throughput = 0.0

    for n in candidates:
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
            futures = [pool.submit(_run_one) for _ in range(n)]
            concurrent.futures.wait(futures)
        elapsed = time.perf_counter() - start
        throughput = n / elapsed

        if throughput > best_throughput:
            best_throughput = throughput
            best_n = n

        # If throughput dropped, further concurrency won't help
        if n > 1 and throughput < best_throughput * 0.8:
            break

    _reranker_semaphore = threading.Semaphore(best_n)
    print(f"[candlekeep] ✓ Precise-path concurrency: {best_n} "
          f"({best_throughput:.1f} qps)", file=sys.stderr)


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

    # Calibrate precise-path concurrency (HTTP mode only — stdio is uncontended)
    if _settings.transport == "http":
        try:
            _calibrate_semaphore()
        except Exception as e:
            print(f"[candlekeep] ⚠ Semaphore calibration failed, using default: {e}",
                  file=sys.stderr)

        # Log rate limit configuration
        if _search_limiter.enabled or _write_limiter.enabled:
            print(f"[candlekeep] ✓ Rate limits: "
                  f"{_settings.rate_limit_search} search/{_settings.rate_limit_window}s, "
                  f"{_settings.rate_limit_write} write/{_settings.rate_limit_window}s "
                  f"(per session)", file=sys.stderr)
        else:
            print("[candlekeep] ⚠ Rate limiting disabled", file=sys.stderr)
    
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

        # Warn if token auth is active on a non-localhost bind address
        bind = _settings.http_host
        if bind not in ("127.0.0.1", "localhost", "::1"):
            print(
                f"[candlekeep] ⚠ Token auth is active but HTTP host is {bind}. "
                "Token will be transmitted in plaintext. Use a TLS-terminating "
                "reverse proxy for non-localhost deployments.",
                file=sys.stderr,
            )

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
    query_type: str = "hybrid",
    ctx: Context = CurrentContext(),
) -> str:
    """Search knowledge base for relevant documents.

    Automatically handles negation queries (e.g., "without", "not", "except").

    Args:
        query: Search query text
        n_results: Number of results to return (default: 5)
        category: Optional category filter
        query_type: Controls search strategy. One of:
            - "simple": Fast semantic lookup (~57ms). Best for conceptual
              questions like "how does caching work?" or "explain auth flow".
            - "hybrid": Lexical + semantic fusion (~82ms). USE THIS when
              your query contains terms that must match literally rather
              than semantically — exact names, version strings, error codes,
              CLI flags, config keys, package names, or any specific
              technical identifier (e.g. "ECONNREFUSED", "--max-retries",
              "bge-small-en-v1.5").
            - "precise": Semantic reranking (~920ms). Best for comparative
              or analytical questions where ranking quality matters more
              than speed — e.g. "compare OAuth2 and SAML for mobile apps".

        For complex multi-part questions, make multiple simple searches
        (one per sub-question) and synthesize the results yourself.
    """
    if msg := _check_ready():
        return msg
    if msg := _rate_check(_search_limiter, ctx):
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
    """Analyze a project directory and return a structured documentation plan.

    Validates the path exists and returns a two-phase prompt: survey first,
    then deep-dive documentation. The agent does all file exploration itself.
    Write the docs as markdown with YAML frontmatter, then use ingest() to add them.
    """
    if msg := _check_ready():
        return msg

    p = Path(directory_path)
    if not p.exists():
        return f"Error: Path not found: {directory_path}"
    if not p.is_dir():
        return f"Error: Not a directory: {directory_path}"

    return f"""**PROJECT DOCUMENTATION REQUEST**

Target directory: **{directory_path}**

Work in two phases: survey the project first, then write documentation.

---

## PHASE 1 — SURVEY

Build a mental model of the project before writing anything.

1. **Explore the directory tree.** Get the top-level structure and identify
   key directories (src, lib, docs, tests, config, scripts, etc.).

2. **Read high-signal files first.** Look for (case-insensitive):
   - README files (any extension: .md, .rst, .txt, or none)
   - Project manifests (pyproject.toml, package.json, Cargo.toml, go.mod, pom.xml)
   - Existing documentation directories (docs/, doc/, wiki/)
   - Architecture or design documents (ARCHITECTURE, DESIGN, ADR, RFC)
   - Entry points (main.py, index.ts, cmd/, __main__.py, App.java)
   - Configuration files (Dockerfile, Makefile, CI configs)

3. **Identify the key sections of the codebase:**
   - What is the public API or interface surface?
   - What are the core modules/packages and how do they relate?
   - What external dependencies does it rely on?
   - What configuration or environment does it need?
   - Are there patterns (MVC, plugin architecture, event-driven, etc.)?

4. **Summarize your findings** before moving to Phase 2. List:
   - Project type and primary language(s)
   - Core components and their responsibilities
   - Data flow or request lifecycle
   - Anything unclear that needs deeper reading

---

## PHASE 2 — DEEP DIVE & DOCUMENTATION

Now read deeper into the key sections you identified and write documentation.

**For each document you create:**

1. Deep-dive into the relevant source files — read implementations, not just
   signatures. Understand the why, not just the what.
2. Write the document as markdown with YAML frontmatter.
3. Use `critique_document(path)` to verify it passes the quality gate.
4. Use `ingest(path)` to add it to the knowledge base.

**Suggested documents** (adapt based on what you found in Phase 1):
- Project Overview — what it does, who it's for, key concepts
- Architecture — components, data flow, design decisions
- Setup & Installation — prerequisites, steps, configuration
- Usage Guide — workflows, examples, CLI commands
- API Reference — public interfaces, parameters, return types

---

## QUALITY GATE

ingest() will reject documents that fail these checks:

- **YAML frontmatter required** — must start with `---` and include:
  title, description, keywords, category, tags
- **At least 2 markdown headers** (## or ###)
- **Between 100 and 10,000 words**
- **No unclosed code blocks** (matched ``` pairs)

Frontmatter template:
```yaml
---
title: "Component Name"
description: "One-line summary of what this covers"
keywords:
  - term1
  - term2
  - term3
category: "overview | architecture | setup | api | guide"
tags:
  - relevant-tag
---
```

## RAG OPTIMIZATION TIPS

The system splits documents at markdown headers (## or ###). If a section
exceeds {_settings.chunk_size} characters it gets sub-chunked with
{_settings.chunk_overlap}-char overlap. The title and description from
frontmatter are prepended to every chunk for context. Write with that in mind:

- Use descriptive headers — "## Authentication Flow" not "## Overview"
- Keep sections under ~{_settings.chunk_size} chars when possible so each
  header-delimited section stays as one chunk
- Make sections self-contained; a chunk should make sense without the
  surrounding document
- Front-load key terms and concepts in each section — embeddings weight
  early tokens more heavily
- Include concrete examples, code snippets, and parameter names
- Avoid vague sections that just reference other sections
- The frontmatter title and description appear in every chunk, so make
  them keyword-rich and specific"""


# ============================================================
# WRITE TOOLS (serialized with _write_guard — timeout in HTTP mode)
# ============================================================

@mcp.tool
def ingest(path: str, ctx: Context = CurrentContext()) -> str:
    """Ingest a file or directory into the knowledge base.

    Validates document quality before ingestion. Documents must have:
    - YAML frontmatter (title, description, keywords)
    - At least 2 markdown headers
    - Between 100 and 10,000 words

    Supports: txt, md, pdf, rst, json, yaml files.
    """
    if msg := _check_ready():
        return msg
    if msg := _rate_check(_write_limiter, ctx):
        return msg

    try:
        with _write_guard():
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
    except _WriteLockTimeout as e:
        return str(e)
    except chromadb.errors.AuthorizationError as e:
        return f"❌ Write permission denied: {e}"
    except Exception as e:
        return f"❌ Error: {e}"

@mcp.tool
def delete_document(source: str, ctx: Context = CurrentContext()) -> str:
    """Delete all chunks from a source file."""
    if msg := _check_ready():
        return msg
    if msg := _rate_check(_write_limiter, ctx):
        return msg

    try:
        with _write_guard():
            count = get_store().delete_by_source(source)
            if count:
                return f"✓ Deleted {count} chunks from {source}"
            return f"No chunks found for {source}"
    except _WriteLockTimeout as e:
        return str(e)
    except chromadb.errors.AuthorizationError as e:
        return f"❌ Write permission denied: {e}"
    except Exception as e:
        return f"❌ Error: {e}"

@mcp.tool
def repopulate_database(ctx: Context = CurrentContext()) -> str:
    """Clear and rebuild the entire database.

    WARNING: This deletes all existing data.
    """
    if msg := _check_ready():
        return msg
    if msg := _rate_check(_write_limiter, ctx):
        return msg

    try:
        with _write_guard():
            get_store().clear()
            return "✓ Database cleared. Use ingest() to add documents."
    except _WriteLockTimeout as e:
        return str(e)
    except chromadb.errors.AuthorizationError as e:
        return f"❌ Write permission denied: {e}"
    except Exception as e:
        return f"❌ Error: {e}"


# ASGI entrypoint for production deployments (uvicorn candlekeep.mcp.server:app)
# stateless_http=True enables multi-worker deployment (uvicorn --workers N)
# by removing per-session state. Each request is independent.
app = mcp.http_app(stateless_http=True)


def main():
    """Entry point for candlekeep command."""
    if _settings.transport == "http":
        print(f"[candlekeep] 🌐 Starting HTTP server on {_settings.http_host}:{_settings.http_port}", file=sys.stderr)
        mcp.run(transport="http", host=_settings.http_host, port=_settings.http_port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
