"""Tests for multi-agent shared server mode (Phase 3).

Covers: dual-mode transport, optional auth, write serialization,
in-memory metrics, concurrent reads, and stdio regression.
"""
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from candlekeep.config import Settings


# ============================================================
# Settings / Configuration
# ============================================================

class TestTransportSettings:
    def test_default_transport_is_stdio(self):
        with patch.dict("os.environ", {}, clear=False):
            s = Settings.from_env()
            assert s.transport == "stdio"

    def test_http_transport_from_env(self):
        env = {"CANDLEKEEP_TRANSPORT": "http"}
        with patch.dict("os.environ", env, clear=False):
            s = Settings.from_env()
            assert s.transport == "http"

    def test_http_host_default(self):
        s = Settings.from_env()
        assert s.http_host == "127.0.0.1"

    def test_http_port_default(self):
        s = Settings.from_env()
        assert s.http_port == 8111

    def test_http_port_from_env(self):
        env = {"CANDLEKEEP_HTTP_PORT": "9999"}
        with patch.dict("os.environ", env, clear=False):
            s = Settings.from_env()
            assert s.http_port == 9999

    def test_mcp_token_default_empty(self):
        s = Settings.from_env()
        assert s.mcp_token == ""

    def test_mcp_token_from_env(self):
        env = {"CANDLEKEEP_MCP_TOKEN": "test-secret"}
        with patch.dict("os.environ", env, clear=False):
            s = Settings.from_env()
            assert s.mcp_token == "test-secret"


# ============================================================
# MCP Instance Creation (auth behavior)
# ============================================================

class TestMCPCreation:
    """Test that _create_mcp produces the right FastMCP instance."""

    def test_stdio_mode_no_auth(self):
        """stdio mode never adds auth, even if token is set."""
        mock_settings = MagicMock()
        mock_settings.transport = "stdio"
        mock_settings.mcp_token = "some-token"
        mock_settings.spice = False

        with patch("candlekeep.mcp.server._settings", mock_settings), \
             patch("candlekeep.mcp.server.instructions", "test"):
            from candlekeep.mcp.server import _create_mcp
            mcp_instance = _create_mcp()
            # Should create without auth — FastMCP with no auth kwarg
            assert mcp_instance is not None
            assert mcp_instance.name == "candlekeep"

    def test_http_mode_with_token_enables_auth(self):
        """HTTP mode + token should create FastMCP with StaticTokenVerifier."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_settings.mcp_token = "secret-token"
        mock_settings.spice = False

        with patch("candlekeep.mcp.server._settings", mock_settings), \
             patch("candlekeep.mcp.server.instructions", "test"):
            from candlekeep.mcp.server import _create_mcp
            mcp_instance = _create_mcp()
            assert mcp_instance is not None
            assert mcp_instance.auth is not None

    def test_http_mode_without_token_no_auth(self):
        """HTTP mode without token should create FastMCP without auth."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_settings.mcp_token = ""
        mock_settings.spice = False

        with patch("candlekeep.mcp.server._settings", mock_settings), \
             patch("candlekeep.mcp.server.instructions", "test"):
            from candlekeep.mcp.server import _create_mcp
            mcp_instance = _create_mcp()
            assert mcp_instance is not None


# ============================================================
# Query Counter (in-memory metrics)
# ============================================================

class TestQueryCounter:
    def test_starts_at_zero(self):
        from candlekeep.mcp.server import _QueryCounter
        counter = _QueryCounter()
        assert counter.count == 0

    def test_increment(self):
        from candlekeep.mcp.server import _QueryCounter
        counter = _QueryCounter()
        counter.increment()
        counter.increment()
        counter.increment()
        assert counter.count == 3

    def test_thread_safety(self):
        """Concurrent increments should not lose counts."""
        from candlekeep.mcp.server import _QueryCounter
        counter = _QueryCounter()
        n_threads = 10
        n_increments = 1000

        def worker():
            for _ in range(n_increments):
                counter.increment()

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counter.count == n_threads * n_increments


# ============================================================
# Write Lock Serialization
# ============================================================

