"""ChromaDB vector store with authentication support."""
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Any
import chromadb
import chromadb.errors
from candlekeep.config import Settings
from candlekeep.database.embeddings import EmbeddingManager
from candlekeep.database.interface import VectorDatabase, SearchResult, Chunk


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _is_stale_collection(exc: Exception) -> bool:
    """True if the error means our cached collection handle points at a UUID
    that no longer exists.

    Happens after a full re-ingest (KB sync): the rebuilt 'candlekeep'
    collection gets a NEW UUID, but this process resolved the handle once at
    startup and keeps querying the old UUID -> 'Collection [<uuid>] does not
    exist.' Detected by message + class name to stay robust across chromadb
    versions.
    """
    msg = str(exc).lower()
    if "does not exist" in msg or ("collection" in msg and "not found" in msg):
        return True
    name = type(exc).__name__.lower()
    return "collection" in name and any(t in name for t in ("notfound", "invalid", "exist"))


def _is_chroma_unavailable(exc: Exception) -> bool:
    """True if the error looks like the Chroma server is unreachable.

    During a KB sync we restart ONLY Chroma and keep this (Candlekeep) process
    warm. A query landing in the brief Chroma-down window should wait and
    retry, not surface a hard error to the client.
    """
    msg = str(exc).lower()
    name = type(exc).__name__.lower()
    needles = (
        "connection", "connect", "refused", "timed out", "timeout",
        "max retries", "could not connect", "failed to connect",
        "remote end closed", "server disconnected", "connection reset",
    )
    return any(n in msg for n in needles) or any(n in name for n in ("connect", "timeout"))


