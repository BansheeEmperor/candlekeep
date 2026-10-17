"""Unit tests for paged full-collection reads (chromadb >= 1.5 get() limit)."""
import pytest

from candlekeep.config import Settings
from candlekeep.database import vector_store as vs
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag import hybrid

pytestmark = [pytest.mark.unit]

# chromadb >= 1.5 fails a get() returning metadatas for more records than this.
CHROMA_GET_LIMIT = 32766


class _CappedCollection:
    """In-memory stand-in that fails like chromadb >= 1.5 on oversized reads."""

    def __init__(self, n):
        self.ids = [f"id{i}" for i in range(n)]
        self.docs = [f"chunk {i} about vector search" for i in range(n)]
        self.metas = [{"source": f"doc{i % 7}.md", "collection": "default"} for i in range(n)]
        self.calls = []

    def count(self):
        return len(self.ids)

    def get(self, limit=None, offset=0, include=("documents", "metadatas"), **_):
        self.calls.append((limit, offset, tuple(include)))
        end = len(self.ids) if limit is None else offset + limit
        if "metadatas" in include and min(end, len(self.ids)) - offset > CHROMA_GET_LIMIT:
            raise RuntimeError("Error executing plan: (code: 1) too many SQL variables")
        sl = slice(offset, end)
        return {
            "ids": self.ids[sl],
            "documents": self.docs[sl] if "documents" in include else None,
            "metadatas": self.metas[sl] if "metadatas" in include else None,
        }


def _store(n):
    store = object.__new__(ChromaVectorStore)
    store.settings = Settings()
    store.collection = _CappedCollection(n)
    store._reconnect_attempts = 1
    store._reconnect_backoff = 0.0
    return store


class TestGetPaginated:
    @pytest.mark.parametrize("n", [0, 1, vs._GET_PAGE_SIZE, 2 * vs._GET_PAGE_SIZE + 3])
    def test_returns_every_record_once_in_order(self, n):
        store = _store(n)
        r = store._get_paginated()
        assert r["ids"] == store.collection.ids
        assert r["documents"] == store.collection.docs
        assert r["metadatas"] == store.collection.metas

    def test_every_request_is_bounded(self):
        store = _store(2 * vs._GET_PAGE_SIZE + 3)
        store._get_paginated()
        assert all(limit == vs._GET_PAGE_SIZE for limit, _, _ in store.collection.calls)
        assert len(store.collection.calls) == 3

    def test_include_selects_fields(self):
        r = _store(10)._get_paginated(include=["documents"])
        assert "metadatas" not in r and len(r["documents"]) == 10

    def test_page_size_is_below_chroma_limit(self):
        assert vs._GET_PAGE_SIZE <= CHROMA_GET_LIMIT


class TestFullCollectionReadsPastChromaLimit:
    """The four callers that used to issue one unbounded get()."""

    N = CHROMA_GET_LIMIT + 1

    def test_unpaged_get_fails_like_chroma(self):
        with pytest.raises(RuntimeError, match="too many SQL variables"):
            _store(self.N).collection.get()

    def test_get_all_chunks(self):
        assert len(_store(self.N).get_all_chunks()) == self.N

    def test_list_documents(self):
        docs = _store(self.N).list_documents()
        assert sum(d["chunks"] for d in docs) == self.N and len(docs) == 7

    def test_bm25_cache(self):
        hybrid.clear_bm25_cache()
        try:
            bm25, ids = hybrid.update_bm25_cache(_store(self.N))
            assert len(ids) == self.N and bm25.corpus_size == self.N
        finally:
            hybrid.clear_bm25_cache()
