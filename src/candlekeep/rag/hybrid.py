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


def _tokenize(text: str) -> List[str]:
    """Tokenize text for BM25: lowercase, extract words, filter stop words.

    Preserves technical identifiers like 'bge-small', 'v3.4.1', 'ms-marco'.
    """
    return [w for w in _WORD_RE.findall(text.lower()) if w not in STOP_WORDS]


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
    """Perform hybrid search combining Vector and BM25 results.
    
    Args:
        db: VectorDatabase instance.
        query: Search query.
        n_results: Number of results to return.
        category: Optional category filter.
    """
    from candlekeep.rag.arcane_recall import expand_results
    
    # 1. Get Vector results (fetch more for fusion)
    vector_results = db.search(query, n_results=n_results * 4, category=category)
    
    # 2. Get BM25 results
    bm25_searcher = get_bm25_searcher(db)
    if bm25_searcher:
        bm25_results = bm25_searcher.search(query, n_results=n_results * 4)
        # Apply category filter to BM25 if needed
        if category:
            bm25_results = [r for r in bm25_results if r.metadata.get("category") == category]
    else:
        bm25_results = []
        
    # 3. Combine with RRF
    # Fetch 4x candidates to allow for merging and backfilling
    fused_results = reciprocal_rank_fusion(
        [vector_results, bm25_results],
        k=60,
        top_n=n_results * 4
    )
    
    # 4. Apply Arcane Recall (context expansion)
    # n_results is the final cap for the sections returned to the agent
    expanded = expand_results(db, fused_results, n_results=n_results, query=query)
    
    return expanded
