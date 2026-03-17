"""Unit tests for query-time graph augmentation."""
import os
import pytest
from unittest.mock import MagicMock, patch
from candlekeep.database.interface import SearchResult
from candlekeep.database.graph_store import GraphStore
from candlekeep.rag.graph_augment import get_graph_chunks


def _sr(text: str, doc_id: str = "id1", score: float = 0.5) -> SearchResult:
    return SearchResult(text=text, metadata={"source": "doc1"}, score=score, doc_id=doc_id)


@pytest.mark.unit
def test_get_graph_chunks_returns_related(tmp_path):
    """get_graph_chunks should return chunks for entities related to query entities."""
    gs = GraphStore(tmp_path / "graph.db")
    # arcanerecall and expansionsimilaritythreshold co-occur in 2 chunks
    gs.add_mentions([
        ("arcanerecall", "doc1", 0), ("expansionsimilaritythreshold", "doc1", 0),
        ("arcanerecall", "doc1", 1), ("expansionsimilaritythreshold", "doc1", 1),
    ])
    gs.rebuild_cooccurrence()

    db = MagicMock()
    db.settings = MagicMock()
    db.settings.entity_ruler_path = tmp_path / "entity_ruler.jsonl"
    db.collection.get.return_value = {
        "ids": ["chunk_abc"],
        "documents": ["ArcaneRecall expands context"],
        "metadatas": [{"source": "doc1"}],
    }

    # Query mentions ArcaneRecall → should find expansionsimilaritythreshold as related
    results = get_graph_chunks(db, gs, "how does ArcaneRecall work?", n_results=5)
    assert len(results) > 0
    assert db.collection.get.called


@pytest.mark.unit
def test_get_graph_chunks_empty_when_no_relations(tmp_path):
    gs = GraphStore(tmp_path / "graph.db")
    # No mentions at all
    db = MagicMock()
    db.settings = MagicMock()
    db.settings.entity_ruler_path = tmp_path / "entity_ruler.jsonl"

    results = get_graph_chunks(db, gs, "how does ArcaneRecall work?", n_results=5)
    assert results == []


@pytest.mark.unit
def test_hybrid_search_no_graph_signal():
    """hybrid_search should not include any graph signal (graph lives in explore)."""
    db = MagicMock()
    db.search.return_value = [_sr("vector result", "v1")]
    db.settings = MagicMock()

    graph_chunks_called = []

    with patch("candlekeep.rag.hybrid._get_sparse_results", return_value=[_sr("bm25 result", "b1")]), \
         patch("candlekeep.rag.arcane_recall.expand_results", side_effect=lambda db, r, **kw: r), \
         patch("candlekeep.rag.graph_augment.get_graph_chunks",
               side_effect=lambda *a, **kw: graph_chunks_called.append(1) or []):
        from candlekeep.rag.hybrid import hybrid_search
        results = hybrid_search(db, "test query", n_results=5)

    assert len(results) > 0
    assert not graph_chunks_called, "hybrid_search must not call graph_augment (graph lives in explore)"
