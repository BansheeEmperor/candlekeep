"""Reranking module for improving search relevance."""
from sentence_transformers import CrossEncoder
from candlekeep.database.interface import SearchResult


def rerank_results(
    query: str,
    results: list[SearchResult],
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    top_k: int = None
) -> list[SearchResult]:
    """Rerank search results using cross-encoder model."""
    if not results:
        return results

    model = CrossEncoder(model_name)
    pairs = [(query, r.text) for r in results]
    scores = model.predict(pairs)

    reranked = []
    for result, score in zip(results, scores):
        reranked.append(SearchResult(
            text=result.text,
            metadata=result.metadata,
            score=float(score),
            doc_id=result.doc_id
        ))

    reranked.sort(key=lambda x: x.score, reverse=True)

    if top_k is not None:
        return reranked[:top_k]
    return reranked
