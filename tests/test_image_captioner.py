"""Unit tests for ImageCaptioner — no live API calls."""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from candlekeep.config import Settings
from candlekeep.rag.image_captioner import ImageCaptioner, _image_dimensions

pytestmark = [pytest.mark.unit]

FIXTURES = Path(__file__).parent / "fixtures"
PNG_200 = FIXTURES / "test_image_200x200.png"
PNG_50 = FIXTURES / "test_image_50x50.png"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(tmp_path: Path, **kwargs) -> Settings:
    s = Settings.__new__(Settings)
    s.vlm_provider = "anthropic"
    s.vlm_concurrency = 2
    s.vlm_max_cost_per_doc = 0.0
    s.vlm_fetch_remote_images = False
    s.bardic_knowledge = False
    s.data_dir = tmp_path
    s.chunk_size = 512
    s.chunk_overlap = 50
    (tmp_path / "image_captions").mkdir()
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def _mock_provider(caption: str = "A diagram showing components.") -> MagicMock:
    p = MagicMock()
    p.name = "anthropic"
    p.caption.return_value = caption
    return p


def _make_md(tmp_path: Path, img_rel: str) -> Path:
    """Write a markdown file referencing a local image."""
    md = tmp_path / "doc.md"
    md.write_text(f"---\ntitle: Test\n---\n\n## Section\n\n![diagram]({img_rel})\n")
    return md


# ---------------------------------------------------------------------------
# _image_dimensions
# ---------------------------------------------------------------------------

class TestImageDimensions:
    def test_png(self):
        data = PNG_200.read_bytes()
        w, h = _image_dimensions(data)
        assert w == 200 and h == 200

    def test_small_png(self):
        data = PNG_50.read_bytes()
        w, h = _image_dimensions(data)
        assert w == 50 and h == 50


# ---------------------------------------------------------------------------
# extract_images — markdown
# ---------------------------------------------------------------------------

