"""Unit tests for explore_entity MCP tool and get_stats graph section."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_explore_entity_returns_related(tmp_path):
    from candlekeep.database.graph_store import GraphStore
    gs = GraphStore(tmp_path / "graph.db")
    gs.add_mentions([
        ("arcanerecall", "doc1", 0), ("bm25searcher", "doc1", 0),
        ("arcanerecall", "doc1", 1), ("bm25searcher", "doc1", 1),
    ])
    gs.rebuild_cooccurrence()

    mock_collection = MagicMock()
    mock_collection.get.return_value = {
        "ids": ["c1"],
        "documents": ["ArcaneRecall expands context"],
        "metadatas": [{"source": "doc1.md", "filename": "doc1.md"}],
    }

    with patch("candlekeep.mcp.server._check_ready", return_value=None), \
         patch("candlekeep.database.graph_store.get_graph_store", return_value=gs), \
         patch("candlekeep.mcp.server.get_store") as mock_store:
        mock_store.return_value.collection = mock_collection
        from candlekeep.mcp.server import _explore_entity_impl
        result = _explore_entity_impl("ArcaneRecall")

    assert "bm25searcher" in result
    assert "Jaccard" in result
    assert "doc1.md" in result


@pytest.mark.unit
def test_explore_entity_no_graph(tmp_path):
    with patch("candlekeep.mcp.server._check_ready", return_value=None), \
         patch("candlekeep.database.graph_store.get_graph_store", return_value=None):
        from candlekeep.mcp.server import _explore_entity_impl
        result = _explore_entity_impl("ArcaneRecall")

    assert "disabled" in result.lower() or "not yet built" in result.lower()


@pytest.mark.unit
def test_get_stats_includes_graph_section(tmp_path):
    from candlekeep.database.graph_store import GraphStore
    gs = GraphStore(tmp_path / "graph.db")
    gs.add_mentions([
        ("arcanerecall", "doc1", 0), ("bm25searcher", "doc1", 0),
        ("arcanerecall", "doc1", 1), ("bm25searcher", "doc1", 1),
    ])
    gs.rebuild_cooccurrence()
    gs.set_ruler_meta(vocab_size=42)

    mock_stats = {
        "total_chunks": 10, "total_documents": 2, "database_size_human": "1 KB",
        "total_characters": 1000, "estimated_tokens": 250, "tokens_per_query": 50,
        "context_savings_ratio": 5.0, "embed_cache_hits": 0, "embed_cache_misses": 0,
        "embed_cache_size": 0, "normalisation_map_size": 0,
    }

    with patch("candlekeep.mcp.server._check_ready", return_value=None), \
         patch("candlekeep.mcp.server.get_store") as mock_store, \
         patch("candlekeep.database.graph_store.get_graph_store", return_value=gs):
        mock_store.return_value.get_stats.return_value = mock_stats
        from candlekeep.mcp.server import get_stats
        result = get_stats.fn()

    assert "Entity Co-occurrence Graph" in result
    assert "2" in result   # entity_count
    assert "1" in result   # edge_count
    assert "42" in result  # vocab_size
