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
