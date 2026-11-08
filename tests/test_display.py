"""Unit tests for the answer-focused search display (rag/display.py) and the document span
Arcane Recall passes to it."""
import re

import pytest
from unittest.mock import MagicMock

from candlekeep.database.interface import SearchResult
from candlekeep.rag import display
from candlekeep.rag.arcane_recall import expand_results

pytestmark = [pytest.mark.unit]

PREFIX = "Document: Guide. Description: A guide.\n\n"


def _result(doc_text, window, match_at=0, source="guide.md", title="Guide", score=0.5):
    """A SearchResult as Arcane Recall builds it: window = (start, end) in doc_text."""
    a, b = window
    text = PREFIX + doc_text[a:b]
    return SearchResult(text=text, score=score, doc_id=source,
                        metadata={"source": f"/docs/{source}", "filename": source, "title": title,
                                  "_match_offset": len(PREFIX) + match_at, "_prefix_len": len(PREFIX),
                                  "_doc_text": doc_text, "_doc_span": (a, b)})


def _bodies(out):
    """The displayed text of each block (between the fences)."""
    return [m.group(1) for m in re.finditer(r"```\n(.*?)\n```\n", out, re.S)]


def _doc(n_sections=12):
    parts = ["# Guide\n\nThe guide opens with an overview of what it covers."]
    for i in range(n_sections):
        parts.append(f"## Section {i}\n\nParagraph {i} talks about topic{i} in some detail. " + "filler words " * 30)
    return "\n\n".join(parts)


class TestBudget:
    @pytest.mark.parametrize("budget", [300, 800, 2000, 4000, 6000])
    def test_displayed_text_stays_within_the_budget(self, budget):
        doc = _doc()
        results = [_result(doc, (0, len(doc)), match_at=400, score=0.9),
                   _result(_doc(5), (0, 900), source="other.md", title="Other", score=0.4),
                   _result(_doc(5), (0, 900), source="third.md", title="Third", score=0.3)]
        out = display.render_results("topic7 details", results, budget)
        assert sum(len(b) for b in _bodies(out)) <= budget

    def test_empty_results_render_nothing(self):
        assert display.render_results("q", [], 4000) == ""


class TestSelection:
    def test_top_result_matched_chunk_is_always_shown(self):
        doc = _doc()
        m = doc.index("Paragraph 9")
        r = _result(doc, (m - 200, m + 600), match_at=200, score=0.9)
        out = display.render_results("overview", [r], 1500)
        assert doc[m:m + 300] in out

    def test_top_document_shows_matching_text_outside_its_window(self):
        doc = _doc()
        m = doc.index("Paragraph 9")
        window = (m - 50, m + 400)            # the answer to "topic3" lies far before the window
        r = _result(doc, window, match_at=50, score=0.9)
        out = display.render_results("topic3", [r], 2000)
        assert "Paragraph 3 talks about topic3" in out

    def test_other_documents_get_short_teasers(self):
        doc = _doc()
        top = _result(doc, (0, len(doc)), score=0.9)
        others = [_result(_doc(6), (0, 1500), source=f"o{i}.md", title=f"O{i}", score=0.1) for i in range(3)]
        out = display.render_results("topic2", [top] + others, 4000)
        bodies = _bodies(out)
        assert len(bodies) == 4
        assert len(bodies[0]) > 3000 and all(100 <= len(b) < len(bodies[0]) / 3 for b in bodies[1:])

    def test_results_of_one_document_are_shown_once(self):
        doc = _doc()
        a = _result(doc, (0, 800), score=0.9)
        b = _result(doc, (2000, 2800), match_at=0, score=0.8)
        out = display.render_results("topic5", [a, b], 4000)
        assert out.count("Source: guide.md") == 1

    def test_falls_back_to_the_window_when_it_does_not_match_the_document(self):
        doc = _doc()
        r = _result(doc, (0, 900), score=0.9)
        r.metadata["_doc_span"] = (100, 1000)          # not where the window body is
        out = display.render_results("topic8", [r], 4000)
        assert "topic8" not in out and len(_bodies(out)[0]) <= 900 + len("Document: Guide\n\n")

    def test_without_document_text_the_window_is_used(self):
        r = SearchResult(text="Document: T.\n\nplain window text about apples", score=0.3, doc_id="d",
                         metadata={"filename": "d.md", "_match_offset": 14})
        out = display.render_results("apples", [r], 4000)
        assert "plain window text about apples" in out

    def test_is_deterministic(self):
        doc = _doc()
        rs = [_result(doc, (0, 1200), score=0.9), _result(_doc(4), (0, 700), source="b.md", title="B", score=0.2)]
        assert display.render_results("topic1 topic2", rs, 3000) == display.render_results("topic1 topic2", rs, 3000)


