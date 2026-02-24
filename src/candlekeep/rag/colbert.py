"""ColBERT sparse backend for hybrid retrieval.

Opt-in replacement for BM25 in the hybrid path. ColBERT uses late
interaction with token-level matching, which handles technical
identifiers better than BM25's bag-of-words approach.

Controlled via CANDLEKEEP_SPARSE_BACKEND=colbert (default: bm25).
BM25 is always maintained as fallback during ColBERT index rebuilds.
"""
import logging
import sys
import threading
from pathlib import Path
from typing import List

from candlekeep.database.interface import SearchResult

logger = logging.getLogger("candlekeep")

# ── Lazy model loading ──────────────────────────────────────────────

_colbert_model = None
_model_lock = threading.Lock()


def _patch_langchain():
    """RAGatouille imports langchain.retrievers which may not exist."""
    import langchain
    if not hasattr(langchain, "retrievers"):
        import types
        import sys as _sys
        from langchain_core.documents.compressor import BaseDocumentCompressor
        retrievers = types.ModuleType("langchain.retrievers")
        dc = types.ModuleType("langchain.retrievers.document_compressors")
        base = types.ModuleType("langchain.retrievers.document_compressors.base")
        base.BaseDocumentCompressor = BaseDocumentCompressor
        dc.base = base
        retrievers.document_compressors = dc
        langchain.retrievers = retrievers
        _sys.modules["langchain.retrievers"] = retrievers
        _sys.modules["langchain.retrievers.document_compressors"] = dc
        _sys.modules["langchain.retrievers.document_compressors.base"] = base


def _get_model():
    """Load ColBERT model singleton (thread-safe)."""
    global _colbert_model
    with _model_lock:
        if _colbert_model is None:
            _patch_langchain()
            from ragatouille import RAGPretrainedModel
            _colbert_model = RAGPretrainedModel.from_pretrained(
                "answerdotai/answerai-colbert-small-v1"
            )
            logger.info("[candlekeep] ColBERT model loaded")
        return _colbert_model


# ── ColBERT Searcher ────────────────────────────────────────────────

_INDEX_NAME = "candlekeep_colbert"


class ColBERTSearcher:
    """In-memory ColBERT index for lexical retrieval.

    The index is built lazily on first query after ingestion marks it
    dirty. During rebuild, queries fall back to BM25 transparently.
    """

    def __init__(self):
        self._texts: List[str] = []
        self._doc_ids: List[str] = []
        self._metadata: dict[str, dict] = {}  # doc_id -> metadata
        self._index = None
        self._dirty = False
        self._building = False
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        """True if the index exists and is not being rebuilt."""
        return self._index is not None and not self._building

    @property
    def dirty(self) -> bool:
        return self._dirty

    def add_chunks(self, chunks: List[SearchResult]):
        """Add chunks and mark index dirty for lazy rebuild."""
        with self._lock:
            for chunk in chunks:
                doc_id = f"{chunk.metadata.get('source', 'unknown')}_{chunk.metadata.get('chunk_index', 0)}"
                self._texts.append(chunk.text)
                self._doc_ids.append(doc_id)
                self._metadata[doc_id] = chunk.metadata.copy()
            self._dirty = True

    def remove_by_source(self, source: str):
        """Remove all chunks from a source and mark dirty."""
        with self._lock:
            indices_to_remove = [
                i for i, did in enumerate(self._doc_ids)
                if did.startswith(f"{source}_")
            ]
            if not indices_to_remove:
                return
            for i in reversed(indices_to_remove):
                del self._texts[i]
                del self._doc_ids[i]
            # Clean metadata
            keys_to_remove = [k for k in self._metadata if k.startswith(f"{source}_")]
            for k in keys_to_remove:
                del self._metadata[k]
            self._dirty = True

    def rebuild(self):
        """Rebuild the ColBERT index from current texts.

        Called lazily on next query when dirty, or after batch ingestion.
        """
        with self._lock:
            if not self._texts:
                self._index = None
                self._dirty = False
                return
            self._building = True

        try:
            model = _get_model()
            index = model.index(
                index_name=_INDEX_NAME,
                collection=list(self._texts),
                document_ids=list(self._doc_ids),
                split_documents=False,
            )
            with self._lock:
                self._index = index
                self._dirty = False
                self._building = False
            logger.info(
                "[candlekeep] ColBERT index rebuilt (%d chunks)", len(self._texts)
            )
        except Exception:
            with self._lock:
                self._building = False
            logger.exception("[candlekeep] ColBERT index rebuild failed")
            raise

    def ensure_index(self):
        """Rebuild if dirty. Returns True if index is ready."""
        if self._dirty and not self._building:
            self.rebuild()
        return self.ready

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Search the ColBERT index. Returns empty if not ready."""
        if not self.ready:
            return []

        model = _get_model()
        try:
            raw = model.search(query=query, k=n_results, index_name=_INDEX_NAME)
        except Exception:
            logger.warning("[candlekeep] ColBERT search failed, returning empty")
            return []

        results = []
        for r in raw:
            doc_id = r.get("document_id", "")
            meta = self._metadata.get(doc_id, {})
            results.append(SearchResult(
                text=r.get("content", ""),
                metadata=meta.copy(),
                score=float(r.get("score", 0.0)),
                doc_id=doc_id,
            ))
        return results

    def clear(self):
        """Full reset."""
        with self._lock:
            self._texts.clear()
            self._doc_ids.clear()
            self._metadata.clear()
            self._index = None
            self._dirty = False
            self._building = False


# ── Global cache (mirrors BM25 cache pattern) ──────────────────────

_colbert_cache: ColBERTSearcher | None = None
_cache_lock = threading.Lock()


def get_colbert_searcher(db) -> ColBERTSearcher:
    """Get or create the global ColBERT searcher.

    On first call, loads all chunks from the database and builds the
    index. Subsequent calls return the cached searcher.
    """
    global _colbert_cache
    with _cache_lock:
        if _colbert_cache is None:
            chunks = db.get_all_chunks()
            if chunks:
                searcher = ColBERTSearcher()
                searcher.add_chunks(chunks)
                searcher.rebuild()
                _colbert_cache = searcher
        return _colbert_cache


def clear_colbert_cache():
    """Full invalidation — forces rebuild on next query.

    Use only for repopulate_database.
    """
    global _colbert_cache
    with _cache_lock:
        if _colbert_cache is not None:
            _colbert_cache.clear()
        _colbert_cache = None


def update_colbert_cache(
    new_chunks: List[SearchResult], removed_source: str | None = None
):
    """Incrementally update the ColBERT cache after a write operation.

    Marks the index dirty for lazy rebuild on next query. Does NOT
    rebuild immediately — single-file ingestion should be fast.
    """
    global _colbert_cache
    with _cache_lock:
        if _colbert_cache is None:
            # Cache not initialized yet. Let the next query do full init.
            return
        if removed_source:
            _colbert_cache.remove_by_source(removed_source)
        if new_chunks:
            _colbert_cache.add_chunks(new_chunks)
        # Index is now dirty — will rebuild lazily on next search.


def remove_from_colbert_cache(source: str):
    """Remove a source from the ColBERT cache after a delete."""
    global _colbert_cache
    with _cache_lock:
        if _colbert_cache is None:
            return
        _colbert_cache.remove_by_source(source)
