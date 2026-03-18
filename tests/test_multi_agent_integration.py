"""Integration tests for multi-agent HTTP mode.

These tests manage their own server processes — no manual server startup needed.
Two server fixtures:
  - _noauth_server: HTTP mode, no token (port 18111)
  - _auth_server: HTTP mode, with token (port 18112)

Both auto-skip if ChromaDB is not running on localhost:8000.
"""
import pytest
import asyncio
import os
import signal
import subprocess
import sys
import tempfile

pytestmark = [pytest.mark.integration]
import time
from pathlib import Path

import pytest

from fastmcp import Client


# ============================================================
# Helpers
# ============================================================

def _run_async(coro):
    return asyncio.run(coro)


async def _wait_for_server(url: str, timeout: float = 120.0) -> bool:
    """Poll until the server responds with real data (not loading message)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            async with Client(url) as c:
                r = await c.call_tool("list_documents", {})
                text = r.content[0].text if r.content else ""
                if "Loading models" not in text and "try again" not in text:
                    return True
        except Exception:
            pass
        await asyncio.sleep(1.0)
    return False


def _start_server(port: int, token: str = "") -> subprocess.Popen:
    """Start a Candlekeep HTTP server as a subprocess."""
    env = os.environ.copy()
    env["CANDLEKEEP_TRANSPORT"] = "http"
    env["CANDLEKEEP_HTTP_PORT"] = str(port)
    env["CANDLEKEEP_HTTP_HOST"] = "127.0.0.1"
    if token:
        env["CANDLEKEEP_MCP_TOKEN"] = token

    proc = subprocess.Popen(
        [sys.executable, "-m", "candlekeep"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def _stop_server(proc: subprocess.Popen):
    """Stop a server subprocess."""
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ============================================================
# Check ChromaDB is available
# ============================================================

def _chroma_available() -> bool:
    try:
        import chromadb
        client = chromadb.HttpClient(host="localhost", port=8000)
        client.heartbeat()
        return True
    except Exception:
        return False


CHROMA_UP = _chroma_available()

pytestmark = pytest.mark.skipif(
    not CHROMA_UP,
    reason="ChromaDB not running on localhost:8000",
)


# ============================================================
# Server fixtures
# ============================================================

NOAUTH_PORT = 48111
AUTH_PORT = 48112
AUTH_TOKEN = "test-secret-token-for-integration"

NOAUTH_URL = f"http://127.0.0.1:{NOAUTH_PORT}/mcp"
AUTH_URL = f"http://127.0.0.1:{AUTH_PORT}/mcp"


def _kill_port(port: int):
    """Kill any process listening on the given port."""
    try:
        import subprocess as sp
        result = sp.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGKILL)
                time.sleep(0.2)
    except Exception:
        pass


@pytest.fixture(scope="class")
def noauth_server():
    """Start a no-auth HTTP server, tear down after the test class."""
    _kill_port(NOAUTH_PORT)
    proc = _start_server(NOAUTH_PORT)
    ready = _run_async(_wait_for_server(NOAUTH_URL))
    if not ready:
        _stop_server(proc)
        pytest.skip("No-auth server failed to start")
    yield NOAUTH_URL
    _stop_server(proc)


@pytest.fixture(scope="class")
def auth_server():
    """Start an auth-enabled HTTP server, tear down after the test class."""
    _kill_port(AUTH_PORT)
    proc = _start_server(AUTH_PORT, token=AUTH_TOKEN)

    async def wait_auth():
        deadline = time.monotonic() + 120.0
        while time.monotonic() < deadline:
            try:
                async with Client(AUTH_URL, auth=AUTH_TOKEN) as c:
                    r = await c.call_tool("list_documents", {})
                    text = r.content[0].text if r.content else ""
                    if "Loading models" not in text and "try again" not in text:
                        return True
            except Exception:
                pass
            await asyncio.sleep(1.0)
        return False

    ready = _run_async(wait_auth())
    if not ready:
        _stop_server(proc)
        pytest.skip("Auth server failed to start")
    yield AUTH_URL
    _stop_server(proc)


# ============================================================
# Smoke test: read tools over HTTP (no auth)
# ============================================================

class TestSmokeHTTP:
    def test_search(self, noauth_server):
        async def go():
            async with Client(noauth_server) as c:
                r = await c.call_tool("search", {"query": "authentication", "n_results": 1})
                assert r.content
        _run_async(go())

    def test_list_documents(self, noauth_server):
        async def go():
            async with Client(noauth_server) as c:
                r = await c.call_tool("list_documents", {})
                assert r.content
        _run_async(go())

    def test_get_stats(self, noauth_server):
        async def go():
            async with Client(noauth_server) as c:
                r = await c.call_tool("get_stats", {})
                assert "Total chunks" in r.content[0].text
        _run_async(go())

    def test_critique_document(self, noauth_server):
        async def go():
            async with Client(noauth_server) as c:
                r = await c.call_tool("critique_document", {"path": "README.md"})
                assert r.content
        _run_async(go())

    def test_generate_documentation(self, noauth_server):
        async def go():
            async with Client(noauth_server) as c:
                r = await c.call_tool("generate_documentation", {"directory_path": "src/candlekeep"})
                assert "PROJECT DOCUMENTATION REQUEST" in r.content[0].text
        _run_async(go())


# ============================================================
# Auth: rejection and acceptance
# ============================================================

class TestAuth:
    def test_no_token_rejected(self, auth_server):
        """Connecting without a token to an auth-enabled server should fail."""
        async def go():
            try:
                async with Client(auth_server) as c:
                    await c.call_tool("list_documents", {})
                return "accepted"
            except Exception:
                return "rejected"
        result = _run_async(go())
        assert result == "rejected"

    def test_wrong_token_rejected(self, auth_server):
        """Connecting with a wrong token should fail."""
        async def go():
            try:
                async with Client(auth_server, auth="wrong-token") as c:
                    await c.call_tool("list_documents", {})
                return "accepted"
            except Exception:
                return "rejected"
        result = _run_async(go())
        assert result == "rejected"

    def test_correct_token_accepted(self, auth_server):
        """Connecting with the correct token should succeed."""
        async def go():
            async with Client(auth_server, auth=AUTH_TOKEN) as c:
                r = await c.call_tool("list_documents", {})
                return r.content
        result = _run_async(go())
        assert result


# ============================================================
# Concurrent reads (no auth)
# ============================================================

class TestConcurrentReads:
    def test_parallel_simple_searches(self, noauth_server):
        """5 parallel simple searches should all return results."""
        queries = [
            "authentication methods",
            "database design patterns",
            "caching strategies",
            "API design best practices",
            "vector search algorithms",
        ]

        async def search(query):
            async with Client(noauth_server) as c:
                r = await c.call_tool("search", {"query": query, "n_results": 2, "query_type": "hybrid"})
                return r.content[0].text

        async def go():
            results = await asyncio.gather(*[search(q) for q in queries])
            assert len(results) == 5
            for r in results:
                assert len(r) > 0

        _run_async(go())

    def test_parallel_mixed_paths(self, noauth_server):
        """Concurrent simple + hybrid + precise should not crash."""
        async def do_search(qtype):
            async with Client(noauth_server) as c:
                r = await c.call_tool("search", {
                    "query": "authentication",
                    "n_results": 2,
                    "query_type": qtype,
                })
                return r.content[0].text

        async def go():
            results = await asyncio.gather(*[do_search(qt) for qt in ["hybrid", "precise", "explore"]])
            assert len(results) == 3

        _run_async(go())


# ============================================================
# Write serialization (no auth)
# ============================================================

_TEST_DOC = """---
title: "Integration Test Doc"
description: "Testing write operations"
keywords: ["test", "integration"]
---

