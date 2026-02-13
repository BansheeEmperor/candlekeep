"""Unit tests for the search router."""
from unittest.mock import MagicMock, patch
from candlekeep.database.interface import SearchResult
from candlekeep.rag.router import search_with_routing, MIN_RELEVANCE_SCORE


def _make_result(text="test", score=0.9, source="test.md", chunk_index=0):
    return SearchResult(
        text=text,
        score=score,
        metadata={"source": source, "filename": source, "chunk_index": chunk_index},
        doc_id="abc",
    )


class TestRouter:
    def test_simple_uses_arcane_recall(self):
        with patch("candlekeep.rag.arcane_recall.search_with_arcane_recall") as mock:
            mock.return_value = [_make_result()]
            results = search_with_routing(MagicMock(), "test query", query_type="simple")
            mock.assert_called_once()
            assert len(results) == 1

    def test_precise_uses_reranker(self):
        with patch("candlekeep.rag.arcane_recall.search_with_arcane_recall") as mock_ar, \
             patch("candlekeep.rag.reranker.rerank_results") as mock_rr:
            mock_ar.return_value = [_make_result(score=0.8)]
            mock_rr.return_value = [_make_result(score=2.5)]
            results = search_with_routing(MagicMock(), "test", query_type="precise")
            mock_ar.assert_called_once()
            mock_rr.assert_called_once()

    def test_relevance_threshold_filters_low_scores(self):
        with patch("candlekeep.rag.arcane_recall.search_with_arcane_recall") as mock:
            mock.return_value = [
                _make_result(text="good", score=0.9),
                _make_result(text="bad", score=0.3),
                _make_result(text="borderline", score=MIN_RELEVANCE_SCORE),
            ]
            results = search_with_routing(MagicMock(), "test", query_type="simple")
            assert len(results) == 2
            assert all(r.score >= MIN_RELEVANCE_SCORE for r in results)

    def test_relevance_threshold_skipped_for_precise(self):
        with patch("candlekeep.rag.arcane_recall.search_with_arcane_recall") as mock_ar, \
             patch("candlekeep.rag.reranker.rerank_results") as mock_rr:
            mock_ar.return_value = [_make_result()]
            mock_rr.return_value = [_make_result(score=-1.5)]
            results = search_with_routing(MagicMock(), "test", query_type="precise")
            assert len(results) == 1

    def test_negation_preprocessing(self):
        with patch("candlekeep.rag.arcane_recall.search_with_arcane_recall") as mock:
            mock.return_value = []
            search_with_routing(MagicMock(), "caching without Redis", query_type="simple")
            call_args = mock.call_args
            assert "Redis" not in call_args[0][1]

    def test_unknown_query_type_falls_back(self):
        with patch("candlekeep.rag.arcane_recall.search_with_arcane_recall") as mock:
            mock.return_value = [_make_result()]
            results = search_with_routing(MagicMock(), "test", query_type="unknown")
            mock.assert_called_once()

    def test_empty_results(self):
        with patch("candlekeep.rag.arcane_recall.search_with_arcane_recall") as mock:
            mock.return_value = []
            results = search_with_routing(MagicMock(), "nonsense", query_type="simple")
            assert results == []