class ChromaVectorStore(VectorDatabase):
    """ChromaDB implementation with authentication."""

    # Class-level defaults so instances built without __init__ still self-heal.
    _reconnect_attempts = 5
    _reconnect_backoff = 1.0
    
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.embedder = EmbeddingManager.get_instance(self.settings)

        # Self-heal tuning: how hard to retry a collection op when Chroma is
        # mid-restart (KB sync) before giving up. Stale-collection re-resolves
        # are instant and not bounded by this; the backoff only paces the
        # Chroma-unreachable case.
        self._reconnect_attempts = int(os.getenv("CANDLEKEEP_RECONNECT_ATTEMPTS", "5"))
        self._reconnect_backoff = float(os.getenv("CANDLEKEEP_RECONNECT_BACKOFF", "1.0"))

        # Setup auth headers
        headers = {}
        if self.settings.chroma_auth_token:
            headers["Authorization"] = f"Bearer {self.settings.chroma_auth_token}"
        
        # Connect to ChromaDB
        try:
            if self.settings.chroma_path:
                self.client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
            else:
                self.client = chromadb.HttpClient(
                    host=self.settings.chroma_host,
                    port=self.settings.chroma_port,
                    headers=headers if headers else None,
                    ssl=self.settings.chroma_ssl
                )
            self._open_collection()
            # Check if remote DB was populated with a different model
            remote_model = self.collection.metadata.get("embedding_model")
            if remote_model and remote_model != self.settings.embedding_model:
                print(f"[candlekeep] ⚠ Remote DB uses '{remote_model}' embeddings, "
                      f"overriding local '{self.settings.embedding_model}'", file=sys.stderr)
                self.settings.embedding_model = remote_model
                # Reset embedder to use the correct model
                EmbeddingManager._instance = None
                EmbeddingManager._model = None
                EmbeddingManager._current_model = None
                self.embedder = EmbeddingManager.get_instance(self.settings)
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to ChromaDB at {self.settings.chroma_url}: {e}"
            )
        
        # Metrics
        self._query_count = 0
        self._graph_store = None

    @property
    def graph_store(self) -> Any:
        """Access the associated graph database."""
        if self._graph_store is None:
            from candlekeep.database.graph_store import get_graph_store
            self._graph_store = get_graph_store(self.settings)
        return self._graph_store

    @graph_store.setter
    def graph_store(self, value: Any) -> None:
        """Set the associated graph database."""
        self._graph_store = value

    def _open_collection(self):
        """(Re)resolve the 'candlekeep' collection handle by name.

        The chromadb client binds a Collection object to its UUID at resolution
        time. After a full re-ingest the UUID changes, so this MUST be callable
        at runtime (not just in __init__) to pick up a swapped-in KB without a
        process restart.
        """
        self.collection = self.client.get_or_create_collection(
            name="candlekeep",
            metadata={"hnsw:space": "cosine", "embedding_model": self.settings.embedding_model},
        )
        return self.collection

    def _invalidate_worker_caches(self):
        """Flush in-memory caches derived from collection contents.

        BM25, the normalisation map, the entity graph and (optionally) ColBERT
        are built once per worker from the corpus. After a data swap they
        describe the OLD corpus; clearing forces a lazy rebuild from the new
        collection on the next query — added latency, never a wrong answer.
        Each clear is independent and best-effort.
        """
        for mod, fn in (
            ("candlekeep.rag.hybrid", "clear_bm25_cache"),
            ("candlekeep.rag.token_normalisation", "clear_normalisation_cache"),
            ("candlekeep.database.graph_store", "clear_graph_store_cache"),
        ):
            try:
                m = __import__(mod, fromlist=[fn])
                getattr(m, fn)()
            except Exception:
                pass
        if os.getenv("CANDLEKEEP_SPARSE_BACKEND", "bm25") == "colbert":
            try:
                from candlekeep.rag.colbert import clear_colbert_cache
                clear_colbert_cache()
            except Exception:
                pass

    def _reconnect(self):
        """Self-heal after a Chroma data swap or restart: re-resolve the
        collection by name (handles a new UUID) and drop the per-worker derived
        caches. Keeps the process warm — no restart required."""
        old_id = getattr(self.collection, "id", None)
        self._open_collection()
        new_id = getattr(self.collection, "id", None)
        self._invalidate_worker_caches()
        # Observability: make a sync's self-heal visible in CK logs so a stale
        # collection (and the one-time cache rebuild it triggers) is auditable.
        print(f"[candlekeep] self-heal: re-resolved collection 'candlekeep' "
              f"{old_id} -> {new_id}; derived caches flushed", file=sys.stderr)

    def _collection_op(self, fn):
        """Run a collection read with self-healing so a Chroma-only restart
        (the KB sync path) stays invisible to callers:

          * stale collection UUID (data swapped underneath us) -> re-resolve by
            name + flush caches, retry immediately;
          * Chroma unreachable (server mid-restart) -> short backoff,
            re-resolve, retry.

        Any other error, or exhausted retries, re-raises the original.
        """
        last = None
        for i in range(self._reconnect_attempts):
            try:
                return fn(self.collection)
            except Exception as e:
                last = e
                if _is_stale_collection(e):
                    self._reconnect()
                    continue
                if _is_chroma_unavailable(e) and i < self._reconnect_attempts - 1:
                    time.sleep(self._reconnect_backoff * (i + 1))
                    try:
                        self._reconnect()
                    except Exception:
                        pass
                    continue
                raise
        raise last

    def _query(self, **kwargs):
        """Self-healing wrapper around collection.query()."""
        return self._collection_op(lambda col: col.query(**kwargs))

    def _get(self, **kwargs):
        """Self-healing wrapper around collection.get()."""
        return self._collection_op(lambda col: col.get(**kwargs))

    def _count(self):
        """Self-healing wrapper around collection.count()."""
        return self._collection_op(lambda col: col.count())

    def _generate_id(self, chunk: Chunk) -> str:
        """Generate unique ID for a chunk."""
        content = f"{chunk.metadata['source']}:{chunk.chunk_index}:{chunk.text[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add_documents(self, chunks: list[Chunk], collection: str = "default", llm: Any = None, extractor_model: str = "en_core_web_sm") -> int:
        """Add chunks to the vector store."""
        if not chunks:
            return 0

        # Delete existing chunks from same sources
        sources = set(c.metadata["source"] for c in chunks)
        for source in sources:
            results = self._get(where={"source": source})
            if results["ids"]:
                self.collection.delete(ids=results["ids"])

        ids = [self._generate_id(c) for c in chunks]
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        metadatas = [{**c.metadata, "collection": collection, "chunk_index": c.chunk_index} for c in chunks]

        # Entity extraction — add entities array to metadata and populate graph
        try:
            from candlekeep.rag.extractor import get_extractor
            from candlekeep.database.graph_store import get_graph_store, schedule_graph_rebuild
            extractor = get_extractor(ruler_path=self.settings.entity_ruler_path, model_name=extractor_model)
            graph_store = get_graph_store(self.settings)
            mentions: list[tuple[str, str, int]] = []
            for meta, text, chunk in zip(metadatas, texts, chunks):
                entities = extractor.extract(text)
                if entities:
                    meta["entities"] = entities
                    if graph_store:
                        source = meta["source"]
                        idx = chunk.chunk_index
                        mentions.extend((e, source, idx) for e in entities)
            if graph_store and mentions:
                graph_store.add_mentions(mentions)
                # Per-file co-occurrence rebuild is O(graph size); during bulk
                # ingest it re-runs on an ever-growing graph and dominates wall
                # time. CANDLEKEEP_DEFER_GRAPH_REBUILD=1 skips it here; the
                # caller MUST invoke the rebuild_graph tool once after the bulk
                # load to materialise the co-occurrence table.
                if os.getenv("CANDLEKEEP_DEFER_GRAPH_REBUILD", "").lower() not in ("1", "true"):
                    schedule_graph_rebuild(graph_store)
        except Exception:
            pass  # entity extraction must never block ingestion

        # Batch upsert to avoid exceeding maximum batch size (e.g. 5461 in Chroma)
        batch_size = 1000
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            self.collection.upsert(
                ids=ids[i:end], 
                embeddings=embeddings[i:end], 
                documents=texts[i:end], 
                metadatas=metadatas[i:end]
            )

        # Reset sparse caches for lazy rebuild on next search.
        from candlekeep.rag.hybrid import clear_bm25_cache
        clear_bm25_cache()

        # If ColBERT backend is active, mark its index dirty for lazy rebuild.
        import os
        if os.getenv("CANDLEKEEP_SPARSE_BACKEND", "bm25") == "colbert":
            from candlekeep.rag.colbert import mark_colbert_dirty
            mark_colbert_dirty()

        # Schedule background normalisation map rebuild. Non-blocking —
        # mirrors the ColBERT dirty-flag pattern. Queries use the stale
        # map until the rebuild completes; no latency impact on ingest.
        from candlekeep.rag.token_normalisation import schedule_background_rebuild
        schedule_background_rebuild(self)

        return len(chunks)

    def search(self, query: str, n_results: int = 5, category: str | None = None) -> list[SearchResult]:
        """Search for similar documents with metadata re-ranking."""
        embedding = self.embedder.embed_query(query)
        
        # Build where clause for category filtering
        where = {"category": category} if category else None
        
        # Fetch extra candidates for re-ranking
        results = self._query(
            query_embeddings=[embedding], n_results=n_results * 3, where=where
        )

        if not results["ids"][0]:
            return []

        candidates = [
            SearchResult(
                text=doc,
                metadata=meta,
                score=1 - dist,  # Convert distance to similarity
                doc_id=doc_id,
            )
            for doc_id, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

        # Filter out overview/index documents
        excluded_files = {"index.md", "README.md", "readme.md"}
        candidates = [
            r for r in candidates 
            if r.metadata.get("filename", "") not in excluded_files
        ]

        # Re-rank with metadata boosting (Bardic Inspiration)
        query_terms = set(query.lower().split())
        
        # Caption chunk boosting configuration
        caption_boost_flat = float(os.getenv("CANDLEKEEP_CAPTION_BOOST", "0.0"))
        caption_boost_adaptive = os.getenv("CANDLEKEEP_CAPTION_BOOST_ADAPTIVE", "false").lower() == "true"
        
        for r in candidates:
            boost = 0
            
            # Caption chunk boost — helps surface visual content in agent context
            if r.metadata.get("content_type") == "image_caption":
                if caption_boost_adaptive:
                    # Adaptive: boost proportional to similarity (only if already relevant)
                    if r.score > 0.5:
                        boost += min(r.score * 0.8, 1.0)
                elif caption_boost_flat > 0:
                    # Flat: constant boost for all caption chunks
                    boost += caption_boost_flat
            
            # Title matching - High priority
            title = r.metadata.get("title", "").lower()
            title_matches = sum(1 for t in query_terms if t in title)
            if title_matches > 0:
                # Up to 0.6 boost for title (significant)
                boost += min(title_matches * 0.2, 0.6)
            
            # Description matching - Medium priority
            description = r.metadata.get("description", "").lower()
            desc_matches = sum(1 for t in query_terms if t in description)
            if desc_matches > 0:
                boost += min(desc_matches * 0.1, 0.3)
            
            # Keyword matching - Medium priority
            keywords = r.metadata.get("keywords", "").lower()
            kw_matches = sum(1 for t in query_terms if t in keywords)
            if kw_matches > 0:
                boost += min(kw_matches * 0.1, 0.3)
            
            r.score += boost

        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:n_results]

    def delete_by_source(self, source: str) -> int:
        """Delete all chunks from a source file."""
        from candlekeep.rag.hybrid import remove_from_bm25_cache
        from candlekeep.database.graph_store import get_graph_store

        results = self._get(where={"source": source})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            remove_from_bm25_cache(source)
            gs = get_graph_store(self.settings)
            if gs:
                gs.remove_by_source(source)
            import os
            if os.getenv("CANDLEKEEP_SPARSE_BACKEND", "bm25") == "colbert":
                from candlekeep.rag.colbert import remove_from_colbert_cache
                remove_from_colbert_cache(source)
            return len(results["ids"])
        return 0

    def clear(self) -> None:
        """Clear all documents from the collection."""
        from candlekeep.rag.hybrid import clear_bm25_cache
        from candlekeep.rag.token_normalisation import clear_normalisation_cache
        from candlekeep.database.graph_store import get_graph_store, clear_graph_store_cache
        clear_bm25_cache()
        clear_normalisation_cache()
        gs = get_graph_store(self.settings)
        if gs:
            gs.clear()
        clear_graph_store_cache()
        import os
        if os.getenv("CANDLEKEEP_SPARSE_BACKEND", "bm25") == "colbert":
            from candlekeep.rag.colbert import clear_colbert_cache
            clear_colbert_cache()
        
        self.client.delete_collection("candlekeep")
        # Brief pause to let ChromaDB finish cleaning up the deleted
        # collection's HNSW index before creating a new one.
        import time
        time.sleep(0.5)
        self.collection = self.client.get_or_create_collection(
            name="candlekeep", metadata={"hnsw:space": "cosine"}
        )

    def list_documents(self) -> list[dict]:
        """List all unique source documents."""
        results = self._get()
        sources = {}
        for meta in results["metadatas"]:
            src = meta["source"]
            if src not in sources:
                sources[src] = {
                    "source": src,
                    "collection": meta.get("collection", "default"),
                    "chunks": 0
                }
            sources[src]["chunks"] += 1
        return list(sources.values())

    def get_stats(self) -> dict:
        """Get collection statistics."""
        count = self._count()
        docs = self.list_documents()
        
        # Calculate database size
        db_path = self.settings.chroma_dir
        try:
            total_size = sum(f.stat().st_size for f in db_path.rglob("*") if f.is_file())
        except (FileNotFoundError, OSError):
            total_size = 0
        
        # Estimate tokens
        all_docs = self._get()
        total_chars = sum(len(doc) for doc in all_docs.get("documents", []))
        estimated_tokens = total_chars // 4
        
        tokens_per_query = (5 * self.settings.chunk_size) // 4
        
        stats = {
            "total_chunks": count,
            "total_documents": len(docs),
            "database_size_bytes": total_size,
            "database_size_human": _human_readable_size(total_size),
            "total_characters": total_chars,
            "estimated_tokens": estimated_tokens,
            "tokens_per_query": tokens_per_query,
            "context_savings_ratio": estimated_tokens / tokens_per_query if tokens_per_query else 0,
        }
        
        # Add embedding cache stats
        cache_stats = self.embedder.get_cache_stats()
        stats["embed_cache_hits"] = cache_stats["embedding_cache_hits"]
        stats["embed_cache_misses"] = cache_stats["embedding_cache_misses"]
        stats["embed_cache_size"] = cache_stats["embedding_cache_size"]

        # Normalisation map size
        from candlekeep.rag.token_normalisation import get_normalisation_map
        norm_map = get_normalisation_map(self.settings.data_dir)
        stats["normalisation_map_size"] = norm_map.size if norm_map is not None else 0

        return stats


    def get_by_entity(self, entity: str, n_results: int = 10) -> list[SearchResult]:
        """Search documents containing an entity."""
        results = self._get(where_document={"$contains": entity}, limit=n_results)
        if not results["ids"]:
            return []

        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_chunks_by_source(self, source: str) -> list[SearchResult]:
        """Get all chunks from a specific source document."""
        results = self._get(where={"source": source})
        if not results["ids"]:
            return []

        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_all_chunks(self) -> list[SearchResult]:
        """Get all chunks from the database."""
        results = self._get()
        if not results["ids"]:
            return []

        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for a list of texts."""
        if not texts:
            return []
        embeddings = self.embedder.embed(texts)
        if hasattr(embeddings, 'tolist'):
            return embeddings.tolist()
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Get cached embedding for a single query."""
        return self.embedder.embed_query(query)

    def get_stored_embeddings_by_source(self, source: str) -> dict[int, list[float]]:

        """Get stored embeddings for all chunks from a source document."""
        results = self._get(
            where={"source": source},
            include=["embeddings", "metadatas"]
        )
        if not results["ids"]:
            return {}

        embeddings_map = {}
        for meta, embedding in zip(results["metadatas"], results["embeddings"]):
            chunk_idx = meta.get("chunk_index", 0)
            embeddings_map[chunk_idx] = embedding
        return embeddings_map

    def remove_orphaned(self, existing_sources: set[str]) -> int:
        """Remove chunks whose source files no longer exist."""
        docs = self.list_documents()
        removed = 0
        for doc in docs:
            if doc["source"] not in existing_sources:
                removed += self.delete_by_source(doc["source"])
        return removed
