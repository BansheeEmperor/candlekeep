"""Candlekeep: RAG knowledge base server."""
import sys

# Check Python version
if sys.version_info < (3, 10):
    raise RuntimeError(
        f"Candlekeep requires Python 3.10+, found {sys.version_info.major}.{sys.version_info.minor}"
    )

# Check SQLite support (ChromaDB dependency)
try:
    import sqlite3
except ImportError:
    # Try pysqlite3 as fallback
    try:
        import pysqlite3 as sqlite3
        sys.modules['sqlite3'] = sqlite3
    except ImportError:
        raise RuntimeError(
            "Candlekeep requires Python with SQLite support (ChromaDB dependency)."
        )

# ChromaDB requires SQLite >= 3.35.0
if sqlite3.sqlite_version_info < (3, 35, 0):
    try:
        __import__("pysqlite3")
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    except ImportError:
        raise RuntimeError(
            f"ChromaDB requires SQLite >= 3.35.0, found {sqlite3.sqlite_version}\n"
            "Fix: pip install pysqlite3"
        )

from candlekeep.mcp.server import mcp, main

__all__ = ["mcp", "main"]
