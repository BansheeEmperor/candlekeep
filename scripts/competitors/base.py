"""Base class and utilities for RAG competitors."""
import time
from pathlib import Path
from typing import Any
from candlekeep.config import Settings
from candlekeep.database.interface import SearchResult

# Forced-equal constants from project settings
_settings = Settings.from_env()
CHUNK_SIZE = _settings.chunk_size
CHUNK_OVERLAP = _settings.chunk_overlap


class Competitor:
    """Base class for RAG competitors."""

    name: str = "base"

    def ingest(self, doc_paths: list[Path]) -> int:
        """Ingest documents and return number of chunks created."""
        raise NotImplementedError

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        """Search and return top-k results."""
        raise NotImplementedError

    def reset(self) -> None:
        """Reset state (e.g. clear vector store)."""
        pass


def timed_search(competitor: Competitor, query: str, k: int = 5) -> tuple[list[SearchResult], float]:
    """Execute search and return results with latency in ms."""
    start = time.perf_counter()
    results = competitor.search(query, k=k)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return results, elapsed_ms


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Simple YAML frontmatter parser for competitors."""
    if not text.startswith("---"):
        return {}, text
    
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
        
    yaml_text = parts[1].strip()
    content = parts[2].strip()
    
    metadata = {}
    for line in yaml_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip()] = value.strip().strip('"').strip("'")
            
    return metadata, content
