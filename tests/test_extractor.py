"""Unit tests for entity extraction pipeline and bootstrap."""
import json
import pytest
from pathlib import Path

from candlekeep.rag.extractor import EntityExtractor, _tech_tokens
from candlekeep.rag.entity_bootstrap import bootstrap_entity_ruler
from candlekeep.database.interface import SearchResult


# ── Pattern matchers ──────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("text,expected_subset", [
    ("EXPANSION_SIMILARITY_THRESHOLD config",  ["EXPANSION_SIMILARITY_THRESHOLD"]),
    ("ArcaneRecall and BM25Searcher",           ["ArcaneRecall", "BM25Searcher"]),
    ("version v1.2.3 released",                ["v1.2.3"]),
    ("no technical tokens here",               []),
])
def test_tech_tokens(text, expected_subset):
    found = _tech_tokens(text)
    for expected in expected_subset:
        assert expected in found


# ── EntityExtractor ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_extract_returns_normalised(tmp_path):
    ex = EntityExtractor(ruler_path=None)
    # Should find SCREAMING_SNAKE and PascalCase via pattern layer
    results = ex.extract("Use CANDLEKEEP_GRAPH_AUGMENT to enable ArcaneRecall.")
    assert "candlekeepgraphaugment" in results
    assert "arcanerecall" in results


@pytest.mark.unit
def test_extract_deduplicates(tmp_path):
    ex = EntityExtractor(ruler_path=None)
    results = ex.extract("ArcaneRecall ArcaneRecall ArcaneRecall")
    assert results.count("arcanerecall") == 1


@pytest.mark.unit
def test_extract_with_ruler(tmp_path):
    ruler_path = tmp_path / "entity_ruler.jsonl"
    ruler_path.write_text(json.dumps({"label": "TECH", "pattern": "Candlekeep"}) + "\n")
    ex = EntityExtractor(ruler_path=ruler_path)
    results = ex.extract("Candlekeep is a RAG server.")
    assert "candlekeep" in results


# ── bootstrap_entity_ruler ────────────────────────────────────────────────────

@pytest.mark.unit
def test_bootstrap_ranks_by_doc_frequency(tmp_path):
    # "ArcaneRecall" appears in 3 docs, "BM25Searcher" in 1
    chunks = [
        SearchResult(text="ArcaneRecall expands context", metadata={"source": "doc1"}, score=1.0, doc_id="1"),
        SearchResult(text="ArcaneRecall is used here",   metadata={"source": "doc2"}, score=1.0, doc_id="2"),
        SearchResult(text="ArcaneRecall again",          metadata={"source": "doc3"}, score=1.0, doc_id="3"),
        SearchResult(text="BM25Searcher for lexical",    metadata={"source": "doc1"}, score=1.0, doc_id="4"),
    ]
    out = tmp_path / "entity_ruler.jsonl"
    count = bootstrap_entity_ruler(chunks, out)
    assert count >= 2

    patterns = [json.loads(l)["pattern"] for l in out.read_text().splitlines()]
    # ArcaneRecall (df=3) should rank above BM25Searcher (df=1)
    assert patterns.index("ArcaneRecall") < patterns.index("BM25Searcher")


@pytest.mark.unit
def test_bootstrap_writes_valid_jsonl(tmp_path):
    chunks = [
        SearchResult(text="ArcaneRecall test", metadata={"source": "doc1"}, score=1.0, doc_id="1"),
    ]
    out = tmp_path / "entity_ruler.jsonl"
    bootstrap_entity_ruler(chunks, out)
    for line in out.read_text().splitlines():
        obj = json.loads(line)
        assert "label" in obj and "pattern" in obj
