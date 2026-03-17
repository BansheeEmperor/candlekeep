"""Unit tests for entity normalization and GraphStore."""
import pytest
from candlekeep.rag.entity_normalise import normalise_entity
from candlekeep.database.graph_store import GraphStore


# ── normalise_entity ──────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("raw,expected", [
    ("EXPANSION_SIMILARITY_THRESHOLD", "expansionsimilaritythreshold"),
    ("ArcaneRecall",                   "arcanerecall"),
    ("bge-small-en-v1.5",             "bgesmallenV15".lower()),  # dots+hyphens stripped
    ("cross-encoder",                  "crossencoder"),
    ("BM25Searcher",                   "bm25searcher"),
    ("token_normalisation",            "tokennormalisation"),
    ("already",                        "already"),
])
def test_normalise_entity(raw, expected):
    assert normalise_entity(raw) == expected


# ── GraphStore ────────────────────────────────────────────────────────────────

@pytest.fixture
def gs(tmp_path):
    store = GraphStore(tmp_path / "test.db")
    yield store
    store.close()


@pytest.mark.unit
def test_add_and_get_related(gs):
    # chunk 0: entities A, B, C co-occur
    # chunk 1: entities A, B co-occur (but not C)
    gs.add_mentions([
        ("a", "doc1", 0), ("b", "doc1", 0), ("c", "doc1", 0),
        ("a", "doc1", 1), ("b", "doc1", 1),
    ])
    gs.rebuild_cooccurrence()

    related = dict(gs.get_related("a", top_n=10))
    # a-b: cooc=2, |a|=2, |b|=2 → jaccard = 2/(2+2-2) = 1.0
    assert "b" in related
    assert abs(related["b"] - 1.0) < 1e-6
    # a-c: cooc=1 → filtered (HAVING COUNT(*) >= 2)
    assert "c" not in related


@pytest.mark.unit
def test_jaccard_partial(gs):
    # a appears in chunks 0,1,2; b appears in chunks 0,1; co-occur in 0,1
    gs.add_mentions([
        ("a", "doc1", 0), ("b", "doc1", 0),
        ("a", "doc1", 1), ("b", "doc1", 1),
        ("a", "doc1", 2),
    ])
    gs.rebuild_cooccurrence()
    related = dict(gs.get_related("a"))
    # jaccard = 2 / (3 + 2 - 2) = 2/3
    assert abs(related["b"] - 2/3) < 1e-6


@pytest.mark.unit
def test_remove_by_source(gs):
    gs.add_mentions([
        ("a", "doc1", 0), ("b", "doc1", 0),
        ("a", "doc2", 0), ("b", "doc2", 0),
    ])
    gs.rebuild_cooccurrence()
    assert gs.get_related("a")  # has results

    gs.remove_by_source("doc1")
    gs.rebuild_cooccurrence()
    # Only doc2 remains: still 1 co-occurrence, filtered by HAVING >= 2
    assert gs.get_related("a") == []


@pytest.mark.unit
def test_clear(gs):
    gs.add_mentions([("a", "doc1", 0), ("b", "doc1", 0)])
    gs.rebuild_cooccurrence()
    gs.clear()
    stats = gs.get_stats()
    assert stats["entity_count"] == 0
    assert stats["cooccurrence_edge_count"] == 0


@pytest.mark.unit
def test_get_stats(gs):
    gs.add_mentions([
        ("a", "doc1", 0), ("b", "doc1", 0),
        ("a", "doc1", 1), ("b", "doc1", 1),
    ])
    gs.rebuild_cooccurrence()
    gs.set_ruler_meta(vocab_size=42)
    stats = gs.get_stats()
    assert stats["entity_count"] == 2
    assert stats["cooccurrence_edge_count"] == 1
    assert stats["entity_ruler_vocabulary_size"] == 42
