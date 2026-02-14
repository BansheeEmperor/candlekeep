"""Reranking module for improving search relevance."""
from sentence_transformers import CrossEncoder
from candlekeep.database.interface import SearchResult

_cross_encoder: CrossEncoder | None = None
_cross_encoder_key: str | None = None


def _get_cross_encoder(model_name: str, device: str = "cpu") -> CrossEncoder:
    """Get or create cached CrossEncoder instance."""
    global _cross_encoder, _cross_encoder_key
    key = f"{model_name}:{device}"
    if _cross_encoder is None or _cross_encoder_key != key:
        _cross_encoder = CrossEncoder(model_name, device=device)
        _cross_encoder_key = key
    return _cross_encoder


def rerank_results(
    query: str,
    results: list[SearchResult],
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    top_k: int = None,
    device: str = "cpu",
) -> list[SearchResult]:
    """Rerank search results using cross-encoder model."""
    if not results:
        return results

    model = _get_cross_encoder(model_name, device)
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
