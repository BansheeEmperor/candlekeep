"""Lexical search and rank fusion for hybrid retrieval."""
import re
from typing import List
from rank_bm25 import BM25Okapi
from candlekeep.database.interface import SearchResult

# Common English stop words — filtered from BM25 tokenization to reduce noise.
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "it", "its",
    "this", "that", "these", "those", "i", "you", "he", "she", "we",
    "they", "me", "him", "her", "us", "them", "my", "your", "his",
    "our", "their", "what", "which", "who", "whom", "how", "when",
    "where", "why", "not", "no", "if", "then", "than", "so", "as",
    "about", "into", "through", "during", "before", "after", "above",
    "below", "between", "each", "all", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "also", "just",
    "very", "too", "any",
})

_WORD_RE = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")

# Alias used by token_normalisation.py when extracting corpus tokens
_token_re = _WORD_RE


def _tokenize(text: str) -> List[str]:
    """Tokenize text for BM25: lowercase, extract words, filter stop words.

    Applies the corpus-derived normalisation map (if loaded) so that surface
    variants map to the same canonical token. The map is built to include
    separator-stripped forms (e.g. 'crossencoder' → 'cross-encoder'), so
    queries using concatenated forms match documents using hyphenated forms.
    """
    from candlekeep.rag.token_normalisation import get_normalisation_map
    from candlekeep.config import get_data_dir
    tokens = [w for w in _WORD_RE.findall(text.lower()) if w not in STOP_WORDS]
    norm_map = get_normalisation_map(get_data_dir())
    if norm_map is not None:
        tokens = norm_map.normalise_all(tokens)
    return tokens


