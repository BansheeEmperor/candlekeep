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
