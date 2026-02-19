"""Arcane Recall: Parent Document Retrieval.

Retrieve small chunks but return expanded parent context.
"""
from typing import List, Set, Dict, Tuple
import numpy as np
from candlekeep.database.interface import VectorDatabase, SearchResult


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def expand_results(
    db: VectorDatabase,
    results: List[SearchResult],
    n_results: int = 5,
    expansion_chunks: int = 2,
    query: str | None = None
) -> List[SearchResult]:
    """Expand search results with adjacent chunks using similarity-weighted window merging.
    
    Optimizations:
    1. Window Merging: Merges overlapping context windows.
    2. Similarity-Weighted Expansion: Only expands if neighbors are semantically related.
    3. Continuation Markers: Always expands if text suggests a continuation (e.g. Markdown lists).
    """
    if not results:
        return []

    # 1. Group results by source document
    results_by_source = {}
    for r in results:
        source = r.metadata.get("source", "")
        if source:
            if source not in results_by_source:
                results_by_source[source] = []
            results_by_source[source].append(r)

    # 2. Fetch all chunks for the relevant sources once
    chunks_by_source = {}
    stored_embeddings_by_source = {}
    for source in results_by_source:
        source_chunks = db.get_chunks_by_source(source)
        # Store as {chunk_index: Chunk}
        chunks_by_source[source] = {
            c.metadata.get("chunk_index", 0): c for c in source_chunks
        }
        # Fetch stored embeddings (computed at ingestion time) — no inference needed
        stored_embeddings_by_source[source] = db.get_stored_embeddings_by_source(source)

    # 3. Process each source and merge windows
    all_windows = []
    
    # Get query embedding if needed for similarity-weighted expansion
    query_embedding = None
    if query:
        query_embedding = db.get_embeddings([query])[0]

    for source, source_results in results_by_source.items():
        doc_chunks = chunks_by_source[source]
        
        # Use stored embeddings from ChromaDB (no inference needed)
        doc_embeddings = stored_embeddings_by_source.get(source, {})

        # Determine windows for each result in this source
        source_windows = []
        for res in source_results:
            idx = res.metadata.get("chunk_index", 0)
            
            # Start with the match itself
            current_window = {idx}
            
            # Expansion logic
            for offset in range(1, expansion_chunks + 1):
                # Try expanding backwards
                prev_idx = idx - offset
                if prev_idx >= 0 and prev_idx in doc_chunks:
                    if should_expand(doc_chunks[idx], doc_chunks[prev_idx], query_embedding, 
                                     doc_embeddings.get(idx), doc_embeddings.get(prev_idx)):
                        current_window.add(prev_idx)
                    else:
                        break # Stop expanding in this direction
                
            for offset in range(1, expansion_chunks + 1):
                # Try expanding forwards
                next_idx = idx + offset
                if next_idx in doc_chunks:
                    if should_expand(doc_chunks[idx], doc_chunks[next_idx], query_embedding, 
                                     doc_embeddings.get(idx), doc_embeddings.get(next_idx)):
                        current_window.add(next_idx)
                    else:
                        break
            
            source_windows.append((sorted(list(current_window)), res.score, res.metadata))

        # Merge overlapping windows for this source
        if source_windows:
            source_windows.sort(key=lambda x: x[0][0]) # Sort by start index
            
            curr_indices, curr_score, curr_meta = source_windows[0]
            for next_indices, next_score, next_meta in source_windows[1:]:
                # If they overlap or are adjacent
                if next_indices[0] <= curr_indices[-1] + 1:
                    # Merge indices
                    combined = sorted(list(set(curr_indices) | set(next_indices)))
                    curr_indices = combined
                    curr_score = max(curr_score, next_score)
                else:
                    all_windows.append((curr_indices, curr_score, curr_meta, source))
                    curr_indices, curr_score, curr_meta = next_indices, next_score, next_meta
            all_windows.append((curr_indices, curr_score, curr_meta, source))

    # ... (rest of window processing from previous block)
    # Global sort across all sources and limit to n_results
    all_windows.sort(key=lambda x: x[1], reverse=True)
    
    expanded = []
    seen_texts = set()
    
    for indices, score, meta, source in all_windows:
        if len(expanded) >= n_results:
            break
            
        doc_chunks = chunks_by_source.get(source, {})
        if not doc_chunks:
            # Fallback for orphan results (though should not happen in normal flow)
            # Find the original result text if possible
            expanded_text = meta.get("_original_text", "") 
            # Note: We'd need to store original text in metadata for this to work perfectly, 
            # but for now, let's just use what we have in doc_chunks or empty.
            if not expanded_text:
                # If we don't have doc_chunks, we can't build the expanded text.
                # However, all_windows was built from source_results which came from results.
                # Let's handle the empty case gracefully.
                expanded_text = ""
        else:
            context_parts = [doc_chunks[i].text for i in indices if i in doc_chunks]
            expanded_text = "\n\n".join(context_parts)
        
        if expanded_text in seen_texts:
            continue
        seen_texts.add(expanded_text)
        
        expanded.append(SearchResult(
            text=expanded_text,
            score=score,
            metadata=meta.copy(),
            doc_id=source
        ))

    return expanded


def should_expand(match_chunk, neighbor_chunk, query_embedding, match_embedding, neighbor_embedding) -> bool:
    """Decide if a neighbor should be included in the expansion window."""
    # 1. Continuation markers (Markdown lists, sub-bullets)
    text = neighbor_chunk.text.strip()
    continuation_prefixes = ("- ", "* ", "+ ", "> ", "  ")
    if text.startswith(continuation_prefixes):
        return True
    
    # 2. Similarity-Weighted Expansion
    # If we have a query embedding, check if neighbor is relevant to the query
    if query_embedding is not None and match_embedding is not None and neighbor_embedding is not None:
        match_sim = calculate_cosine_similarity(query_embedding, match_embedding)
        neighbor_sim = calculate_cosine_similarity(query_embedding, neighbor_embedding)
        
        # Only expand if neighbor’s similarity to the query is within 8% of
        # the match.  NOTE: 0.92 is a relative multiplier
        # (EXPANSION_SIMILARITY_THRESHOLD), not an absolute cosine threshold.
        # Effective cutoff = match_sim × 0.92.
        # See ARCHITECTURE.md § Tuned Parameters for recalibration guidance.
        if neighbor_sim >= (match_sim * 0.92):
            return True
        return False

    return True # Default to expansion if no query embedding provided (legacy behavior)


def search_with_arcane_recall(
    db: VectorDatabase,
    query: str,
    n_results: int = 5,
    expansion_chunks: int = 2
) -> List[SearchResult]:
    """Search with parent document expansion."""
    if n_results > 10:
        import sys
        print(
            f"[candlekeep] ⚠ n_results={n_results} — Arcane Recall computes "
            f"cosine similarity for each neighbor of each result. At high "
            f"n_results, expansion latency scales linearly. See "
            f"ARCHITECTURE.md § Arcane Recall for details.",
            file=sys.stderr,
        )
    # Pass query to expand_results for similarity-weighted pruning
    results = db.search(query, n_results=n_results * 2)
    return expand_results(db, results, n_results, expansion_chunks, query=query)
