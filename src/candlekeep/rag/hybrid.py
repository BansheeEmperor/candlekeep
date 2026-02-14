"""Lexical search and rank fusion for hybrid retrieval."""
from typing import List
from rank_bm25 import BM25Okapi
from candlekeep.database.interface import SearchResult


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
    """In-memory BM25 index for lexical retrieval."""
    
    def __init__(self, chunks: List[SearchResult]):
        self.chunks = chunks
        # Tokenize chunks for BM25
        self.tokenized_corpus = [doc.text.lower().split() for doc in chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        tokenized_query = query.lower().split()
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
_bm25_cache = None
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
    """Invalidate the BM25 searcher cache."""
    global _bm25_cache
    with _cache_lock:
        _bm25_cache = None


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
