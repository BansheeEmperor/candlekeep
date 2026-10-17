"""Unit tests for the BM25 cache under concurrent (thread-pool) tool execution."""
import threading
import time

import pytest

from candlekeep.rag import hybrid

pytestmark = [pytest.mark.unit]


class _Store:
    """Counts full-collection reads; optionally clears the cache mid-read like a self-heal."""

    def __init__(self, n=50, delay=0.0, heal_on_first_read=False):
        self.reads = 0
        self.n, self.delay, self.heal = n, delay, heal_on_first_read

    def _get_paginated(self, include=None):
        self.reads += 1
        if self.heal and self.reads == 1:
            hybrid.clear_bm25_cache()  # what ChromaVectorStore._reconnect() triggers
        time.sleep(self.delay)
        ids = [f"id{i}" for i in range(self.n)]
        return {"ids": ids, "documents": [f"chunk {i} vector search index" for i in range(self.n)]}


@pytest.fixture(autouse=True)
def _fresh_cache():
    hybrid.clear_bm25_cache()
    yield
    hybrid.clear_bm25_cache()


def test_concurrent_cold_queries_build_once():
    store = _Store(delay=0.2)
    results = []
    threads = [threading.Thread(target=lambda: results.append(hybrid.update_bm25_cache(store))) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert store.reads == 1
    assert len({id(bm25) for bm25, _ in results}) == 1


def test_self_heal_during_build_does_not_deadlock_and_rebuilds():
    store = _Store(heal_on_first_read=True)
    done = []
    t = threading.Thread(target=lambda: done.append(hybrid.update_bm25_cache(store)), daemon=True)
    t.start()
    t.join(timeout=5)
    assert done, "update_bm25_cache deadlocked on a clear from inside the build"
    assert store.reads == 2  # the build that spanned the clear was redone
    bm25, ids = done[0]
    assert bm25.corpus_size == len(ids) == 50


def test_clear_during_build_is_not_lost():
    store = _Store(delay=0.3)
    t = threading.Thread(target=hybrid.update_bm25_cache, args=(store,))
    t.start()
    time.sleep(0.05)
    hybrid.clear_bm25_cache()  # e.g. an ingest finishing while a query builds
    t.join()
    hybrid.update_bm25_cache(store)
    assert store.reads == 2  # the post-clear query rebuilt from the new data
