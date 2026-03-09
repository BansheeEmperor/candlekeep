"""Unit tests for Arcane Recall expand_results."""
import pytest
from unittest.mock import MagicMock
from candlekeep.database.interface import SearchResult
from candlekeep.rag.arcane_recall import expand_results

pytestmark = [pytest.mark.unit]


def _make_result(text, source="doc.md", chunk_index=0, score=0.9):
    return SearchResult(
        text=text, score=score,
        metadata={"source": source, "filename": source, "chunk_index": chunk_index},
        doc_id=f"{source}:{chunk_index}",
    )


def _mock_db(chunks_by_source):
    """Create a mock DB that returns chunks by source."""
    db = MagicMock()
    def get_chunks(source):
        return chunks_by_source.get(source, [])
    db.get_chunks_by_source = MagicMock(side_effect=get_chunks)
    return db


class TestExpandResults:
    def test_expands_with_adjacent_chunks(self):
        """Should include ±2 chunks around the matched chunk."""
        source_chunks = [_make_result(f"chunk{i}", chunk_index=i) for i in range(6)]
        db = _mock_db({"doc.md": source_chunks})

        results = [_make_result("chunk2", chunk_index=2)]
        expanded = expand_results(db, results, n_results=1, expansion_chunks=2)

        assert len(expanded) == 1
        # Should contain chunks 0,1,2,3,4 (±2 around index 2)
        assert "chunk0" in expanded[0].text
        assert "chunk4" in expanded[0].text

    def test_clamps_at_start(self):
        """Expansion at chunk 0 should not go negative."""
        source_chunks = [_make_result(f"chunk{i}", chunk_index=i) for i in range(5)]
        db = _mock_db({"doc.md": source_chunks})

        results = [_make_result("chunk0", chunk_index=0)]
        expanded = expand_results(db, results, n_results=1, expansion_chunks=2)

        assert "chunk0" in expanded[0].text
        assert "chunk2" in expanded[0].text

    def test_deduplicates_overlapping_expansions(self):
        """Two adjacent matches should not produce duplicate expanded text."""
        source_chunks = [_make_result(f"chunk{i}", chunk_index=i) for i in range(6)]
        db = _mock_db({"doc.md": source_chunks})

        results = [
            _make_result("chunk2", chunk_index=2),
            _make_result("chunk3", chunk_index=3),
        ]
        expanded = expand_results(db, results, n_results=5, expansion_chunks=2)

        texts = [r.text for r in expanded]
        assert len(texts) == len(set(texts))  # No duplicates

    def test_per_source_lookup(self):
        """Should call get_chunks_by_source per unique source, not full scan."""
        db = _mock_db({
            "a.md": [_make_result("a0", source="a.md", chunk_index=0)],
            "b.md": [_make_result("b0", source="b.md", chunk_index=0)],
        })

        results = [
            _make_result("a0", source="a.md", chunk_index=0),
            _make_result("b0", source="b.md", chunk_index=0),
        ]
        expand_results(db, results, n_results=2, expansion_chunks=2)

        assert db.get_chunks_by_source.call_count == 2

    def test_unknown_source_returns_empty_expansion(self):
        """Results from source with no chunks produce empty expanded text."""
        db = _mock_db({})
        results = [_make_result("orphan", source="missing.md")]
        expanded = expand_results(db, results, n_results=1)

        assert len(expanded) == 1
        assert expanded[0].text == ""  # No chunks found to expand

    def test_respects_n_results(self):
        """Should not return more than n_results across distinct windows."""
        source_chunks = [_make_result(f"chunk{i}", chunk_index=i) for i in range(100)]
        db = _mock_db({"doc.md": source_chunks})

        # Request 3 non-adjacent chunks far apart so they don't merge
        results = [
            _make_result("chunk0", chunk_index=0),
            _make_result("chunk50", chunk_index=50),
            _make_result("chunk90", chunk_index=90),
            _make_result("chunk99", chunk_index=99),
        ]
        expanded = expand_results(db, results, n_results=3, expansion_chunks=2)

        assert len(expanded) == 3

    def test_arcane_coalescence_merges_adjacent_matches(self):
        """Arcane Coalescence should merge adjacent/overlapping matches into one window."""
        source_chunks = [_make_result(f"chunk{i}", chunk_index=i) for i in range(10)]
        db = _mock_db({"doc.md": source_chunks})

        results = [
            _make_result("chunk2", chunk_index=2),
            _make_result("chunk3", chunk_index=3),
        ]
        # These are adjacent, so they should merge into a single Divine Window
        expanded = expand_results(db, results, n_results=5, expansion_chunks=2)

        assert len(expanded) == 1
        # Result should cover chunks 0 to 5 (±2 around 2 and 3)
        assert "chunk0" in expanded[0].text
        assert "chunk5" in expanded[0].text
        assert "chunk6" not in expanded[0].text
