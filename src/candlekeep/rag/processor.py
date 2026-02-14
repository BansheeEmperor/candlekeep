"""Document processor for multi-format ingestion with chunking."""
import re
from pathlib import Path
import yaml
from candlekeep.config import Settings
from candlekeep.database.interface import Chunk


class DocumentProcessor:
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".rst", ".json", ".yaml", ".yml"}
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()

    def process(self, path: str | Path) -> list[Chunk]:
        """Process a file and return chunks with metadata."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        text = self._extract_text(path)
        frontmatter, content = self._parse_frontmatter(text)
        chunks = self._chunk_text(content)

        base_meta = {"source": str(path), "filename": path.name, "extension": path.suffix}
        base_meta.update(frontmatter)

        # Build context prefix from metadata (Bardic Knowledge)
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

        return [
            Chunk(
                text=f"{context_prefix}{chunk}" if context_prefix else chunk,
                metadata=base_meta.copy(),
                chunk_index=i
            )
            for i, chunk in enumerate(chunks)
        ]

    def _parse_frontmatter(self, text: str) -> tuple[dict, str]:
        """Extract YAML frontmatter and return (metadata, content)."""
        match = self.FRONTMATTER_PATTERN.match(text)
        if not match:
            return {}, text
        try:
            meta = yaml.safe_load(match.group(1)) or {}
            # Flatten lists to comma-separated for ChromaDB
            for key in ("keywords", "tags", "tools", "related"):
                if key in meta and isinstance(meta[key], list):
                    meta[key] = ", ".join(str(v) for v in meta[key])
            # Convert non-string values to strings
            for key, val in list(meta.items()):
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    meta[key] = str(val)
            return meta, text[match.end():]
        except yaml.YAMLError:
            return {}, text

    def _extract_text(self, path: Path) -> str:
        """Extract text from file."""
        if path.suffix.lower() == ".pdf":
            return self._extract_pdf(path)
        return path.read_text(encoding="utf-8", errors="replace")

    def _extract_pdf(self, path: Path) -> str:
        """Extract PDF text."""
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

    def _chunk_text(self, text: str) -> list[str]:
        """Split text at markdown headers when present, else fixed chunking."""
        if not text.strip():
            return []

        size, overlap = self.settings.chunk_size, self.settings.chunk_overlap
        headers = list(self.HEADER_PATTERN.finditer(text))

        if not headers:
            return self._fixed_chunk(text, size, overlap)

        chunks = []
        positions = [m.start() for m in headers]
        
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
        """Fixed-size chunking with overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap if end < len(text) else len(text)
        return chunks

    def process_directory(self, path: str | Path) -> list[Chunk]:
        """Process all supported files in a directory."""
        path = Path(path)
        all_chunks = []
        for file in path.rglob("*"):
            if file.is_file() and file.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    all_chunks.extend(self.process(file))
                except Exception:
                    continue
        return all_chunks
