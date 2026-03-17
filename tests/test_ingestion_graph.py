"""Unit tests for entity extraction integration in ingestion pipeline."""
import pytest
from unittest.mock import MagicMock, patch
from candlekeep.database.interface import Chunk


def _make_chunk(text: str, source: str = "doc1", idx: int = 0) -> Chunk:
    return Chunk(text=text, metadata={"source": source, "filename": "doc1.md"}, chunk_index=idx)


@pytest.mark.unit
def test_add_documents_populates_entities_metadata(tmp_path):
    """Entities array should appear in ChromaDB metadata after add_documents."""
    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore

    settings = MagicMock(spec=Settings)
    settings.entity_ruler_path = tmp_path / "entity_ruler.jsonl"
    settings.graph_db_path = tmp_path / "graph.db"
    settings.embedding_model = "bge-small"
    settings.embedding_model_name = "BAAI/bge-small-en-v1.5"
    settings.embedding_cache_size = 10
    settings.device = "cpu"
    settings.chroma_dir = tmp_path / "chroma"

    store = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 384]
    embedder.embed_query.return_value = [0.1] * 384

    with patch("candlekeep.database.vector_store.ChromaVectorStore.__init__", return_value=None):
        vs = ChromaVectorStore.__new__(ChromaVectorStore)
        vs.settings = settings
        vs.embedder = embedder
        vs.collection = store

        store.get.return_value = {"ids": []}
        captured_metadatas = []

        def capture_upsert(**kwargs):
            captured_metadatas.extend(kwargs["metadatas"])

        store.upsert.side_effect = capture_upsert

        chunks = [_make_chunk("ArcaneRecall expands context with BM25Searcher")]
        vs.add_documents(chunks)

        assert captured_metadatas, "upsert was not called"
        meta = captured_metadatas[0]
        assert "entities" in meta
        assert "arcanerecall" in meta["entities"]
        assert "bm25searcher" in meta["entities"]


@pytest.mark.unit
def test_add_documents_no_entities_omits_key(tmp_path):
    """Chunks with no extractable entities should not have 'entities' key."""
    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore

    settings = MagicMock(spec=Settings)
    settings.entity_ruler_path = tmp_path / "entity_ruler.jsonl"
    settings.graph_db_path = tmp_path / "graph.db"
    settings.embedding_model = "bge-small"
    settings.embedding_model_name = "BAAI/bge-small-en-v1.5"
    settings.embedding_cache_size = 10
    settings.device = "cpu"
    settings.chroma_dir = tmp_path / "chroma"

    store = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 384]

    with patch("candlekeep.database.vector_store.ChromaVectorStore.__init__", return_value=None):
        vs = ChromaVectorStore.__new__(ChromaVectorStore)
        vs.settings = settings
        vs.embedder = embedder
        vs.collection = store
        store.get.return_value = {"ids": []}
        captured_metadatas = []
        store.upsert.side_effect = lambda **kw: captured_metadatas.extend(kw["metadatas"])

        chunks = [_make_chunk("the quick brown fox jumps over the lazy dog")]
        vs.add_documents(chunks)

        meta = captured_metadatas[0]
        # No technical entities — key should be absent (ChromaDB rejects empty arrays)
        assert meta.get("entities", None) != []


@pytest.mark.unit
def test_delete_by_source_removes_graph_mentions(tmp_path):
    """delete_by_source should call graph_store.remove_by_source."""
    from candlekeep.database.graph_store import GraphStore
    gs = GraphStore(tmp_path / "graph.db")
    gs.add_mentions([("arcanerecall", "doc1.md", 0), ("bm25searcher", "doc1.md", 0)])

    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore

    settings = MagicMock(spec=Settings)
    settings.graph_db_path = tmp_path / "graph.db"

    store = MagicMock()
    store.get.return_value = {"ids": ["abc123"]}

    with patch("candlekeep.database.vector_store.ChromaVectorStore.__init__", return_value=None), \
         patch("candlekeep.database.graph_store.get_graph_store", return_value=gs), \
         patch("candlekeep.rag.hybrid.remove_from_bm25_cache"):
        vs = ChromaVectorStore.__new__(ChromaVectorStore)
        vs.settings = settings
        vs.collection = store

        vs.delete_by_source("doc1.md")

    # Mentions should be gone
    import sqlite3
    conn = sqlite3.connect(tmp_path / "graph.db")
    count = conn.execute("SELECT COUNT(*) FROM entity_mentions WHERE source = 'doc1.md'").fetchone()[0]
    conn.close()
    assert count == 0