class TestExtractMarkdownImages:
    def test_extracts_local_image(self, tmp_path):
        import shutil
        shutil.copy(PNG_200, tmp_path / "arch.png")
        md = _make_md(tmp_path, "arch.png")
        s = _settings(tmp_path)
        captioner = ImageCaptioner(s, _mock_provider())
        images = captioner.extract_images(md)
        assert len(images) == 1
        assert images[0][1]["image_index"] == 0

    def test_skips_small_image(self, tmp_path):
        import shutil
        # Create a 40x40 image (below 50px threshold)
        import struct, zlib
        def make_png(w, h):
            def chunk(name, data):
                c = struct.pack(">I", len(data)) + name + data
                return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            row = b"\x00" + bytes([100, 150, 200]) * w
            idat = chunk(b"IDAT", zlib.compress(row * h))
            iend = chunk(b"IEND", b"")
            return sig + ihdr + idat + iend
        
        tiny_png = tmp_path / "icon.png"
        tiny_png.write_bytes(make_png(40, 40))
        md = _make_md(tmp_path, "icon.png")
        s = _settings(tmp_path)
        captioner = ImageCaptioner(s, _mock_provider())
        images = captioner.extract_images(md)
        assert images == []

    def test_skips_remote_by_default(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text("## S\n\n![x](https://example.com/img.png)\n")
        s = _settings(tmp_path)
        captioner = ImageCaptioner(s, _mock_provider())
        assert captioner.extract_images(md) == []

    def test_skips_missing_file(self, tmp_path):
        md = _make_md(tmp_path, "nonexistent.png")
        s = _settings(tmp_path)
        captioner = ImageCaptioner(s, _mock_provider())
        assert captioner.extract_images(md) == []

    def test_no_images_returns_empty(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text("## Section\n\nNo images here.\n")
        s = _settings(tmp_path)
        captioner = ImageCaptioner(s, _mock_provider())
        assert captioner.extract_images(md) == []


# ---------------------------------------------------------------------------
# caption_images — cache hit/miss
# ---------------------------------------------------------------------------

class TestCaptionImages:
    def test_cache_miss_calls_provider(self, tmp_path):
        import shutil
        shutil.copy(PNG_200, tmp_path / "arch.png")
        md = _make_md(tmp_path, "arch.png")
        s = _settings(tmp_path)
        provider = _mock_provider("Architecture diagram with Gateway and Worker nodes.")
        captioner = ImageCaptioner(s, provider)
        images = captioner.extract_images(md)
        chunks, captioned, from_cache = captioner.caption_images(md, images)
        assert captioned == 1
        assert from_cache == 0
        assert len(chunks) == 1
        assert "Architecture diagram" in chunks[0].text
        assert chunks[0].metadata["content_type"] == "image_caption"
        provider.caption.assert_called_once()

    def test_cache_hit_skips_provider(self, tmp_path):
        import shutil
        shutil.copy(PNG_200, tmp_path / "arch.png")
        md = _make_md(tmp_path, "arch.png")
        s = _settings(tmp_path)
        provider = _mock_provider("Cached caption.")
        captioner = ImageCaptioner(s, provider)
        images = captioner.extract_images(md)

        # First call — populates cache
        captioner.caption_images(md, images)
        provider.caption.reset_mock()

        # Second call — should hit cache
        chunks, captioned, from_cache = captioner.caption_images(md, images)
        assert captioned == 0
        assert from_cache == 1
        provider.caption.assert_not_called()

    def test_chunk_metadata(self, tmp_path):
        import shutil
        shutil.copy(PNG_200, tmp_path / "arch.png")
        md = _make_md(tmp_path, "arch.png")
        s = _settings(tmp_path)
        captioner = ImageCaptioner(s, _mock_provider("desc"))
        images = captioner.extract_images(md)
        chunks, _, _ = captioner.caption_images(md, images)
        meta = chunks[0].metadata
        assert meta["source"] == str(md)
        assert meta["content_type"] == "image_caption"
        assert "image_page" in meta
        assert "image_index" in meta

    def test_empty_images_returns_empty(self, tmp_path):
        s = _settings(tmp_path)
        captioner = ImageCaptioner(s, _mock_provider())
        md = tmp_path / "doc.md"
        md.write_text("## S\n")
        chunks, captioned, from_cache = captioner.caption_images(md, [])
        assert chunks == [] and captioned == 0 and from_cache == 0


# ---------------------------------------------------------------------------
# Cost circuit breaker
# ---------------------------------------------------------------------------

class TestCostCircuitBreaker:
    def test_stops_after_budget_exceeded(self, tmp_path):
        import shutil
        # Create 3 images
        for name in ("a.png", "b.png", "c.png"):
            shutil.copy(PNG_200, tmp_path / name)
        md = tmp_path / "doc.md"
        md.write_text(
            "## S\n\n![a](a.png)\n\n![b](b.png)\n\n![c](c.png)\n"
        )
        # Budget so tight that even 1 image exceeds it after captioning
        # _token_cost("anthropic", ~1000 tokens) ≈ $0.003 > $0.001
        s = _settings(tmp_path, vlm_max_cost_per_doc=0.001)
        call_count = 0

        def expensive_caption(image_bytes, *, prompt, max_tokens):
            nonlocal call_count
            call_count += 1
            return "x" * 2000  # ~500 words → high token count

        provider = MagicMock()
        provider.name = "anthropic"
        provider.caption.side_effect = expensive_caption

        captioner = ImageCaptioner(s, provider)
        images = captioner.extract_images(md)
        assert len(images) == 3
        chunks, captioned, from_cache = captioner.caption_images(md, images)
        # Should have stopped after budget exceeded — not all 3 captioned
        assert captioned < 3


# ---------------------------------------------------------------------------
# No-op when vlm_provider unset
# ---------------------------------------------------------------------------

class TestNoOpWithoutProvider:
    def test_processor_no_captioner_when_provider_unset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CANDLEKEEP_VLM_PROVIDER", "")
        from candlekeep.rag.processor import DocumentProcessor
        # Need a fresh Settings with no vlm_provider
        s = Settings.__new__(Settings)
        s.vlm_provider = ""
        s.vlm_concurrency = 3
        s.vlm_max_cost_per_doc = 0.0
        s.vlm_fetch_remote_images = False
        s.bardic_knowledge = False
        s.data_dir = tmp_path
        s.chunk_size = 512
        s.chunk_overlap = 50
        s.device = "cpu"
        s.embedding_model = "bge-small"
        s.embedding_cache_size = 10
        s.spice = False
        s.sparse_backend = "bm25"
        s.transport = "stdio"
        s.http_host = "127.0.0.1"
        s.http_port = 8111
        s.mcp_token = ""
        s.rate_limit_search = 30
        s.rate_limit_write = 5
        s.rate_limit_window = 60
        s.llm_provider = ""
        s.chroma_url = "http://localhost:8000"
        s.chroma_auth_token = ""

        proc = DocumentProcessor(s)
        assert proc._captioner is None

    def test_process_returns_only_text_chunks_without_provider(self, tmp_path):
        import shutil
        shutil.copy(PNG_200, tmp_path / "arch.png")
        md = tmp_path / "doc.md"
        md.write_text(
            "---\ntitle: T\ndescription: D\nkeywords:\n  - k\ncategory: c\ntags:\n  - t\n---\n\n"
            "## Section\n\nSome content.\n\n![arch](arch.png)\n"
        )
        s = _settings(tmp_path)
        s.vlm_provider = ""
        from candlekeep.rag.processor import DocumentProcessor
        proc = DocumentProcessor.__new__(DocumentProcessor)
        proc.settings = s
        proc._captioner = None  # explicitly no captioner

        result = proc.process(md)
        assert result.images_captioned == 0
        assert result.images_from_cache == 0
        assert all(c.metadata.get("content_type") != "image_caption" for c in result.chunks)
