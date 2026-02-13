"""Arcane Recall: Parent Document Retrieval.

Retrieve small chunks but return expanded parent context.
"""
from typing import List
from candlekeep.database.interface import VectorDatabase, SearchResult


def expand_results(
    db: VectorDatabase,
    results: List[SearchResult],
    n_results: int = 5,
    expansion_chunks: int = 2,
) -> List[SearchResult]:
    """Expand search results with adjacent chunks from the same document."""
    chunks_by_source = {}
    for r in results:
        source = r.metadata.get("source", "")
        if source and source not in chunks_by_source:
            source_chunks = db.get_chunks_by_source(source)
            chunks_by_source[source] = {
                c.metadata.get("chunk_index", 0): c for c in source_chunks
            }

    expanded = []
    seen_texts = set()

    for result in results:
        if len(expanded) >= n_results:
            break

        source = result.metadata.get("source", "")
        chunk_idx = result.metadata.get("chunk_index", 0)

        if source not in chunks_by_source:
            expanded.append(result)
            continue

        start_idx = max(0, chunk_idx - expansion_chunks)
        end_idx = chunk_idx + expansion_chunks + 1

        context_parts = []
        for idx in range(start_idx, end_idx):
            if idx in chunks_by_source[source]:
                context_parts.append(chunks_by_source[source][idx].text)

        expanded_text = "\n\n".join(context_parts)

        if expanded_text in seen_texts:
            continue
        seen_texts.add(expanded_text)

        expanded.append(SearchResult(
            text=expanded_text,
            score=result.score,
            metadata=result.metadata.copy(),
            doc_id=result.doc_id
        ))

    return expanded[:n_results]


def search_with_arcane_recall(
    db: VectorDatabase,
    query: str,
    n_results: int = 5,
    expansion_chunks: int = 2
) -> List[SearchResult]:
    """Search with parent document expansion."""
    results = db.search(query, n_results=n_results * 2)
    return expand_results(db, results, n_results, expansion_chunks)
