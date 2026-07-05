"""Base protocol and utilities for competitive benchmark competitors.

All competitors implement the same interface and return the same SearchResult
type so the eval runner works unchanged across implementations.

Isolation principle: competitors use chromadb directly, not Candlekeep's
vector store. The only shared code is the embedding model (bge-small-en-v1.5)
and the SearchResult / Chunk dataclasses.
"""
import time
import hashlib
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import chromadb
from sentence_transformers import SentenceTransformer

from candlekeep.database.interface import SearchResult, Chunk


# ── Shared embedding model (singleton) ──────────────────────────────
# All competitors use the same model instance to ensure identical
# embeddings. This isolates retrieval strategy from embedding quality.

_shared_model: SentenceTransformer | None = None


def get_shared_embedding_model(
    model_id: str = "BAAI/bge-small-en-v1.5",
    device: str = "cpu",
    cache_dir: str | None = None,
) -> SentenceTransformer:
    """Return a singleton SentenceTransformer shared across all competitors."""
    global _shared_model
    if _shared_model is None:
        kwargs = {"device": device}
        if cache_dir:
            kwargs["cache_folder"] = cache_dir
        _shared_model = SentenceTransformer(model_id, **kwargs)
    return _shared_model


def reset_shared_model():
    """Reset the singleton (for test isolation)."""
    global _shared_model
    _shared_model = None


# ── Shared chunking (forced-equal for apples-to-apples) ────────────
# All competitors use identical 512-char chunks with 50-char overlap.
# This isolates retrieval strategy from chunking strategy.
#
# Future work: test the effect of varying these variables:
#   - chunk_size: 256, 512, 768, 1024, 1536
#   - chunk_overlap: 0, 25, 50, 100, 200
#   - splitting strategy: fixed-size vs markdown-header vs sentence-aware
#   - frontmatter handling: strip vs preserve vs prepend-to-chunks
import re
import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter. Returns (metadata, content)."""
    match = _FRONTMATTER_RE.match(text)
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


def _fixed_chunk(text: str, size: int, overlap: int) -> list[str]:
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


def shared_chunk_document(path: Path) -> list[Chunk]:
    """Chunk a document using the shared strategy (512 chars, 50 overlap).

    Splits on markdown headers when present, falls back to fixed-size.
    Strips frontmatter but preserves it as metadata.
    Does NOT apply Bardic Knowledge (context prefix) — that's a
    Candlekeep-specific technique tested via ablation.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, content = _parse_frontmatter(text)

    headers = list(_HEADER_RE.finditer(content))
    if headers:
        raw_chunks = []
        positions = [m.start() for m in headers]
        if positions[0] > 0:
            preamble = content[:positions[0]].strip()
            if preamble:
                raw_chunks.extend(_fixed_chunk(preamble, CHUNK_SIZE, CHUNK_OVERLAP))
        for i, pos in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(content)
            section = content[pos:end].strip()
            if len(section) <= CHUNK_SIZE:
                raw_chunks.append(section)
            else:
                raw_chunks.extend(_fixed_chunk(section, CHUNK_SIZE, CHUNK_OVERLAP))
    else:
        raw_chunks = _fixed_chunk(content, CHUNK_SIZE, CHUNK_OVERLAP)

    base_meta = {"source": str(path), "filename": path.name, "extension": path.suffix}
    base_meta.update(frontmatter)

    return [
        Chunk(text=chunk, metadata=base_meta.copy(), chunk_index=i)
        for i, chunk in enumerate(raw_chunks)
    ]


def generate_chunk_id(chunk: Chunk) -> str:
    """Deterministic ID for a chunk."""
    content = f"{chunk.metadata.get('source', '')}:{chunk.chunk_index}:{chunk.text[:100]}"
    return hashlib.md5(content.encode()).hexdigest()


# ── Competitor base class ───────────────────────────────────────────

class Competitor(ABC):
    """Base class for benchmark competitors.

    Each competitor manages its own chromadb collection and implements
    ingest/search/reset using chromadb directly (not Candlekeep's
    vector store).
    """

    name: str

    @abstractmethod
    def ingest(self, doc_paths: list[Path]) -> int:
        """Ingest documents. Returns chunk count."""
        ...

    @abstractmethod
    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        """Search and return top-k results."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Clear all indexed data."""
        ...


# ── Timing utility ──────────────────────────────────────────────────

def timed_search(competitor: Competitor, query: str, k: int = 5) -> tuple[list[SearchResult], float]:
    """Run a search and return (results, latency_ms)."""
    start = time.perf_counter_ns()
    results = competitor.search(query, k)
    latency_ms = (time.perf_counter_ns() - start) / 1e6
    return results, latency_ms
