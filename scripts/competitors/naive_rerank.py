"""Naive vector search + rerank competitor."""
from pathlib import Path
from candlekeep.database.interface import SearchResult
from scripts.competitors.naive import NaiveVectorSearch
from scripts.competitors.base import CHUNK_SIZE, CHUNK_OVERLAP

class NaiveRerank(NaiveVectorSearch):
    """Naive vector search + Cross-encoder reranking."""

    name = "naive-rerank"

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        # Get more candidates for reranking
        candidates = super().search(query, k=k * 4)
        if not candidates:
            return []
            
        from candlekeep.rag.reranker import rerank_results
        # Uses the shared reranker model
        return rerank_results(query, candidates, top_k=k, device="cpu")