class TestDocumentSpan:
    """Arcane Recall passes the stitched document and each window's span in it."""

    META = {"source": "doc.md", "filename": "doc.md", "title": "Setup Guide", "description": "How setup works"}
    HEAD = "Document: Setup Guide. Description: How setup works.\n\n"

    def _db(self, bodies):
        chunks = [SearchResult(text=self.HEAD + b, score=1.0, doc_id=f"doc.md:{i}", metadata={**self.META, "chunk_index": i})
                  for i, b in enumerate(bodies)]
        db = MagicMock()
        db.get_chunks_by_source = MagicMock(side_effect=lambda s: chunks if s == "doc.md" else [])
        return db, chunks

    def test_window_body_is_its_span_of_the_document(self):
        shared = "the shared overlap region of chunk text"
        bodies = ["intro " + shared, shared + " second part", "third chunk", "fourth chunk", "fifth chunk"]
        db, chunks = self._db(bodies)
        r = expand_results(db, [chunks[3]], n_results=1, expansion_chunks=1)[0]
        a, b = r.metadata["_doc_span"]
        assert r.text[r.metadata["_prefix_len"]:] == r.metadata["_doc_text"][a:b]
        assert r.metadata["_doc_text"].startswith("intro " + shared + " second part")
        assert r.metadata["_doc_text"].count(shared) == 1

    def test_prefix_length_is_the_header(self):
        db, chunks = self._db(["one", "two", "three"])
        r = expand_results(db, [chunks[1]], n_results=1, expansion_chunks=1)[0]
        assert r.text[:r.metadata["_prefix_len"]] == self.HEAD


class TestServerBudget:
    @pytest.mark.parametrize("n, budget", [(1, 4000), (5, 4000), (10, 8000), (20, 16000)])
    def test_budget_grows_with_the_number_of_results(self, monkeypatch, n, budget):
        from candlekeep.mcp import server
        monkeypatch.setattr(server._settings, "result_budget", 4000)
        assert server._display_budget(n) == budget


def _long_doc():
    """A document whose sections cover distinct topics, with code, a table and a list."""
    parts = ["# Handbook\n\nThe handbook covers several unrelated subjects in turn."]
    for i in range(10):
        parts.append(f"## Topic {i}\n\nThis section discusses subject{i} in general terms. " + "padding words " * 40)
    parts.append("## Rotation\n\nTo rotate the zebracrypt keys, run the rotation job weekly.")
    parts.append("```python\nrotate_keys(zebracrypt=True)\n```")
    parts.append("| Setting | Value |\n|---|---|\n| interval | weekly |")
    parts.append("- first step\n- second step\n- third step")
    return "\n\n".join(parts)


class TestQueryWords:
    def test_the_passage_with_the_query_words_is_chosen_far_outside_the_window(self):
        doc = _long_doc()
        r = _result(doc, (0, 900), score=0.9)
        out = display.render_results("how do I rotate zebracrypt keys", [r], 2000)
        assert "To rotate the zebracrypt keys" in out

    def test_an_unrelated_query_does_not_pull_that_passage(self):
        doc = _long_doc()
        r = _result(doc, (0, 900), score=0.9)
        out = display.render_results("subject2 general terms", [r], 1500)
        assert "zebracrypt" not in out


class TestSegments:
    def test_code_tables_and_list_items_are_their_own_passages(self):
        kinds = {k for _a, _b, k in display.segment(_long_doc(), 0)}
        assert {"heading", "para", "code", "table", "list"} <= kinds

    def test_a_fenced_block_stays_whole(self):
        doc = _long_doc()
        code = [(a, b) for a, b, k in display.segment(doc, 0) if k == "code"]
        assert len(code) == 1 and doc[code[0][0]:code[0][1]] == "```python\nrotate_keys(zebracrypt=True)\n```"

    def test_a_gap_is_marked_and_section_headings_come_with_their_passages(self):
        doc = _long_doc()
        r = _result(doc, (0, 900), score=0.9)
        out = display.render_results("zebracrypt keys rotation", [r], 1200)
        assert "\n[…]\n" in out and "## Rotation" in out


class TestServerWiring:
    def _results(self):
        doc = _doc()
        return [_result(doc, (0, len(doc)), match_at=300, score=0.9),
                _result(_doc(6), (0, 1500), source="b.md", title="B", score=0.5)]

    def test_window_mode_is_the_per_result_view(self, monkeypatch):
        from candlekeep.mcp import server
        monkeypatch.setattr(server._settings, "result_display", "window")
        rs = self._results()
        assert server._render_results("q", rs, 5) == "\n".join(server._format_result(r, server._settings.result_chars) for r in rs)

    @pytest.mark.parametrize("n, budget", [(5, 4000), (10, 8000)])
    def test_focused_mode_keeps_to_the_budget_for_n_results(self, monkeypatch, n, budget):
        from candlekeep.mcp import server
        monkeypatch.setattr(server._settings, "result_display", "focused")
        monkeypatch.setattr(server._settings, "result_budget", 4000)
        rs = self._results() * 1
        out = server._render_results("topic3", rs, n)
        assert sum(len(b) for b in _bodies(out)) <= budget
        assert out == display.render_results("topic3", rs, budget, server._settings.result_min_relevance,
                                             server._settings.result_relevance_gap)

    def test_relevance_floors_come_from_the_settings(self, monkeypatch):
        from candlekeep.mcp import server
        monkeypatch.setattr(server._settings, "result_display", "focused")
        monkeypatch.setattr(server._settings, "result_min_relevance", 0.5)
        monkeypatch.setattr(server._settings, "result_relevance_gap", None)
        rs = self._results()
        rs[0].metadata["_doc_relevance"], rs[1].metadata["_doc_relevance"] = 0.9, 0.3
        assert "Source: b.md" not in server._render_results("topic3", rs, 5)


