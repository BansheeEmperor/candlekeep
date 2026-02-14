"""ChromaDB vector store with authentication support."""
import hashlib
import json
import sys
from pathlib import Path
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


class ChromaVectorStore(VectorDatabase):
    """ChromaDB implementation with authentication."""
    
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.embedder = EmbeddingManager.get_instance(self.settings)
        
        # Setup auth headers
        headers = {}
        if self.settings.chroma_auth_token:
            headers["Authorization"] = f"Bearer {self.settings.chroma_auth_token}"
        
        # Connect to ChromaDB
        try:
            self.client = chromadb.HttpClient(
                host=self.settings.chroma_host,
                port=self.settings.chroma_port,
                headers=headers if headers else None,
                ssl=self.settings.chroma_ssl
            )
            self.collection = self.client.get_or_create_collection(
                name="candlekeep",
                metadata={"hnsw:space": "cosine", "embedding_model": self.settings.embedding_model}
            )
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

    def _generate_id(self, chunk: Chunk) -> str:
        """Generate unique ID for a chunk."""
        content = f"{chunk.metadata['source']}:{chunk.chunk_index}:{chunk.text[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add_documents(self, chunks: list[Chunk], collection: str = "default") -> int:
        """Add chunks to the vector store."""
        if not chunks:
            return 0

        # Invalidate hybrid search cache
        from candlekeep.rag.hybrid import clear_bm25_cache
        clear_bm25_cache()

        # Delete existing chunks from same sources
        sources = set(c.metadata["source"] for c in chunks)
        for source in sources:
            self.delete_by_source(source)

        ids = [self._generate_id(c) for c in chunks]
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        metadatas = [{**c.metadata, "collection": collection, "chunk_index": c.chunk_index} for c in chunks]

        self.collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        return len(chunks)

    def search(self, query: str, n_results: int = 5, category: str | None = None) -> list[SearchResult]:
        """Search for similar documents with metadata re-ranking."""
        embedding = self.embedder.embed_query(query)
        
        # Build where clause for category filtering
        where = {"category": category} if category else None
        
        # Fetch extra candidates for re-ranking
        results = self.collection.query(
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

        # Re-rank with metadata boosting
        query_terms = set(query.lower().split())
        for r in candidates:
            boost = 0
            
            # Title matching
            title = r.metadata.get("title", "").lower()
            title_matches = sum(1 for t in query_terms if t in title)
            if title_matches > 0:
                boost += min(title_matches * 0.1, 0.3)
            
            # Keyword matching
            keywords = r.metadata.get("keywords", "").lower()
            kw_matches = sum(1 for t in query_terms if t in keywords)
            boost += min(kw_matches * 0.05, 0.15)
            
            r.score += boost

        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:n_results]

    def delete_by_source(self, source: str) -> int:
        """Delete all chunks from a source file."""
        from candlekeep.rag.hybrid import clear_bm25_cache
        clear_bm25_cache()
        
        results = self.collection.get(where={"source": source})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])
        return 0

    def clear(self) -> None:
        """Clear all documents from the collection."""
        from candlekeep.rag.hybrid import clear_bm25_cache
        clear_bm25_cache()
        
        self.client.delete_collection("candlekeep")
        self.collection = self.client.get_or_create_collection(
            name="candlekeep", metadata={"hnsw:space": "cosine"}
        )

    def list_documents(self) -> list[dict]:
        """List all unique source documents."""
        results = self.collection.get()
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
        count = self.collection.count()
        docs = self.list_documents()
        
        # Calculate database size
        db_path = self.settings.chroma_dir
        try:
            total_size = sum(f.stat().st_size for f in db_path.rglob("*") if f.is_file())
        except (FileNotFoundError, OSError):
            total_size = 0
        
        # Estimate tokens
        all_docs = self.collection.get()
        total_chars = sum(len(doc) for doc in all_docs.get("documents", []))
        estimated_tokens = total_chars // 4
        
        tokens_per_query = (5 * self.settings.chunk_size) // 4
        
        metrics = self._load_metrics()
        tokens_saved = metrics.get("queries", 0) * (estimated_tokens - tokens_per_query)
        
        return {
            "total_chunks": count,
            "total_documents": len(docs),
            "database_size_bytes": total_size,
            "database_size_human": _human_readable_size(total_size),
            "total_characters": total_chars,
            "estimated_tokens": estimated_tokens,
            "tokens_per_query": tokens_per_query,
            "context_savings_ratio": estimated_tokens / tokens_per_query if tokens_per_query else 0,
            "total_queries": metrics.get("queries", 0),
            "tokens_saved": tokens_saved,
        }

    def _load_metrics(self) -> dict:
        """Load usage metrics from file."""
        metrics_file = self.settings.data_dir / "metrics.json"
        if metrics_file.exists():
            return json.loads(metrics_file.read_text())
        return {"queries": 0}

    def _save_metrics(self, metrics: dict):
        """Save usage metrics to file."""
        metrics_file = self.settings.data_dir / "metrics.json"
        metrics_file.write_text(json.dumps(metrics))

    def record_query(self):
        """Record a search query for metrics."""
        metrics = self._load_metrics()
        metrics["queries"] = metrics.get("queries", 0) + 1
        self._save_metrics(metrics)

    def get_by_entity(self, entity: str, n_results: int = 10) -> list[SearchResult]:
        """Search documents containing an entity."""
        results = self.collection.get(where_document={"$contains": entity}, limit=n_results)
        if not results["ids"]:
            return []

        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_chunks_by_source(self, source: str) -> list[SearchResult]:
        """Get all chunks from a specific source document."""
        results = self.collection.get(where={"source": source})
        if not results["ids"]:
            return []

        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_all_chunks(self) -> list[SearchResult]:
        """Get all chunks from the database."""
        results = self.collection.get()
        if not results["ids"]:
            return []

        return [
            SearchResult(text=doc, metadata=meta, score=1.0, doc_id=doc_id)
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def remove_orphaned(self, existing_sources: set[str]) -> int:
        """Remove chunks whose source files no longer exist."""
        docs = self.list_documents()
        removed = 0
        for doc in docs:
            if doc["source"] not in existing_sources:
                removed += self.delete_by_source(doc["source"])
        return removed
