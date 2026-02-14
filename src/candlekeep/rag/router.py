"""Adaptive query routing based on agent-provided query type."""
from typing import List, Literal
from candlekeep.database.interface import VectorDatabase, SearchResult
from candlekeep.rag.search import preprocess_negation

QueryType = Literal["simple", "precise", "hybrid"]

# Minimum score threshold — results below this are filtered as irrelevant.
# Based on score distribution analysis: adversarial=0.709, lowest legitimate=0.847.
MIN_RELEVANCE_SCORE = 0.75


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
        simple  -> Arcane Recall (~23ms)
        precise -> Arcane Recall + Divine Insight: expanded + reranked (~1550ms)
        hybrid  -> BM25 + Vector + RRF + Arcane Recall (~80ms)

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
        # RRF scores are on a different scale [0, 1] but often small. 
        # We don't apply MIN_RELEVANCE_SCORE to hybrid for now as RRF 
        # doesn't map directly to the vector similarity threshold.
    else:
        results = search_with_arcane_recall(db, processed, n_results)
        # Filter below relevance threshold (skip for precise/hybrid — different scales)
        results = [r for r in results if r.score >= MIN_RELEVANCE_SCORE]

    return results
