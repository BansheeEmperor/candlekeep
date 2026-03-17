"""Document processor for multi-format ingestion with chunking."""
import re
from dataclasses import dataclass
from pathlib import Path
import yaml
from candlekeep.config import Settings
from candlekeep.database.interface import Chunk


@dataclass
class ProcessResult:
    chunks: list[Chunk]
    images_captioned: int = 0
    images_from_cache: int = 0


class DocumentProcessor:
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".rst", ".json", ".yaml", ".yml"}
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self._captioner = None
        if self.settings.vlm_provider and self.settings.vlm_provider != "none":
            try:
                from candlekeep.providers.factory import create_vision_provider
                from candlekeep.rag.image_captioner import ImageCaptioner
                self._captioner = ImageCaptioner(self.settings, create_vision_provider())
            except Exception:
                pass  # VLM unavailable — degrade gracefully

    def process(self, path: str | Path) -> ProcessResult:
        """Process a file and return ProcessResult with chunks and caption counts."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        text = self._extract_text(path)
        frontmatter, content = self._parse_frontmatter(text)
        chunks = self._chunk_text(content)

        base_meta = {"source": str(path), "filename": path.name, "extension": path.suffix}
        base_meta.update(frontmatter)

        context_prefix = ""
        if self.settings.bardic_knowledge:
            context_parts = []
            if "title" in base_meta:
                context_parts.append(f"Document: {base_meta['title']}")
            if "description" in base_meta:
                context_parts.append(f"Description: {base_meta['description']}")
            context_prefix = ". ".join(context_parts)
            if context_prefix:
                context_prefix += ".\n\n"

        text_chunks = [
            Chunk(
                text=f"{context_prefix}{chunk}" if context_prefix else chunk,
                metadata=base_meta.copy(),
                chunk_index=i,
            )
            for i, chunk in enumerate(chunks)
        ]

        captioned = 0
        from_cache = 0
        if self._captioner:
            try:
                images = self._captioner.extract_images(path)
                cap_chunks, captioned, from_cache = self._captioner.caption_images(
                    path, images,
                    base_chunk_index=len(text_chunks),
                    title=base_meta.get("title", ""),
                    description=base_meta.get("description", ""),
                )
                text_chunks.extend(cap_chunks)
            except Exception:
                pass  # caption failure must not block text ingestion

        return ProcessResult(chunks=text_chunks, images_captioned=captioned, images_from_cache=from_cache)

    def _parse_frontmatter(self, text: str) -> tuple[dict, str]:
        """Extract YAML frontmatter and return (metadata, content)."""
        match = self.FRONTMATTER_PATTERN.match(text)
        if not match:
            return {}, text
        try:
            meta = yaml.safe_load(match.group(1)) or {}
            for key in ("keywords", "tags", "tools", "related"):
                if key in meta and isinstance(meta[key], list):
                    meta[key] = ", ".join(str(v) for v in meta[key])
            for key, val in list(meta.items()):
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    meta[key] = str(val)
            return meta, text[match.end():]
        except yaml.YAMLError:
            return {}, text

    def _extract_text(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            return self._extract_pdf(path)
        return path.read_text(encoding="utf-8", errors="replace")

    def _extract_pdf(self, path: Path) -> str:
        try:
            import pymupdf4llm
            return pymupdf4llm.to_markdown(str(path))
        except Exception:
            pass
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            raise RuntimeError(f"Failed to extract PDF: {e}")

    HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    SETEXT_PATTERN = re.compile(r"^(.+)\n([=\-]{3,})$", re.MULTILINE)

    def _chunk_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        size, overlap = self.settings.chunk_size, self.settings.chunk_overlap
        atx_headers = [(m.start(), m.group()) for m in self.HEADER_PATTERN.finditer(text)]
        setext_headers = [(m.start(), m.group()) for m in self.SETEXT_PATTERN.finditer(text)]
        headers = sorted(atx_headers + setext_headers, key=lambda x: x[0])

        if not headers:
            return self._fixed_chunk(text, size, overlap)

        chunks = []
        positions = [pos for pos, _ in headers]

        if positions[0] > 0:
            preamble = text[:positions[0]].strip()
            if preamble:
                chunks.extend(self._fixed_chunk(preamble, size, overlap))

        for i, pos in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            section = text[pos:end].strip()
            if len(section) <= size:
                chunks.append(section)
            else:
                chunks.extend(self._fixed_chunk(section, size, overlap))

        return chunks

    def _fixed_chunk(self, text: str, size: int, overlap: int) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap if end < len(text) else len(text)
        return chunks

    def process_directory(self, path: str | Path) -> ProcessResult:
        """Process all supported files in a directory."""
        path = Path(path)
        all_chunks: list[Chunk] = []
        total_captioned = 0
        total_from_cache = 0
        for file in path.rglob("*"):
            if file.is_file() and file.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    result = self.process(file)
                    all_chunks.extend(result.chunks)
                    total_captioned += result.images_captioned
                    total_from_cache += result.images_from_cache
                except Exception:
                    continue
        return ProcessResult(
            chunks=all_chunks,
            images_captioned=total_captioned,
            images_from_cache=total_from_cache,
        )
