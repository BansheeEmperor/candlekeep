"""Unit tests for document quality gate."""
import pytest
import tempfile
from pathlib import Path
from candlekeep.mcp.server import check_document_quality

pytestmark = [pytest.mark.unit]


def _write_temp(content: str, suffix=".md") -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


GOOD_DOC = """---
title: "Test Document"
description: "A test document for quality checks"
keywords: ["test", "quality"]
---

# Test Document

## Section One

This is a well-structured document with frontmatter, headers, and enough
content to pass the quality gate. It has multiple sections and paragraphs
to ensure the word count is above the minimum threshold of one hundred words.
We need to keep writing to make sure we have enough content here for the
quality check to pass without any issues at all. Adding more sentences to
reach the word count. Technical documentation should be thorough and cover
all the important details that a reader would need to understand the topic.

## Section Two

More content here to ensure we have enough words and structure. This section
covers additional details about the topic. Good documentation includes
examples, explanations, and references to related concepts. Each section
should be self-contained and provide value to the reader on its own.
"""

NO_FRONTMATTER = """# No Frontmatter

## Section One

This document has no YAML frontmatter at all but has enough words to pass
the length check. It should fail on the frontmatter requirement only.
We need enough words here to avoid the too-short check triggering as well.
"""

NO_HEADERS = """---
title: "No Headers"
description: "Missing markdown headers"
keywords: ["test"]
---

This document has frontmatter but no markdown headers at all. It is just
a flat block of text with no structure. Because it has frontmatter the
quality gate trusts it as curated content and allows it through.
"""

NO_HEADERS_NO_FRONTMATTER = """This document has no YAML frontmatter and no markdown headers at all.
It is just a flat block of text with no structure. The quality gate should
reject it because it has neither frontmatter nor headers to prove curation.
We need enough words here to avoid the too-short check triggering as well.
"""

TOO_SHORT = """---
title: "Short"
description: "Too short"
keywords: ["test"]
---

# Short

## Very Short

Too few words.
"""

UNCLOSED_CODE = """---
title: "Bad Code"
description: "Unclosed code block"
keywords: ["test"]
---

# Code Example

## The Problem

Here is some code that is never closed properly and has enough words to
pass the length check because we need over one hundred words total.

```python
def hello():
    print("this block is never closed")

## Another Section

More content to pad the word count above the minimum threshold needed.
"""


class TestQualityGate:
    def test_good_document_passes(self):
        path = _write_temp(GOOD_DOC)
        issues = check_document_quality(path)
        assert issues == []

    def test_missing_frontmatter_rejected(self):
        path = _write_temp(NO_FRONTMATTER)
        issues = check_document_quality(path)
        assert any("frontmatter" in i.lower() for i in issues)

    def test_missing_headers_rejected(self):
        """No frontmatter + no headers = rejected."""
        path = _write_temp(NO_HEADERS_NO_FRONTMATTER)
        issues = check_document_quality(path)
        assert any("header" in i.lower() or "structure" in i.lower() for i in issues)

    def test_frontmatter_no_headers_passes(self):
        """Frontmatter acts as proof of curation - headers not required."""
        path = _write_temp(NO_HEADERS)
        issues = check_document_quality(path)
        assert not any("header" in i.lower() or "structure" in i.lower() for i in issues)

    def test_too_short_rejected(self):
        path = _write_temp(TOO_SHORT)
        issues = check_document_quality(path)
        assert any("short" in i.lower() for i in issues)

    def test_unclosed_code_block_rejected(self):
        path = _write_temp(UNCLOSED_CODE)
        issues = check_document_quality(path)
        assert any("code block" in i.lower() for i in issues)

    def test_multiple_issues_reported(self):
        path = _write_temp("Just a tiny file.")
        issues = check_document_quality(path)
        assert len(issues) >= 2  # frontmatter + headers + short


BODY = """
# Heading

## Section One

This document has enough words and structure to pass every other check of the
quality gate, so the frontmatter is the only thing under test here. It keeps
going for a while to clear the minimum word count without any trouble at all.
"""

