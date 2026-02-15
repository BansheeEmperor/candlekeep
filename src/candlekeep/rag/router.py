"""Adaptive query routing based on agent-provided query type."""
from typing import List, Literal
from candlekeep.database.interface import VectorDatabase, SearchResult
from candlekeep.rag.search import preprocess_negation

QueryType = Literal["simple", "precise", "hybrid"]

# Minimum score threshold — results below this are filtered as irrelevant.
# Based on score distribution analysis: adversarial=0.709, lowest legitimate=0.847.
MIN_RELEVANCE_SCORE = 0.75

# RRF scores for hybrid are much smaller (usually < 0.1).
# Based on Centurion adversarial analysis, noise usually stays below 0.02.
# NOTE: This is a statistical heuristic based on the Centurion corpus size. 
# In production with 1M+ chunks, this threshold may require recalibration.
HYBRID_RELEVANCE_THRESHOLD = 0.03


def search_with_routing(
    db: VectorDatabase,
    query: str,
    n_results: int = 5,
    category: str | None = None,
    query_type: QueryType = "simple",
) -> List[SearchResult]:
    """Route search to optimal technique stack based on query type.

    All paths use Arcane Recall (±2 chunk expansion) by default.
    Results below MIN_RELEVANCE_SCORE are filtered out.

    Stacks:
        simple  -> Arcane Recall (fast)
        precise -> Arcane Recall + Divine Insight (high accuracy, slower)
        hybrid  -> BM25 + Vector + RRF + Arcane Recall (lexical + semantic)

    For complex multi-part questions, the agent should decompose into
    multiple simple searches and synthesize the results itself.
    """
    from candlekeep.rag.arcane_recall import search_with_arcane_recall

    processed = preprocess_negation(query)

    if query_type == "precise":
        from candlekeep.rag.reranker import rerank_results
        device = getattr(db, 'settings', None)
        device = device.device if device else "cpu"
        # Fetch candidates and apply threshold before slow reranking
        results = search_with_arcane_recall(db, processed, n_results * 3)
        results = [r for r in results if r.score >= MIN_RELEVANCE_SCORE]
        
        if results:
            results = rerank_results(processed, results, top_k=n_results, device=device)
    elif query_type == "hybrid":
        from candlekeep.rag.hybrid import hybrid_search
        results = hybrid_search(db, processed, n_results, category=category)
        # Apply threshold to hybrid RRF results
        results = [r for r in results if r.score >= HYBRID_RELEVANCE_THRESHOLD]
    else:
        results = search_with_arcane_recall(db, processed, n_results)
        # Filter below relevance threshold (skip for precise/hybrid — different scales)
        results = [r for r in results if r.score >= MIN_RELEVANCE_SCORE]

    return results
