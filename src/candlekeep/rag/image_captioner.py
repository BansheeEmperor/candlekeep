"""VLM-powered image captioner for PDF and markdown documents."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from candlekeep.config import Settings
    from candlekeep.providers.base import VisionProvider

from candlekeep.database.interface import Chunk

_CAPTION_PROMPT = (
    "You are extracting structured information from a technical diagram for a searchable knowledge base. "
    "List EVERY component name, port number, IP address, CIDR range, version number, count, percentage, "
    "timeout value, memory size, and other specific technical values visible in the diagram. "
    "Format: 'Component X has port Y', 'Node Z uses IP address W', 'Configuration A shows value B'. "
    "Be exhaustive — list every label, arrow, and value you can read."
)

# Approximate cost per token (input+output blended) by provider model prefix.
# Used only for the post-call cost log — not for pre-call estimation.
_COST_PER_TOKEN: dict[str, float] = {
    "claude": 3e-6,   # ~$3/M tokens (Sonnet-class)
    "gpt-4o": 5e-6,   # ~$5/M tokens
    "gpt-4": 5e-6,
}


def _token_cost(provider_name: str, tokens: int) -> float:
    for prefix, rate in _COST_PER_TOKEN.items():
        if prefix in provider_name.lower():
            return tokens * rate
    return tokens * 3e-6  # conservative default


class ImageCaptioner:
    def __init__(self, settings: "Settings", provider: "VisionProvider") -> None:
        self._settings = settings
        self._provider = provider

    # ------------------------------------------------------------------
    # Image extraction
    # ------------------------------------------------------------------

    def extract_images(self, path: Path) -> list[tuple[bytes, dict]]:
        """Return list of (image_bytes, meta) for images in *path*, filtered to >=100x100."""
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_images(path)
        if suffix in (".md", ".html", ".htm"):
            return self._extract_md_images(path)
        return []

    def _extract_pdf_images(self, path: Path) -> list[tuple[bytes, dict]]:
        """Render figure-bearing pages as full-page images.

        Detects figure pages via two signals:
        - Embedded raster images (photos, matplotlib PNGs)
        - Significant vector graphics (TikZ/PGF architecture diagrams)

        Capped at settings.vlm_pdf_max_pages per document to bound cost.
        """
        try:
            import fitz  # pymupdf
        except ImportError:
            return []

        max_pages = getattr(self._settings, "vlm_pdf_max_pages", 15)
        results = []
        doc = fitz.open(str(path))

        for page_num, page in enumerate(doc):
            if len(results) >= max_pages:
                break

            has_raster = bool(page.get_images(full=False))

            # Detect vector graphics: count path drawing commands.
            # A page with >20 distinct paths is likely a diagram page.
            has_vector = False
            if not has_raster:
                try:
                    drawings = page.get_drawings()
                    has_vector = len(drawings) > 20
                except Exception:
                    pass

            if not (has_raster or has_vector):
                continue

            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            results.append((
                pix.tobytes("png"),
                {"image_page": page_num, "image_index": 0},
            ))

        doc.close()
        return results

    _MD_IMG_RE = re.compile(r"!\[.*?\]\((.+?)\)")

    def _extract_md_images(self, path: Path) -> list[tuple[bytes, dict]]:
        text = path.read_text(encoding="utf-8", errors="replace")
        results = []
        for idx, m in enumerate(self._MD_IMG_RE.finditer(text)):
            src = m.group(1).strip()
            is_remote = src.startswith("http://") or src.startswith("https://")
            if is_remote:
                if not self._settings.vlm_fetch_remote_images:
                    continue
                try:
                    import urllib.request
                    with urllib.request.urlopen(src, timeout=10) as r:
                        data = r.read()
                except Exception:
                    continue
            else:
                img_path = (path.parent / src).resolve()
                if not img_path.exists():
                    continue
                data = img_path.read_bytes()
            # Check dimensions — use 50px threshold for explicitly referenced markdown images
            # (unlike PDF embedded images, these are intentional diagram references)
            w, h = _image_dimensions(data)
            if w < 50 or h < 50:
                continue
            results.append((data, {"image_page": 0, "image_index": idx}))
        return results

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _cache_path(self, image_bytes: bytes) -> Path:
        digest = hashlib.sha256(image_bytes).hexdigest()
        return self._settings.image_caption_cache_dir / f"{digest}.json"

    # ------------------------------------------------------------------
    # Captioning
    # ------------------------------------------------------------------

    def caption_images(
        self,
        path: Path,
        images: list[tuple[bytes, dict]],
        base_chunk_index: int = 0,
        title: str = "",
        description: str = "",
    ) -> tuple[list[Chunk], int, int]:
        """Caption *images* and return (chunks, captioned, from_cache)."""
        if not images:
            return [], 0, 0
        return asyncio.run(self._caption_async(path, images, base_chunk_index, title, description))

    async def _caption_async(
        self,
        path: Path,
        images: list[tuple[bytes, dict]],
        base_chunk_index: int,
        title: str = "",
        description: str = "",
    ) -> tuple[list[Chunk], int, int]:
        sem = asyncio.Semaphore(self._settings.vlm_concurrency)
        chunks: list[Chunk | None] = [None] * len(images)
        captioned = 0
        from_cache = 0
        total_cost = 0.0
        budget = self._settings.vlm_max_cost_per_doc  # 0.0 = unlimited

        # Build bardic prefix — use frontmatter title/description if available
        bardic_prefix = ""
        if self._settings.bardic_knowledge:
            parts = []
            if title:
                parts.append(f"Document: {title}")
            if description:
                parts.append(f"Description: {description}")
            bardic_prefix = (". ".join(parts) + ".\n\n") if parts else f"Document: {path.name}.\n\n"

        # Separate cache hits from misses
        tasks = []
        for i, (img_bytes, meta) in enumerate(images):
            cp = self._cache_path(img_bytes)
            if cp.exists():
                caption = json.loads(cp.read_text())["caption"]
                chunks[i] = _make_chunk(caption, meta, path, base_chunk_index + i, bardic_prefix)
                from_cache += 1
            else:
                tasks.append((i, img_bytes, meta, cp))

        async def _do_caption(i: int, img_bytes: bytes, meta: dict, cp: Path) -> None:
            nonlocal captioned, total_cost
            async with sem:
                try:
                    caption, tokens = await asyncio.to_thread(
                        _call_provider, self._provider, img_bytes
                    )
                except Exception as exc:
                    print(f"[candlekeep] ⚠ VLM caption failed: {exc}", file=sys.stderr)
                    return
                cost = _token_cost(self._provider.name, tokens)
                total_cost += cost
                if budget > 0 and total_cost > budget:
                    print(
                        f"[candlekeep] ⚠ VLM cost circuit breaker: ${total_cost:.4f} > "
                        f"${budget:.4f} limit, skipping remaining images",
                        file=sys.stderr,
                    )
                    return
                cp.write_text(json.dumps({"caption": caption, "tokens": tokens}))
                chunks[i] = _make_chunk(caption, meta, path, base_chunk_index + i, bardic_prefix)
                captioned += 1

        await asyncio.gather(*[_do_caption(i, b, m, cp) for i, b, m, cp in tasks])

        result_chunks = [c for c in chunks if c is not None]
        total_images = captioned + from_cache
        if total_images:
            print(
                f"[candlekeep] Image captioning: {total_images} images "
                f"({from_cache} from cache), ~${total_cost:.4f} cost",
                file=sys.stderr,
            )
        return result_chunks, captioned, from_cache


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _call_provider(provider: "VisionProvider", image_bytes: bytes) -> tuple[str, int]:
    """Call provider.caption() and return (caption_text, approx_tokens)."""
    caption = provider.caption(image_bytes, prompt=_CAPTION_PROMPT, max_tokens=1024)
    # Approximate token count from caption length (no SDK token counts in base interface)
    tokens = len(caption.split()) * 4 // 3 + 500  # rough: output words + ~500 input
    return caption, tokens


def _make_chunk(caption: str, meta: dict, path: Path, chunk_index: int, bardic_prefix: str) -> Chunk:
    return Chunk(
        text=f"{bardic_prefix}{caption}" if bardic_prefix else caption,
        metadata={
            "source": str(path),
            "filename": path.name,
            "extension": path.suffix,
            "content_type": "image_caption",
            "image_page": meta["image_page"],
            "image_index": meta["image_index"],
        },
        chunk_index=chunk_index,
    )


def _image_dimensions(data: bytes) -> tuple[int, int]:
    """Return (width, height) from image bytes without PIL dependency."""
    # PNG: width at bytes 16-20, height at 20-24
    if data[:4] == b"\x89PNG":
        import struct
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    # JPEG: scan for SOF marker
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 8:
            if data[i] != 0xFF:
                break
            marker = data[i + 1]
            length = int.from_bytes(data[i + 2:i + 4], "big")
            if marker in (0xC0, 0xC1, 0xC2):
                h = int.from_bytes(data[i + 5:i + 7], "big")
                w = int.from_bytes(data[i + 7:i + 9], "big")
                return w, h
            i += 2 + length
    # Fallback: assume large enough
    return 200, 200