def reciprocal_rank_fusion(
    results_list: List[List[SearchResult]], 
    k: int = 60, 
    top_n: int = 5
) -> List[SearchResult]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion.
    
    Args:
        results_list: List of ranked SearchResult lists.
        k: Smoothing constant (default 60).
        top_n: Number of results to return.
    """
    fused_scores = {}  # {doc_text: score}
    doc_map = {}      # {doc_text: SearchResult}
    
    for results in results_list:
        for rank, res in enumerate(results):
            # We use text as the unique identifier for fusion
            if res.text not in fused_scores:
                fused_scores[res.text] = 0.0
                doc_map[res.text] = res
            
            fused_scores[res.text] += 1.0 / (k + (rank + 1))
            
    # Sort by fused score
    sorted_texts = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
    
    fused_results = []
    for text in sorted_texts[:top_n]:
        res = doc_map[text]
        # Update the score to the fused score
        res.score = fused_scores[text]
        fused_results.append(res)
        
    return fused_results


class BM25Searcher:
    """In-memory BM25 index for lexical retrieval.

    Supports incremental updates: add/remove chunks without re-fetching
    the full corpus from ChromaDB. The tokenized corpus is cached in memory;
    only the BM25Okapi IDF statistics are recomputed on mutation (O(N)
    arithmetic over pre-tokenized data, no network I/O or re-tokenization).
    """
    
    def __init__(self, chunks: List[SearchResult]):
        self.chunks = list(chunks)
        self.tokenized_corpus = [_tokenize(doc.text) for doc in self.chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None

    def _rebuild_bm25(self):
        """Rebuild BM25Okapi from the cached tokenized corpus (no I/O)."""
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def add_chunks(self, new_chunks: List[SearchResult]):
        """Add chunks incrementally. Tokenizes only the new chunks, then
        rebuilds BM25 IDF over the full (cached) tokenized corpus."""
        for chunk in new_chunks:
            self.chunks.append(chunk)
            self.tokenized_corpus.append(_tokenize(chunk.text))
        self._rebuild_bm25()

    def remove_by_source(self, source: str):
        """Remove all chunks from a source. Rebuilds BM25 IDF over the
        remaining cached tokenized corpus."""
        indices_to_remove = [
            i for i, c in enumerate(self.chunks)
            if c.metadata.get("source", "") == source
        ]
        if not indices_to_remove:
            return
        # Remove in reverse order to preserve indices
        for i in reversed(indices_to_remove):
            del self.chunks[i]
            del self.tokenized_corpus[i]
        self._rebuild_bm25()

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        if not self.bm25:
            return []
        tokenized_query = _tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top indices
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:n_results]
        
        results = []
        for i in top_indices:
            if scores[i] <= 0:
                continue
            res = self.chunks[i]
            # Copy to avoid modifying original
            new_res = SearchResult(
                text=res.text,
                metadata=res.metadata.copy(),
                score=float(scores[i]),
                doc_id=res.doc_id
            )
            results.append(new_res)
            
        return results


# Global cache for BM25 searcher to avoid rebuilding on every query
_bm25_cache: BM25Searcher | None = None
_cache_lock = __import__("threading").Lock()

def get_bm25_searcher(db) -> BM25Searcher:
    global _bm25_cache
    with _cache_lock:
        if _bm25_cache is None:
            chunks = db.get_all_chunks()
            if chunks:
                _bm25_cache = BM25Searcher(chunks)
        return _bm25_cache


def clear_bm25_cache():
    """Full invalidation — forces rebuild from ChromaDB on next query.

    Use only for repopulate_database. For add/delete operations, prefer
    update_bm25_cache / remove_from_bm25_cache to avoid the ChromaDB
    round-trip.
    """
    global _bm25_cache
    with _cache_lock:
        _bm25_cache = None


def update_bm25_cache(new_chunks: List[SearchResult], removed_source: str | None = None):
    """Incrementally update the BM25 cache after a write operation.

    Avoids the full ChromaDB fetch + re-tokenization of clear_bm25_cache().
    The BM25Okapi IDF statistics are recomputed over the in-memory tokenized
    corpus — this is O(N) arithmetic, not O(N) network I/O + tokenization.

    Args:
        new_chunks: Chunks that were just added (already ingested into ChromaDB).
        removed_source: Source path that was deleted before adding new_chunks
                        (the ingest flow deletes old chunks then adds new ones).
    """
    global _bm25_cache
    with _cache_lock:
        if _bm25_cache is None:
            # Cache hasn't been built yet (no hybrid query has run).
            # Don't build it now — let the next hybrid query do the full init.
            return
        if removed_source:
            _bm25_cache.remove_by_source(removed_source)
        if new_chunks:
            _bm25_cache.add_chunks(new_chunks)


def remove_from_bm25_cache(source: str):
    """Remove a source from the BM25 cache after a delete operation."""
    global _bm25_cache
    with _cache_lock:
        if _bm25_cache is None:
            return
        _bm25_cache.remove_by_source(source)


def hybrid_search(
    db, 
    query: str, 
    n_results: int = 5,
    category: str | None = None
) -> List[SearchResult]:
    """Perform hybrid search combining Vector and sparse results.
    
    The sparse signal is BM25 by default. When CANDLEKEEP_SPARSE_BACKEND=colbert,
    uses ColBERT late interaction instead. Falls back to BM25 transparently if
    the ColBERT index is rebuilding.

    When CANDLEKEEP_GRAPH_AUGMENT=true (default) and the entity co-occurrence
    graph is available, the explore path uses smart graph expansion to surface
    related documents invisible to standard vector+BM25 search.

    Args:
        db: VectorDatabase instance.
        query: Search query.
        n_results: Number of results to return.
        category: Optional category filter.
    """
    from candlekeep.rag.arcane_recall import expand_results
    
    # 1. Get Vector results (fetch more for fusion)
    vector_results = db.search(query, n_results=n_results * 4, category=category)
    
    # 2. Get sparse results (ColBERT or BM25)
    sparse_results = _get_sparse_results(db, query, n_results * 4, category)

    # 3. Combine with RRF (2-way: vector + sparse)
    fused_results = reciprocal_rank_fusion(
        [vector_results, sparse_results], k=60, top_n=n_results * 4,
    )
    
    # 5. Apply Arcane Recall (context expansion)
    expanded = expand_results(db, fused_results, n_results=n_results, query=query)
    
    return expanded


def _get_sparse_results(
    db, query: str, n_results: int, category: str | None
) -> List[SearchResult]:
    """Get sparse retrieval results from the configured backend.

    When ColBERT is configured but its index is rebuilding, falls back
    to BM25 with a warning log.
    """
    import os
    backend = os.getenv("CANDLEKEEP_SPARSE_BACKEND", "bm25")

    if backend == "colbert":
        return _colbert_sparse(db, query, n_results, category)

    return _bm25_sparse(db, query, n_results, category)


def _bm25_sparse(
    db, query: str, n_results: int, category: str | None
) -> List[SearchResult]:
    """BM25 sparse retrieval."""
    bm25_searcher = get_bm25_searcher(db)
    if not bm25_searcher:
        return []
    results = bm25_searcher.search(query, n_results=n_results)
    if category:
        results = [r for r in results if r.metadata.get("category") == category]
    return results


def _colbert_sparse(
    db, query: str, n_results: int, category: str | None
) -> List[SearchResult]:
    """ColBERT sparse retrieval with BM25 fallback."""
    import logging
    logger = logging.getLogger("candlekeep")

    from candlekeep.rag.colbert import is_available, get_colbert_searcher

    if not is_available():
        logger.warning(
            "[candlekeep] \u26a0 ColBERT unavailable, using BM25 fallback"
        )
        return _bm25_sparse(db, query, n_results, category)

    searcher = get_colbert_searcher(db)
    if searcher is None or not searcher.ensure_index():
        logger.warning(
            "[candlekeep] \u26a0 ColBERT index rebuilding, using BM25 fallback for this query"
        )
        return _bm25_sparse(db, query, n_results, category)

    results = searcher.search(query, n_results=n_results)
    if category:
        results = [r for r in results if r.metadata.get("category") == category]
    return results


# ── Explore search (smart graph expansion) ────────────────────────────────

_PAIRED_JACCARD_THRESHOLD = 0.0  # any co-occurrence edge = paired


def explore_search(
    db,
    query: str,
    n_results: int = 5,
    category: str | None = None,
) -> List[SearchResult]:
    """Hybrid search with smart graph expansion.

    1. Extract entities from query.
    2. Identify paired entities (co-occurring partners already in query).
    3. Expand only unpaired entities via the co-occurrence graph.
    4. Vector+BM25 RRF → top-(n_results - M) results.
    5. Fill M slots with unique graph expansion docs.
    6. Fallback: if graph has fewer than M unique docs, fill from RRF.

    M=2 reserved graph slots based on benchmark sweep (Option C, M=2:
    50% expansion recall, 0% NDCG degradation with smart expansion).
    """
    from candlekeep.rag.arcane_recall import expand_results

    m_slots = 2

    # Standard 2-way RRF
    vector_results = db.search(query, n_results=n_results * 4, category=category)
    sparse_results = _get_sparse_results(db, query, n_results * 4, category)
    fused = reciprocal_rank_fusion(
        [vector_results, sparse_results], k=60, top_n=n_results * 4,
    )

    # Smart graph expansion
    graph_unique = []
    try:
        from candlekeep.database.graph_store import get_graph_store
        from candlekeep.rag.extractor import get_extractor
        from candlekeep.rag.graph_augment import get_graph_chunks

        settings = getattr(db, "settings", None)
        if settings:
            gs = get_graph_store(settings)
            if gs:
                extractor = get_extractor(settings.entity_ruler_path)
                query_entities = extractor.extract(query)

                if query_entities:
                    # Identify paired entities
                    paired = set()
                    for i, e1 in enumerate(query_entities):
                        for e2 in query_entities[i + 1:]:
                            for ent, jac in gs.get_related(e1, top_n=50):
                                if ent == e2 and jac >= _PAIRED_JACCARD_THRESHOLD:
                                    paired.add(e1)
                                    paired.add(e2)
                                    break

                    # Expand only unpaired entities
                    expand = [e for e in query_entities if e not in paired]

                    if expand:
                        graph_results = get_graph_chunks(
                            db, gs, query,
                            n_results=n_results * 2,
                            entity_filter=expand,
                        )
                        fused_ids = {r.doc_id for r in fused[:n_results * 4]}
                        graph_unique = [r for r in graph_results if r.doc_id not in fused_ids]
    except Exception:
        pass  # graph expansion must never break search

    # Assemble: top-(n-M) from RRF + up to M graph unique + fallback
    rrf_slots = n_results - min(len(graph_unique), m_slots)
    final = list(fused[:rrf_slots])
    final.extend(graph_unique[:m_slots])

    if len(final) < n_results:
        used_ids = {r.doc_id for r in final}
        for r in fused[rrf_slots:]:
            if r.doc_id not in used_ids:
                final.append(r)
                used_ids.add(r.doc_id)
            if len(final) >= n_results:
                break

    expanded = expand_results(db, final, n_results=n_results, query=query)
    return expanded
