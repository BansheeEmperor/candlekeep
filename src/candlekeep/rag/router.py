"""Adaptive query routing based on agent-provided query type."""
from typing import List, Literal
from candlekeep.database.interface import VectorDatabase, SearchResult
from candlekeep.rag.search import preprocess_negation

QueryType = Literal["simple", "precise"]

# Minimum score threshold — results below this are filtered as irrelevant.
# Based on score distribution analysis: adversarial=0.558, lowest legitimate=0.748.
MIN_RELEVANCE_SCORE = 0.65


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

    For complex multi-part questions, the agent should decompose into
    multiple simple searches and synthesize the results itself.
    """
    from candlekeep.rag.arcane_recall import search_with_arcane_recall

    processed = preprocess_negation(query)

    if query_type == "precise":
        from candlekeep.rag.reranker import rerank_results
        results = search_with_arcane_recall(db, processed, n_results * 3)
        results = rerank_results(processed, results, top_k=n_results)
    else:
        results = search_with_arcane_recall(db, processed, n_results)
        # Filter below relevance threshold (skip for precise — cross-encoder uses different scale)
        results = [r for r in results if r.score >= MIN_RELEVANCE_SCORE]

    return results