# Integration Test

## Section One

This document tests write operations in multi-agent mode. It has enough
words to pass the quality gate and proper frontmatter and headers. The
content is deliberately generic because we only care about whether the
write operations work correctly under concurrent access patterns.

## Section Two

More content here to ensure the document passes all quality checks.
This section provides additional padding to meet the minimum word count.
"""


class TestWriteSerialization:
    def test_concurrent_ingest_no_crash(self, noauth_server):
        """Two parallel ingests of the same file should not crash."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(_TEST_DOC)
            path = f.name

        async def ingest():
            async with Client(noauth_server) as c:
                r = await c.call_tool("ingest", {"path": path})
                return r.content[0].text

        async def go():
            results = await asyncio.gather(ingest(), ingest())
            for r in results:
                assert "Error" not in r or "Ingested" in r

        try:
            _run_async(go())
        finally:
            async def cleanup():
                async with Client(noauth_server) as c:
                    await c.call_tool("delete_document", {"source": path})
            _run_async(cleanup())
            Path(path).unlink(missing_ok=True)


# ============================================================
# Read during write (no auth)
# ============================================================

class TestReadDuringWrite:
    def test_search_during_ingest(self, noauth_server):
        """Search should return results while an ingest is in progress."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(_TEST_DOC)
            path = f.name

        async def go():
            async def do_ingest():
                async with Client(noauth_server) as c:
                    return await c.call_tool("ingest", {"path": path})

            async def do_search():
                async with Client(noauth_server) as c:
                    return await c.call_tool("search", {
                        "query": "authentication",
                        "n_results": 1,
                        "query_type": "hybrid",
                    })

            _, search_result = await asyncio.gather(do_ingest(), do_search())
            assert search_result.content

        try:
            _run_async(go())
        finally:
            async def cleanup():
                async with Client(noauth_server) as c:
                    await c.call_tool("delete_document", {"source": path})
            _run_async(cleanup())
            Path(path).unlink(missing_ok=True)
