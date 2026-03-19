"""Bootstrap entity ruler vocabulary from corpus by document frequency."""
import json
import re
from collections import defaultdict
from pathlib import Path

from candlekeep.database.interface import SearchResult
from candlekeep.rag.extractor import _tech_tokens

_TOP_N = 500


def bootstrap_entity_ruler(chunks: list[SearchResult], output_path: Path) -> int:
    """Extract top-N technical entities by document frequency, write to JSONL.

    Returns the number of patterns written.
    """
    # Count document frequency (distinct sources per entity surface form)
    doc_freq: dict[str, set[str]] = defaultdict(set)
    for chunk in chunks:
        source = chunk.metadata.get("source", "")
        for tok in _tech_tokens(chunk.text):
            doc_freq[tok].add(source)

    # Rank by doc frequency, take top N
    ranked = sorted(doc_freq.items(), key=lambda x: len(x[1]), reverse=True)[:_TOP_N]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        for surface, _ in ranked:
            f.write(json.dumps({"label": "TECH", "pattern": surface}) + "\n")

    return len(ranked)