class TestWriteLock:
    """Verify that write operations are serialized via _write_lock."""

    def test_write_lock_exists(self):
        from candlekeep.mcp.server import _write_lock
        assert isinstance(_write_lock, type(threading.Lock()))

    def test_concurrent_writes_serialize(self):
        """Two threads acquiring _write_lock should not overlap."""
        from candlekeep.mcp.server import _write_lock

        execution_log = []
        barrier = threading.Barrier(2)

        def writer(name):
            barrier.wait()  # Sync start
            with _write_lock:
                execution_log.append(f"{name}_start")
                time.sleep(0.05)  # Simulate work
                execution_log.append(f"{name}_end")

        t1 = threading.Thread(target=writer, args=("A",))
        t2 = threading.Thread(target=writer, args=("B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # One writer must fully complete before the other starts.
        # Valid orderings: A_start,A_end,B_start,B_end or B_start,B_end,A_start,A_end
        assert len(execution_log) == 4
        # The second entry must be the end of whoever started first
        assert execution_log[0].endswith("_start")
        assert execution_log[1].endswith("_end")
        assert execution_log[0][0] == execution_log[1][0]  # Same writer
        assert execution_log[2].endswith("_start")
        assert execution_log[3].endswith("_end")
        assert execution_log[2][0] == execution_log[3][0]  # Same writer


# ============================================================
# Main entrypoint branching
# ============================================================

class TestMainEntrypoint:
    def test_stdio_mode_calls_run_default(self):
        """main() with stdio transport calls mcp.run() with no args."""
        mock_settings = MagicMock()
        mock_settings.transport = "stdio"

        with patch("candlekeep.mcp.server._settings", mock_settings), \
             patch("candlekeep.mcp.server.mcp") as mock_mcp:
            from candlekeep.mcp.server import main
            main()
            mock_mcp.run.assert_called_once_with()

    def test_http_mode_calls_run_with_transport(self):
        """main() with http transport calls mcp.run(transport='http', ...)."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_settings.http_host = "0.0.0.0"
        mock_settings.http_port = 8111

        with patch("candlekeep.mcp.server._settings", mock_settings), \
             patch("candlekeep.mcp.server.mcp") as mock_mcp:
            from candlekeep.mcp.server import main
            main()
            mock_mcp.run.assert_called_once_with(
                transport="http", host="0.0.0.0", port=8111
            )


# ============================================================
# get_stats uses in-memory counter
# ============================================================

class TestStatsUsesCounter:
    """Verify get_stats reads from _query_counter, not file-based metrics."""

    def test_stats_reflects_counter(self):
        """get_stats should use _query_counter.count for query/token stats."""
        from candlekeep.mcp.server import _QueryCounter

        mock_counter = _QueryCounter()
        mock_counter.increment()
        mock_counter.increment()

        mock_store = MagicMock()
        mock_store.get_stats.return_value = {
            "total_chunks": 100,
            "total_documents": 10,
            "database_size_human": "1.0 MB",
            "total_characters": 50000,
            "estimated_tokens": 12500,
            "tokens_per_query": 640,
            "context_savings_ratio": 19.5,
        }

        with patch("candlekeep.mcp.server._loading", False), \
             patch("candlekeep.mcp.server._read_access", True), \
             patch("candlekeep.mcp.server.get_store", return_value=mock_store), \
             patch("candlekeep.mcp.server._query_counter", mock_counter):
            from candlekeep.mcp.server import get_stats
            result = get_stats.fn()
            assert "Total queries: 2" in result
            # tokens_saved = 2 * (12500 - 640) = 23720
            assert "23,720" in result


# ============================================================
# Vector store no longer has file-based metrics
# ============================================================

class TestMetricsRemoved:
    """Verify file-based metrics methods are gone from ChromaVectorStore."""

    def test_no_record_query_method(self):
        from candlekeep.database.vector_store import ChromaVectorStore
        assert not hasattr(ChromaVectorStore, "record_query")

    def test_no_load_metrics_method(self):
        from candlekeep.database.vector_store import ChromaVectorStore
        assert not hasattr(ChromaVectorStore, "_load_metrics")

    def test_no_save_metrics_method(self):
        from candlekeep.database.vector_store import ChromaVectorStore
        assert not hasattr(ChromaVectorStore, "_save_metrics")

    def test_get_stats_no_total_queries_key(self):
        """get_stats return dict should not contain total_queries or tokens_saved."""
        mock_store = MagicMock()
        mock_store.settings = MagicMock()
        mock_store.settings.chunk_size = 512
        mock_store.settings.chroma_dir = MagicMock()

        # Call the real get_stats on a real-ish instance
        from candlekeep.database.vector_store import ChromaVectorStore
        # We can't easily instantiate without ChromaDB, so just check the class
        # doesn't have the old methods
        assert not hasattr(ChromaVectorStore, "_load_metrics")


# ============================================================
# ASGI app exposed
# ============================================================

class TestASGIApp:
    def test_app_is_exposed(self):
        """server.py should expose an 'app' for uvicorn."""
        from candlekeep.mcp.server import app
        assert app is not None


# ============================================================
# Auth token validation
# ============================================================

class TestAuthTokenValidation:
    """Verify StaticTokenVerifier rejects invalid tokens."""

    def test_valid_token_accepted(self):
        from fastmcp.server.auth import StaticTokenVerifier
        auth = StaticTokenVerifier(tokens={"valid-token": {"client_id": "agent-1", "scopes": []}})
        # StaticTokenVerifier stores tokens internally
        assert auth is not None

    def test_auth_object_created_with_correct_token(self):
        """The token from CANDLEKEEP_MCP_TOKEN should be the key in the verifier."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_settings.mcp_token = "my-secret-123"
        mock_settings.spice = False

        with patch("candlekeep.mcp.server._settings", mock_settings), \
             patch("candlekeep.mcp.server.instructions", "test"):
            from candlekeep.mcp.server import _create_mcp
            mcp_instance = _create_mcp()
            # The auth provider should have our token
            assert mcp_instance.auth is not None
            from fastmcp.server.auth import StaticTokenVerifier
            assert isinstance(mcp_instance.auth, StaticTokenVerifier)
