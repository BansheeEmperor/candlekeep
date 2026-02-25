"""ColBERT sparse backend for hybrid retrieval.

Opt-in replacement for BM25 in the hybrid path. ColBERT uses late
interaction with token-level matching, which handles technical
identifiers better than BM25's bag-of-words approach.

Controlled via CANDLEKEEP_SPARSE_BACKEND=colbert (default: bm25).
BM25 is always maintained as fallback during ColBERT index rebuilds.

Architecture:
- Disk-based index at data_dir/colbert_index/ (shared across workers)
- Background thread rebuild (non-blocking queries)
- Graceful degradation to BM25 if ragatouille import fails

See: docs/RESEARCH_DIARY.md Entry 50 for implementation details.
     docs/ARCHITECTURE.md § Concurrency Controls for thread safety.
     docs/DESIGN.md § 4.1 for benchmark data and technique decision.
"""
import json
import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import List

from candlekeep.database.interface import SearchResult

logger = logging.getLogger("candlekeep")

# ── Availability check ──────────────────────────────────────────────
#
# RAGatouille depends on langchain but imports a submodule path
# (langchain.retrievers.document_compressors.base) that doesn't exist
# in newer langchain versions. We patch it with stub modules before
# importing ragatouille. If the patch or import fails for any reason,
# we set _COLBERT_AVAILABLE = False and the hybrid path falls back to
# BM25 with a warning log. The user gets degraded lexical precision
# instead of a crash.
#
# This patch is fragile by nature — it depends on RAGatouille's
# internal import structure. Pinned to ragatouille>=0.0.8,<0.1.0 in
# pyproject.toml to reduce breakage risk. Monitor RAGatouille releases
# for changes to the langchain dependency.
#
# See: docs/RESEARCH_DIARY.md Entry 50 § Known Limitations, item 3.

_COLBERT_AVAILABLE = False
_COLBERT_ERROR: str | None = None


def _patch_langchain():
    """Create stub modules for langchain.retrievers.document_compressors.

    RAGatouille 0.0.8-0.0.9 imports BaseDocumentCompressor from
    langchain.retrievers.document_compressors.base, but langchain >=0.2
    moved it to langchain_core.documents.compressor. This patch creates
    the expected module path pointing to the real class.

    The patch is idempotent — safe to call multiple times.
    """
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


try:
    _patch_langchain()
    from ragatouille import RAGPretrainedModel
    _COLBERT_AVAILABLE = True
except Exception as e:
    _COLBERT_ERROR = str(e)
    logger.warning(
        "[candlekeep] ColBERT unavailable: %s. Falling back to BM25.", e
    )


def is_available() -> bool:
    """Check if ColBERT backend can be used."""
    return _COLBERT_AVAILABLE


# ── Lazy model loading ──────────────────────────────────────────────

_colbert_model = None
_model_lock = threading.Lock()

_MODEL_NAME = "answerdotai/answerai-colbert-small-v1"


def _get_model():
    """Load ColBERT model singleton (thread-safe)."""
    global _colbert_model
    with _model_lock:
        if _colbert_model is None:
            _colbert_model = RAGPretrainedModel.from_pretrained(_MODEL_NAME)
            logger.info("[candlekeep] ColBERT model loaded (%s)", _MODEL_NAME)
        return _colbert_model


# ── Index directory management ──────────────────────────────────────

_INDEX_NAME = "candlekeep_colbert"
_METADATA_FILE = "chunk_metadata.json"


def _get_index_dir() -> Path:
    """Get the shared ColBERT index directory.

    Uses the Candlekeep data directory so all workers (and restarts)
    share the same index on disk.
    """
    from candlekeep.config import get_data_dir
    index_dir = get_data_dir() / "colbert_index"
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir


def _get_index_mtime() -> float:
    """Get the modification time of the live index, or 0 if none."""
    marker = _get_index_dir() / "index_ready"
    if marker.exists():
        return marker.stat().st_mtime
    return 0.0


# ── ColBERT Searcher ────────────────────────────────────────────────


