"""Reranking module for improving search relevance."""
import math
import sys

import torch
from sentence_transformers import CrossEncoder
from candlekeep.database.interface import SearchResult
from candlekeep.config import Settings

_cross_encoder: CrossEncoder | None = None
_cross_encoder_key: str | None = None


def _get_cross_encoder(model_name: str, device: str = "cpu") -> CrossEncoder:
    """Get or create cached CrossEncoder instance.

    On CPU, loads the model in float64 to work around a torch ≥2.10
    regression where float32 matmul produces NaN on certain platforms
    (macOS ARM confirmed). GPU paths are unaffected.
    """
    global _cross_encoder, _cross_encoder_key
    key = f"{model_name}:{device}"
    if _cross_encoder is None or _cross_encoder_key != key:
        settings = Settings.from_env()
        cache_dir = settings.models_dir
        
        try:
            _cross_encoder = CrossEncoder(
                model_name, 
                device=device, 
                local_files_only=True,
                cache_folder=str(cache_dir)
            )
        except Exception:
            print(f"[candlekeep] ❌ Cross-encoder '{model_name}' not found locally in {cache_dir}. "
                  f"Run ./scripts/setup.sh", file=sys.stderr)
            sys.exit(1)

        # Workaround: torch ≥2.10 float32 matmul NaN on CPU (macOS ARM).
        # Promote to float64 on CPU where the issue manifests.
        if device == "cpu":
            _cross_encoder.model = _cross_encoder.model.to(torch.float64)

        _cross_encoder_key = key
    return _cross_encoder


def warm_up(device: str = "cpu"):
    """Trigger model loading to avoid latency on first request."""
    _get_cross_encoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device)


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
        s = float(score)
        if math.isnan(s):
            # Safety net: if NaN slips through despite float64 workaround,
            # preserve the original bi-encoder score so the result isn't lost.
            print(f"[candlekeep] ⚠ Cross-encoder returned NaN for query, "
                  f"falling back to bi-encoder score", file=sys.stderr)
            s = result.score
        reranked.append(SearchResult(
            text=result.text,
            metadata=result.metadata,
            score=s,
            doc_id=result.doc_id
        ))

    reranked.sort(key=lambda x: x.score, reverse=True)

    if top_k is not None:
        return reranked[:top_k]
    return reranked