INVALID_YAML = """---
title: Cloud Storage Options: Object, Block, and File
description: An unquoted colon in the title breaks the YAML mapping.
---
""" + BODY

QUOTED_COLON = """---
title: "Cloud Storage Options: Object, Block, and File"
description: The same title, quoted.
---
""" + BODY

UNTERMINATED = """---
title: "Never closed"
description: The block has no closing line.
""" + BODY

NOT_A_MAPPING = """---
- just
- a list
---
""" + BODY


class TestFrontmatterParsing:
    """The gate must reject frontmatter the processor would silently drop."""

    def test_invalid_yaml_rejected(self):
        issues = check_document_quality(_write_temp(INVALID_YAML))
        assert any(i.startswith("Invalid YAML frontmatter at line 2") for i in issues), issues

    def test_quoted_colon_accepted_and_title_kept(self):
        from candlekeep.rag.processor import DocumentProcessor
        path = _write_temp(QUOTED_COLON)
        assert check_document_quality(path) == []
        meta, _ = DocumentProcessor()._parse_frontmatter(path.read_text())
        assert meta["title"] == "Cloud Storage Options: Object, Block, and File"

    def test_unterminated_frontmatter_rejected(self):
        issues = check_document_quality(_write_temp(UNTERMINATED))
        assert any("Unreadable YAML frontmatter" in i for i in issues), issues

    def test_non_mapping_frontmatter_rejected(self):
        issues = check_document_quality(_write_temp(NOT_A_MAPPING))
        assert any("not a mapping" in i for i in issues), issues

    def test_rejected_frontmatter_is_what_the_processor_drops(self):
        """Every case the gate flags is one where the processor keeps no metadata."""
        from candlekeep.rag.processor import DocumentProcessor
        for doc in (INVALID_YAML, UNTERMINATED):
            meta, body = DocumentProcessor()._parse_frontmatter(doc)
            assert meta == {} and body.startswith("---")


class TestDirectoryIngestGate:
    """ingest() on a directory skips files that fail the gate and lists them."""

    @staticmethod
    def _ingest(path):
        import sys
        from unittest.mock import MagicMock, patch
        import candlekeep.mcp.server  # noqa: F401
        mod = sys.modules["candlekeep.mcp.server"]
        store = MagicMock()
        store.add_documents.side_effect = lambda chunks, collection: len(chunks)
        with patch.object(mod, "_check_ready", return_value=None), \
             patch.object(mod, "get_store", return_value=store), \
             patch("candlekeep.rag.token_normalisation.schedule_background_rebuild"):
            return mod.ingest(str(path)), store

    def test_failing_files_skipped_and_listed(self, tmp_path):
        (tmp_path / "good.md").write_text(GOOD_DOC)
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "bad.md").write_text(INVALID_YAML)
        msg, store = self._ingest(tmp_path)
        assert msg.startswith("✓ Ingested")
        assert "Skipped 1 file(s)" in msg and "sub/bad.md: Invalid YAML frontmatter" in msg
        chunks = store.add_documents.call_args.args[0]
        assert {c.metadata["filename"] for c in chunks} == {"good.md"}

    def test_nothing_ingested_when_every_file_fails(self, tmp_path):
        (tmp_path / "bad.md").write_text(INVALID_YAML)
        (tmp_path / "short.md").write_text(TOO_SHORT)
        msg, store = self._ingest(tmp_path)
        assert msg.startswith("❌ Nothing ingested — 2 file(s) failed the quality gate")
        store.add_documents.assert_not_called()

    def test_single_file_still_rejected(self, tmp_path):
        bad = tmp_path / "bad.md"
        bad.write_text(INVALID_YAML)
        msg, store = self._ingest(bad)
        assert msg.startswith("❌ Document rejected") and "Invalid YAML frontmatter" in msg
        store.add_documents.assert_not_called()