class ColBERTSearcher:
    """Disk-based ColBERT index with background rebuild.

    The index is stored on disk at data_dir/colbert_index/ and shared
    across uvicorn workers via the filesystem. Rebuilds happen in a
    background thread — queries during rebuild use BM25 fallback.

    Lifecycle:
    1. add_chunks / remove_by_source mutate in-memory chunk lists
    2. Mutations mark _dirty = True
    3. On next query, ensure_index() spawns a background rebuild thread
    4. Background thread builds index to a temp dir, then atomically
       renames to the live path and touches an "index_ready" marker
    5. Other workers detect the new marker mtime and reload
    """

    def __init__(self):
        self._texts: List[str] = []
        self._doc_ids: List[str] = []
        self._metadata: dict[str, dict] = {}  # doc_id -> metadata
        self._model_for_search = None  # RAGPretrainedModel loaded from index
        self._dirty = False
        self._building = False
        self._loaded_mtime: float = 0.0  # mtime of the index we loaded
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        """True if a searchable index is loaded."""
        return self._model_for_search is not None

    @property
    def dirty(self) -> bool:
        return self._dirty

    def add_chunks(self, chunks: List[SearchResult]):
        """Add chunks and mark index dirty for lazy rebuild."""
        with self._lock:
            for chunk in chunks:
                doc_id = (
                    f"{chunk.metadata.get('source', 'unknown')}"
                    f"_{chunk.metadata.get('chunk_index', 0)}"
                )
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
            keys_to_remove = [
                k for k in self._metadata if k.startswith(f"{source}_")
            ]
            for k in keys_to_remove:
                del self._metadata[k]
            self._dirty = True

    def _rebuild_sync(self):
        """Build the index to disk (runs in background thread).

        After building, the model instance retains the searcher — we use
        it directly for this worker. The index is also saved to disk so
        other workers can load it via _load_from_disk().
        """
        with self._lock:
            if not self._texts:
                self._dirty = False
                return
            texts = list(self._texts)
            doc_ids = list(self._doc_ids)
            metadata = dict(self._metadata)

        index_dir = _get_index_dir()
        try:
            model = _get_model()
            model.index(
                index_name=_INDEX_NAME,
                collection=texts,
                document_ids=doc_ids,
                split_documents=False,
            )

            # The model now has the searcher loaded — use it directly.
            # This avoids the from_index reload that fails on first use.
            self._model_for_search = model

            # Save metadata and copy index to shared disk location
            # so other workers can load it.
            rag_index = Path(f".ragatouille/colbert/indexes/{_INDEX_NAME}")
            if rag_index.exists():
                tmp_dir = Path(tempfile.mkdtemp(
                    prefix="colbert_build_", dir=index_dir.parent
                ))
                try:
                    shutil.copytree(rag_index, tmp_dir / "index")
                    (tmp_dir / _METADATA_FILE).write_text(json.dumps(metadata))

                    # Atomic swap
                    live_dir = index_dir / "live"
                    old_dir = index_dir / "old"
                    if old_dir.exists():
                        shutil.rmtree(old_dir)
                    if live_dir.exists():
                        live_dir.rename(old_dir)
                    tmp_dir.rename(live_dir)
                    if old_dir.exists():
                        shutil.rmtree(old_dir, ignore_errors=True)

                    (index_dir / "index_ready").touch()
                    self._loaded_mtime = _get_index_mtime()
                except Exception:
                    if tmp_dir.exists():
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                    logger.warning("[candlekeep] Failed to save ColBERT index to disk")

            with self._lock:
                self._dirty = False
            logger.info(
                "[candlekeep] ColBERT index rebuilt (%d chunks)", len(texts)
            )
        except Exception:
            logger.exception("[candlekeep] ColBERT index rebuild failed")
        finally:
            with self._lock:
                self._building = False

    def _load_from_disk(self):
        """Load a pre-built index from disk."""
        index_dir = _get_index_dir()
        live_index = index_dir / "live" / "index"
        meta_path = index_dir / "live" / _METADATA_FILE

        if not live_index.exists():
            return

        try:
            model = RAGPretrainedModel.from_index(str(live_index))
            self._model_for_search = model
            self._loaded_mtime = _get_index_mtime()

            # Load metadata if available
            if meta_path.exists():
                self._metadata = json.loads(meta_path.read_text())

            logger.info("[candlekeep] ColBERT index loaded from disk")
        except Exception:
            logger.warning("[candlekeep] Failed to load ColBERT index from disk")

    def _check_reload(self):
        """Reload from disk if another worker rebuilt the index."""
        current_mtime = _get_index_mtime()
        if current_mtime > self._loaded_mtime:
            self._load_from_disk()

    def ensure_index(self):
        """Trigger rebuild if dirty, or reload if stale. Non-blocking.

        Returns True if the index is ready for searching.
        """
        # Check if another worker has a newer index
        if not self._dirty and not self._building:
            self._check_reload()

        # Trigger background rebuild if dirty
        if self._dirty and not self._building:
            with self._lock:
                if self._dirty and not self._building:
                    self._building = True
                    thread = threading.Thread(
                        target=self._rebuild_sync, daemon=True
                    )
                    thread.start()

        return self.ready

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Search the ColBERT index. Returns empty if not ready."""
        if not self.ready:
            return []

        try:
            raw = self._model_for_search.search(
                query=query, k=n_results
            )
        except Exception:
            logger.warning("[candlekeep] ColBERT search failed, returning empty")
            return []

        results = []
        for r in raw:
            doc_id = r.get("document_id", "")
            meta = self._metadata.get(doc_id, {})
            if isinstance(meta, dict):
                meta = meta.copy()
            else:
                meta = {}
            results.append(SearchResult(
                text=r.get("content", ""),
                metadata=meta,
                score=float(r.get("score", 0.0)),
                doc_id=doc_id,
            ))
        return results

    def clear(self):
        """Full reset — clears in-memory state and disk index."""
        with self._lock:
            self._texts.clear()
            self._doc_ids.clear()
            self._metadata.clear()
            self._model_for_search = None
            self._dirty = False
            self._building = False
            self._loaded_mtime = 0.0

        # Remove disk index
        index_dir = _get_index_dir()
        live_dir = index_dir / "live"
        marker = index_dir / "index_ready"
        if live_dir.exists():
            shutil.rmtree(live_dir, ignore_errors=True)
        if marker.exists():
            marker.unlink(missing_ok=True)


# ── Global cache (mirrors BM25 cache pattern) ──────────────────────

_colbert_cache: ColBERTSearcher | None = None
_cache_lock = threading.Lock()


def get_colbert_searcher(db) -> ColBERTSearcher | None:
    """Get or create the global ColBERT searcher.

    On first call, loads all chunks from the database. If a pre-built
    index exists on disk, loads it immediately (fast cold start).
    Otherwise marks dirty for background rebuild on first query.

    Returns None if ColBERT is not available (import failed).
    """
    if not _COLBERT_AVAILABLE:
        return None

    global _colbert_cache
    with _cache_lock:
        if _colbert_cache is None:
            searcher = ColBERTSearcher()

            # Try loading existing disk index first (fast cold start)
            searcher._load_from_disk()
            had_disk_index = searcher.ready

            # Load chunk data from DB for future rebuilds
            chunks = db.get_all_chunks()
            if chunks:
                searcher.add_chunks(chunks)
                # add_chunks sets _dirty = True. If we loaded a disk
                # index, the chunks may match it — but we can't verify
                # without comparing. Keep dirty so the next query
                # triggers a rebuild with the current DB state.
                # The disk index serves queries until the rebuild
                # completes, so there's no quality gap.

            _colbert_cache = searcher
        return _colbert_cache


def clear_colbert_cache():
    """Full invalidation — clears memory and disk index.

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

    Marks the index dirty for background rebuild on next query. Does
    NOT rebuild immediately — single-file ingestion stays fast.
    """
    global _colbert_cache
    with _cache_lock:
        if _colbert_cache is None:
            return
        if removed_source:
            _colbert_cache.remove_by_source(removed_source)
        if new_chunks:
            _colbert_cache.add_chunks(new_chunks)


def remove_from_colbert_cache(source: str):
    """Remove a source from the ColBERT cache after a delete."""
    global _colbert_cache
    with _cache_lock:
        if _colbert_cache is None:
            return
        _colbert_cache.remove_by_source(source)