def _scored(relevances, n_sections=6):
    """One result per document, in rank order, with the given relevance scores."""
    out = []
    for i, rel in enumerate(relevances):
        doc = _doc(n_sections)
        r = _result(doc, (0, len(doc)), source=f"d{i}.md", title=f"D{i}", score=1.0 - i / 10)
        r.metadata["_doc_relevance"] = rel
        out.append(r)
    return out


class TestFreynanMirror:
    def _shown(self, out):
        return dict(zip(re.findall(r"Source: (\S+)", out), (len(b) for b in _bodies(out))))

    def test_documents_below_the_relative_floor_get_nothing(self):
        out = display.render_results("topic2", _scored([0.90, 0.88, 0.70]), 4000, None, 0.15)
        assert set(self._shown(out)) == {"d0.md", "d1.md"}

    def test_documents_below_the_absolute_floor_get_nothing(self):
        out = display.render_results("topic2", _scored([0.90, 0.80, 0.55]), 4000, 0.60, None)
        assert "d2.md" not in self._shown(out)

    def test_documents_of_almost_equal_relevance_get_almost_equal_shares(self):
        shown = self._shown(display.render_results("topic2", _scored([0.900, 0.899], 20), 4000, None, 0.15))
        assert abs(shown["d0.md"] - shown["d1.md"]) < 0.15 * 4000

    def test_rank_order_split_without_relevance_scores(self):
        rs = _scored([0.90, 0.899], 20)
        del rs[1].metadata["_doc_relevance"]
        shown = self._shown(display.render_results("topic2", rs, 4000, None, 0.15))
        assert shown["d0.md"] > 3 * shown["d1.md"]

    def test_only_the_matched_chunk_when_nothing_reaches_the_absolute_floor(self):
        rs = _scored([0.50, 0.45])
        doc = rs[0].metadata["_doc_text"]
        out = display.render_results("topic2", rs, 4000, 0.60, 0.15)
        assert list(self._shown(out)) == ["d0.md"]
        assert _bodies(out)[0] == "Document: D0\n\n" + doc[:display.MUST]

    def test_floors_off_keep_every_document(self):
        out = display.render_results("topic2", _scored([0.90, 0.60, 0.30]), 4000, None, None)
        assert len(self._shown(out)) == 3

    def test_stays_within_the_budget(self):
        out = display.render_results("topic2", _scored([0.9, 0.89, 0.88, 0.87]), 3000, 0.6, 0.15)
        assert sum(len(b) for b in _bodies(out)) <= 3000


class TestDocumentRelevance:
    def test_arcane_recall_passes_the_best_chunk_cosine(self):
        meta = {"source": "doc.md", "filename": "doc.md", "title": "T"}
        chunks = [SearchResult(text=f"Document: T.\n\nchunk {i}", score=1.0, doc_id=f"doc.md:{i}",
                               metadata={**meta, "chunk_index": i}) for i in range(3)]
        db = MagicMock()
        db.get_chunks_by_source = MagicMock(return_value=chunks)
        db.get_stored_embeddings_by_source = MagicMock(return_value={0: [1.0, 0.0], 1: [0.6, 0.8], 2: [0.0, 1.0]})
        db.embed_query = MagicMock(return_value=[0.0, 2.0])
        r = expand_results(db, [chunks[0]], n_results=1, expansion_chunks=1, query="q")[0]
        assert r.metadata["_doc_relevance"] == pytest.approx(1.0)

    def test_no_relevance_without_a_query(self):
        meta = {"source": "doc.md", "filename": "doc.md", "title": "T"}
        chunks = [SearchResult(text="Document: T.\n\nchunk", score=1.0, doc_id="doc.md:0", metadata={**meta, "chunk_index": 0})]
        db = MagicMock()
        db.get_chunks_by_source = MagicMock(return_value=chunks)
        r = expand_results(db, chunks, n_results=1)[0]
        assert "_doc_relevance" not in r.metadata


class TestSettings:
    @pytest.mark.parametrize("value, expected", [("0.6", 0.6), ("off", None), ("", None), ("None", None)])
    def test_relevance_floor_can_be_disabled(self, monkeypatch, value, expected):
        from candlekeep.config import _optional_float
        monkeypatch.setenv("CANDLEKEEP_RESULT_MIN_RELEVANCE", value)
        assert _optional_float("CANDLEKEEP_RESULT_MIN_RELEVANCE", "0.60") == expected
