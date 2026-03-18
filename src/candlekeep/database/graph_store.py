"""SQLite-backed entity co-occurrence graph store."""
import sqlite3
import threading
from pathlib import Path


class GraphStore:
    """Stores entity mentions and materializes co-occurrence with Jaccard similarity."""

    def __init__(self, db_path: Path | str):
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS entity_mentions (
                    entity TEXT NOT NULL,
                    source TEXT NOT NULL,
                    chunk_idx INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_entity ON entity_mentions(entity);
                CREATE INDEX IF NOT EXISTS idx_source ON entity_mentions(source);
                CREATE TABLE IF NOT EXISTS entity_cooccurrence (
                    entity_a TEXT NOT NULL,
                    entity_b TEXT NOT NULL,
                    cooccurrence_count INTEGER NOT NULL,
                    jaccard_similarity REAL NOT NULL,
                    PRIMARY KEY (entity_a, entity_b)
                );
                CREATE TABLE IF NOT EXISTS entity_ruler_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            self._conn.commit()

    def add_mentions(self, mentions: list[tuple[str, str, int]]):
        """Add entity mentions: list of (entity, source, chunk_idx)."""
        with self._lock:
            self._conn.executemany(
                "INSERT INTO entity_mentions (entity, source, chunk_idx) VALUES (?, ?, ?)",
                mentions,
            )
            self._conn.commit()

    def remove_by_source(self, source: str):
        with self._lock:
            self._conn.execute("DELETE FROM entity_mentions WHERE source = ?", (source,))
            self._conn.commit()

    def rebuild_cooccurrence(self):
        """Recompute entity_cooccurrence table from entity_mentions."""
        with self._lock:
            self._conn.execute("DELETE FROM entity_cooccurrence")
            # Compute pairwise co-occurrence counts and Jaccard similarity.
            # Jaccard(A,B) = |chunks(A) ∩ chunks(B)| / |chunks(A) ∪ chunks(B)|
            #              = cooccurrence_count / (|A| + |B| - cooccurrence_count)
            self._conn.execute("""
                INSERT INTO entity_cooccurrence (entity_a, entity_b, cooccurrence_count, jaccard_similarity)
                SELECT
                    a.entity,
                    b.entity,
                    COUNT(*) AS cooc,
                    CAST(COUNT(*) AS REAL) / (
                        (SELECT COUNT(DISTINCT source || '|' || CAST(chunk_idx AS TEXT))
                         FROM entity_mentions WHERE entity = a.entity)
                        + (SELECT COUNT(DISTINCT source || '|' || CAST(chunk_idx AS TEXT))
                           FROM entity_mentions WHERE entity = b.entity)
                        - COUNT(*)
                    )
                FROM entity_mentions a
                JOIN entity_mentions b
                    ON a.source = b.source AND a.chunk_idx = b.chunk_idx AND a.entity < b.entity
                GROUP BY a.entity, b.entity
                HAVING COUNT(*) >= 2
            """)
            self._conn.commit()

    def get_related(self, entity: str, top_n: int = 5) -> list[tuple[str, float]]:
        """Return top-N related entities by Jaccard similarity."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT entity_b AS other, jaccard_similarity FROM entity_cooccurrence
                WHERE entity_a = ?
                UNION ALL
                SELECT entity_a AS other, jaccard_similarity FROM entity_cooccurrence
                WHERE entity_b = ?
                ORDER BY jaccard_similarity DESC
                LIMIT ?
                """,
                (entity, entity, top_n),
            ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def get_stats(self) -> dict:
        with self._lock:
            entity_count = self._conn.execute(
                "SELECT COUNT(DISTINCT entity) FROM entity_mentions"
            ).fetchone()[0]
            edge_count = self._conn.execute(
                "SELECT COUNT(*) FROM entity_cooccurrence"
            ).fetchone()[0]
            vocab_size_row = self._conn.execute(
                "SELECT value FROM entity_ruler_meta WHERE key = 'vocab_size'"
            ).fetchone()
            vocab_size = int(vocab_size_row[0]) if vocab_size_row else 0
        return {
            "entity_count": entity_count,
            "cooccurrence_edge_count": edge_count,
            "entity_ruler_vocabulary_size": vocab_size,
        }

    def set_ruler_meta(self, vocab_size: int):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO entity_ruler_meta (key, value) VALUES ('vocab_size', ?)",
                (str(vocab_size),),
            )
            self._conn.commit()

    def clear(self):
        with self._lock:
            self._conn.executescript("""
                DELETE FROM entity_mentions;
                DELETE FROM entity_cooccurrence;
                DELETE FROM entity_ruler_meta;
            """)
            self._conn.commit()

    def close(self):
        self._conn.close()


# ── Background rebuild (mirrors token_normalisation pattern) ─────────────────

_rebuild_building = False
_rebuild_lock = threading.Lock()
_rebuild_thread: threading.Thread | None = None


def schedule_graph_rebuild(graph_store: GraphStore) -> None:
    """Fire-and-forget background co-occurrence rebuild. No-op if already running."""
    global _rebuild_building, _rebuild_thread
    with _rebuild_lock:
        if _rebuild_building:
            return
        _rebuild_building = True

    thread = threading.Thread(
        target=_rebuild_worker,
        args=(graph_store,),
        daemon=True,
        name="graph-cooccurrence-rebuild",
    )
    _rebuild_thread = thread
    thread.start()


def _join_rebuild_thread():
    """Join the rebuild thread at interpreter shutdown to avoid C++ abort."""
    if _rebuild_thread is not None and _rebuild_thread.is_alive():
        _rebuild_thread.join(timeout=5)


import atexit
atexit.register(_join_rebuild_thread)


def _rebuild_worker(graph_store: GraphStore) -> None:
    import logging
    global _rebuild_building
    try:
        graph_store.rebuild_cooccurrence()
        logging.getLogger("candlekeep").info(
            "[candlekeep] Graph co-occurrence rebuild complete"
        )
    except Exception:
        logging.getLogger("candlekeep").exception(
            "[candlekeep] Graph co-occurrence rebuild failed"
        )
    finally:
        with _rebuild_lock:
            _rebuild_building = False


# ── Singleton ─────────────────────────────────────────────────────────────────

_graph_store: GraphStore | None = None
_gs_lock = threading.Lock()


def get_graph_store(settings) -> GraphStore | None:
    """Return the GraphStore singleton, or None if disabled/unavailable."""
    import os
    if os.getenv("CANDLEKEEP_GRAPH_AUGMENT", "true").lower() == "false":
        return None

    global _graph_store
    with _gs_lock:
        if _graph_store is None:
            _graph_store = GraphStore(settings.graph_db_path)
    return _graph_store


def clear_graph_store_cache():
    global _graph_store
    with _gs_lock:
        _graph_store = None
