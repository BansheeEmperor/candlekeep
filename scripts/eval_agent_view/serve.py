#!/usr/bin/env python3
"""Layer 2 server launcher: a candlekeep server whose startup write probe never
reaches Chroma (protocol section 16, pre-run deviation on read-only servers).

Candlekeep's background init checks write access by adding and then deleting the
point "__auth_test__" in the shared collection, which changes that collection's
HNSW index on every server start. Before candlekeep is imported, this script
wraps chromadb's Collection.add and Collection.delete: a call whose ids are
exactly the probe's (["__auth_test__"] or "__auth_test__", passed positionally
or as ids=) raises

    PermissionError("evaluation server: write probe disabled")

without contacting Chroma; every other call goes through unchanged. Candlekeep
catches the error and logs "⚠ Read-only mode (write access denied)"; its search
tools do not depend on write access. The script then imports
candlekeep.mcp.server with importlib.import_module (the candlekeep package
rebinds the name candlekeep.mcp, so a plain import cannot be used) and calls its
main(), as the `candlekeep` console script does.

It uses only the standard library and chromadb, so it runs in every state's venv
(FastMCP 2.14.5 in A, 3.4.9 in B and C). drive.py l2 starts it as

    <state venv>/bin/python scripts/eval_agent_view/serve.py

with the server's environment, and fails the step unless this server's log shows
the "neutralised" and "blocked" lines printed here and candlekeep's read-only
line. The ingest server is started with the `candlekeep` command and keeps the
probe.
"""
from __future__ import annotations

import functools
import importlib
import os
import sqlite3
import sys

PROBE_ID = "__auth_test__"
PROBE_ERROR = "evaluation server: write probe disabled"
TAG = "[serve.py]"
# Lines drive.py looks for in the server log (keep in sync with drive.py).
NEUTRALISED_LINE = f"{TAG} write probe neutralised: chromadb Collection.add/delete refuse ids ['{PROBE_ID}']"
BLOCKED_LINE = f"{TAG} blocked Collection.{{method}}(ids=['{PROBE_ID}']) before it reached Chroma"


def _say(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


def is_probe_call(args: tuple, kwargs: dict) -> bool:
    """True when the ids of an add/delete call are exactly the probe's: the first
    positional argument or ids=, either "__auth_test__" or a one-element list
    (or tuple) holding it."""
    if "ids" in kwargs:
        ids = kwargs["ids"]
    elif args:
        ids = args[0]
    else:
        return False
    if isinstance(ids, str):
        return ids == PROBE_ID
    if isinstance(ids, (list, tuple)):
        return len(ids) == 1 and isinstance(ids[0], str) and ids[0] == PROBE_ID
    return False


def _guarded(method: str, original):
    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        if is_probe_call(args, kwargs):
            _say(BLOCKED_LINE.format(method=method))
            raise PermissionError(PROBE_ERROR)
        return original(self, *args, **kwargs)

    wrapper.__ck_eval_probe_guard__ = True
    return wrapper


def neutralise_write_probe() -> None:
    """Wrap chromadb.api.models.Collection.Collection.add and .delete (idempotent)."""
    from chromadb.api.models.Collection import Collection
    for method in ("add", "delete"):
        original = getattr(Collection, method)
        if not getattr(original, "__ck_eval_probe_guard__", False):
            setattr(Collection, method, _guarded(method, original))
    _say(NEUTRALISED_LINE)


def main() -> int:
    # Run like the console script: the harness directory (this script's, which
    # Python puts first on sys.path) must not shadow any module the server imports.
    here = os.path.dirname(os.path.realpath(__file__))
    sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.curdir) != here]
    # The candlekeep package swaps in pysqlite3 before chromadb is imported when the
    # SQLite library is older than 3.35; importing chromadb first would bypass that.
    if sqlite3.sqlite_version_info < (3, 35, 0):
        _say(f"{TAG} SQLite {sqlite3.sqlite_version} < 3.35: refusing (candlekeep would swap in pysqlite3 "
             "before chromadb is imported)")
        return 2
    neutralise_write_probe()
    server = importlib.import_module("candlekeep.mcp.server")
    _say(f"{TAG} candlekeep.mcp.server from {server.__file__}")
    return server.main()


if __name__ == "__main__":
    sys.exit(main())
