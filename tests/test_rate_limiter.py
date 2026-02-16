"""Tests for per-session rate limiting."""
import time
import threading
from unittest.mock import MagicMock

import pytest

# Import the class directly from server module internals
from candlekeep.mcp.server import _RateLimiter, _rate_check


class TestRateLimiter:
    """Unit tests for _RateLimiter sliding window logic."""

    def test_allows_calls_under_limit(self):
        limiter = _RateLimiter(max_calls=3, window_seconds=60)
        assert limiter.check("session-1") is True
        assert limiter.check("session-1") is True
        assert limiter.check("session-1") is True

    def test_rejects_at_limit(self):
        limiter = _RateLimiter(max_calls=2, window_seconds=60)
        assert limiter.check("session-1") is True
        assert limiter.check("session-1") is True
        assert limiter.check("session-1") is False

    def test_sessions_are_isolated(self):
        limiter = _RateLimiter(max_calls=1, window_seconds=60)
        assert limiter.check("session-a") is True
        assert limiter.check("session-a") is False
        # Different session is unaffected
        assert limiter.check("session-b") is True

    def test_window_expiry(self):
        limiter = _RateLimiter(max_calls=1, window_seconds=0.1)
        assert limiter.check("s1") is True
        assert limiter.check("s1") is False
        time.sleep(0.15)
        # Window expired, should allow again
        assert limiter.check("s1") is True

    def test_disabled_when_max_zero(self):
        limiter = _RateLimiter(max_calls=0, window_seconds=60)
        assert limiter.enabled is False
        # Should always allow
        for _ in range(100):
            assert limiter.check("s1") is True

    def test_enabled_when_max_positive(self):
        limiter = _RateLimiter(max_calls=5, window_seconds=60)
        assert limiter.enabled is True

    def test_cleanup_removes_stale_sessions(self):
        limiter = _RateLimiter(max_calls=10, window_seconds=60)
        limiter.check("active")
        limiter.check("stale")

        # Manually age the stale session
        now = time.monotonic()
        with limiter._lock:
            limiter._sessions["stale"] = [now - 700]  # 700s ago

        limiter.cleanup(max_idle_seconds=600)

        with limiter._lock:
            assert "active" in limiter._sessions
            assert "stale" not in limiter._sessions

    def test_cleanup_preserves_active_sessions(self):
        limiter = _RateLimiter(max_calls=10, window_seconds=60)
        limiter.check("s1")
        limiter.check("s2")
        limiter.cleanup(max_idle_seconds=600)
        with limiter._lock:
            assert "s1" in limiter._sessions
            assert "s2" in limiter._sessions

    def test_thread_safety(self):
        """Concurrent calls from multiple threads don't corrupt state."""
        limiter = _RateLimiter(max_calls=50, window_seconds=60)
        results = []

        def worker():
            result = limiter.check("shared-session")
            results.append(result)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed = sum(1 for r in results if r)
        denied = sum(1 for r in results if not r)
        assert allowed == 50
        assert denied == 50


class TestRateCheck:
    """Tests for the _rate_check helper that integrates with Context."""

    def _make_ctx(self, session_id="test-session"):
        ctx = MagicMock()
        ctx.session_id = session_id
        return ctx

    def test_skipped_in_stdio_mode(self):
        """Rate check returns None (allow) when transport is not http."""
        from candlekeep.mcp.server import _settings
        original = _settings.transport
        try:
            _settings.transport = "stdio"
            limiter = _RateLimiter(max_calls=1, window_seconds=60)
            ctx = self._make_ctx()
            # Even after exceeding limit, stdio mode allows
            assert _rate_check(limiter, ctx) is None
            assert _rate_check(limiter, ctx) is None
        finally:
            _settings.transport = original

    def test_enforced_in_http_mode(self):
        from candlekeep.mcp.server import _settings
        original = _settings.transport
        try:
            _settings.transport = "http"
            limiter = _RateLimiter(max_calls=1, window_seconds=60)
            ctx = self._make_ctx()
            assert _rate_check(limiter, ctx) is None  # first call allowed
            assert _rate_check(limiter, ctx) is not None  # second rejected
        finally:
            _settings.transport = original

    def test_graceful_on_missing_session_id(self):
        """If session_id raises, allow the call rather than crash."""
        from candlekeep.mcp.server import _settings
        original = _settings.transport
        try:
            _settings.transport = "http"
            limiter = _RateLimiter(max_calls=1, window_seconds=60)
            ctx = MagicMock()
            type(ctx).session_id = property(lambda self: (_ for _ in ()).throw(RuntimeError("no session")))
            assert _rate_check(limiter, ctx) is None
        finally:
            _settings.transport = original

    def test_disabled_limiter_always_allows(self):
        from candlekeep.mcp.server import _settings
        original = _settings.transport
        try:
            _settings.transport = "http"
            limiter = _RateLimiter(max_calls=0, window_seconds=60)
            ctx = self._make_ctx()
            for _ in range(100):
                assert _rate_check(limiter, ctx) is None
        finally:
            _settings.transport = original
