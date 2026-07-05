"""The Keeper's Chronicle: a separate collection for agent-recorded memories.

Unlike the main knowledge base (full documents, chunked and hybrid-searched),
the Chronicle holds short-form lessons an agent learns during work — failure
patterns, debugging tips, "where to look when X breaks". Entries live in their
own ChromaDB collection (``memory``) so they are isolated from the document
tomes and survive ``repopulate_database`` (which only clears ``candlekeep``).
"""
import hashlib
import threading
from dataclasses import dataclass, field

import chromadb

from candlekeep.database.embeddings import EmbeddingManager

# Dedicated ChromaDB collection name for memories.
COLLECTION_NAME = "memory"

# Relevance Ward for recall — cosine similarity below this is filtered out so
# the Chronicle returns nothing rather than irrelevant noise. Simpler than the
# main router's Ward (see rag/router.py) but serves the same purpose.
MIN_RELEVANCE_SCORE = 0.5

# ChromaDB's ``$contains`` only works on document text, not metadata, and
# metadata values must be scalars. So tags are stored two ways:
#   1. A comma-joined ``tags`` string for display/round-tripping.
#   2. One boolean key per tag (``tag:<name> = True``) so recall can filter
#      with exact-match ``$and`` clauses (whole-tag, no substring false hits).
_TAG_SEP = ","
_TAG_KEY_PREFIX = "tag:"


@dataclass
class ChronicleEntry:
    """A single recorded memory."""
    id: str
    text: str
    tags: list[str] = field(default_factory=list)
    category: str = ""
    author: str = ""
    created_at: str = ""
    score: float = 0.0  # populated only on recall


def _clean_tags(tags: list[str]) -> list[str]:
    """Strip blanks and whitespace from a tag list."""
    return [t.strip() for t in tags if t and t.strip()]


def _encode_tags(tags: list[str]) -> str:
    """Join tags into a display string."""
    clean = _clean_tags(tags)
    return _TAG_SEP.join(clean)


def _decode_tags(encoded: str) -> list[str]:
    """Reverse of :func:`_encode_tags`."""
    if not encoded:
        return []
    return [t for t in encoded.split(_TAG_SEP) if t]


class Chronicle:
    """ChromaDB-backed store for agent memories in a separate collection."""

    def __init__(self, client: chromadb.ClientAPI, embedder: EmbeddingManager):
        self._embedder = embedder
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

    def _generate_id(self, text: str, created_at: str) -> str:
        """Deterministic ID from content + timestamp."""
        content = f"{created_at}:{text[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def record(
        self,
        text: str,
        tags: list[str] | None = None,
        category: str = "",
        author: str = "",
        created_at: str = "",
    ) -> ChronicleEntry:
        """Record a new memory. Returns the created entry with its generated ID.

        ``created_at`` should be an ISO 8601 timestamp supplied by the caller
        (this module does not read the clock so it stays import-safe in tests).
        """
        tags = _clean_tags(tags or [])
        entry_id = self._generate_id(text, created_at)
        embedding = self._embedder.embed([text])[0]
        metadata = {
            "tags": _encode_tags(tags),
            "category": category,
            "author": author,
            "created_at": created_at,
        }
        # One boolean key per tag enables exact-match filtering on recall.
        for tag in tags:
            metadata[f"{_TAG_KEY_PREFIX}{tag}"] = True
        self._collection.upsert(
            ids=[entry_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        return ChronicleEntry(
            id=entry_id,
            text=text,
            tags=tags,
            category=category,
            author=author,
            created_at=created_at,
        )

    def recall(
        self,
        query: str,
        n_results: int = 5,
        tags: list[str] | None = None,
        category: str = "",
    ) -> list[ChronicleEntry]:
        """Recall memories semantically similar to ``query``.

        Optional ``tags`` (memory must contain ALL of them) and ``category``
        (exact match) narrow the results. Entries below the relevance Ward are
        filtered out.
        """
        if self._collection.count() == 0:
            return []

        where = self._build_where(tags, category)
        embedding = self._embedder.embed_query(query)
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where or None,
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        entries = []
        for entry_id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1 - dist  # cosine distance → similarity
            if score < MIN_RELEVANCE_SCORE:
                continue
            entries.append(self._to_entry(entry_id, doc, meta, score))
        return entries

    def entries(self, category: str = "", limit: int = 20) -> list[ChronicleEntry]:
        """List memories, newest first, optionally filtered by category."""
        where = {"category": category} if category else None
        results = self._collection.get(where=where)
        if not results["ids"]:
            return []

        items = [
            self._to_entry(entry_id, doc, meta, 0.0)
            for entry_id, doc, meta in zip(
                results["ids"], results["documents"], results["metadatas"]
            )
        ]
        # ChromaDB has no ORDER BY — sort in Python. Collection is small.
        items.sort(key=lambda e: e.created_at, reverse=True)
        return items[:limit]

    def strike(self, entry_id: str) -> bool:
        """Delete a memory by ID. Returns True if it existed."""
        existing = self._collection.get(ids=[entry_id])
        if not existing["ids"]:
            return False
        self._collection.delete(ids=[entry_id])
        return True

    def count(self) -> int:
        """Total number of recorded memories."""
        return self._collection.count()

    # -- internal helpers ----------------------------------------------------

    @staticmethod
    def _build_where(tags: list[str] | None, category: str) -> dict | None:
        """Build a ChromaDB where-clause for tag/category filtering."""
        clauses = []
        if category:
            clauses.append({"category": category})
        for tag in _clean_tags(tags or []):
            clauses.append({f"{_TAG_KEY_PREFIX}{tag}": True})
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    @staticmethod
    def _to_entry(entry_id: str, doc: str, meta: dict, score: float) -> ChronicleEntry:
        return ChronicleEntry(
            id=entry_id,
            text=doc,
            tags=_decode_tags(meta.get("tags", "")),
            category=meta.get("category", ""),
            author=meta.get("author", ""),
            created_at=meta.get("created_at", ""),
            score=score,
        )


# -- Singleton accessor (mirrors database/graph_store.get_graph_store) --------

_chronicle: Chronicle | None = None
_chronicle_lock = threading.Lock()


def get_chronicle(client: chromadb.ClientAPI, embedder: EmbeddingManager) -> Chronicle:
    """Return the Chronicle singleton, creating it on first use."""
    global _chronicle
    with _chronicle_lock:
        if _chronicle is None:
            _chronicle = Chronicle(client, embedder)
    return _chronicle


def clear_chronicle_cache():
    """Reset the singleton (used by tests)."""
    global _chronicle
    with _chronicle_lock:
        _chronicle = None
