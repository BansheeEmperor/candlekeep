"""Naive vector search + cross-encoder reranking competitor.

The most common single upgrade: retrieve more candidates from ChromaDB,
then rerank with a cross-encoder. Same cross-encoder as Candlekeep's
precise path (ms-marco-MiniLM-L-6-v2) for a fair comparison.
"""
import math
from pathlib import Path

import torch
from sentence_transformers import CrossEncoder

import chromadb

from candlekeep.database.interface import SearchResult
from scripts.competitors.base import (
    Competitor,
    get_shared_embedding_model,
    shared_chunk_document,
    generate_chunk_id,
)

_cross_encoder: CrossEncoder | None = None


def _get_cross_encoder(device: str = "cpu") -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2", device=device,
        )
        if device == "cpu":
            _cross_encoder.model = _cross_encoder.model.to(torch.float64)
    return _cross_encoder


class NaiveRerank(Competitor):
    """ChromaDB top-k → cross-encoder reranking. No expansion, no filtering."""

    name = "naive-rerank"

    def __init__(self, db_path: str | None = None, device: str = "cpu"):
        self.client = chromadb.Client() if db_path is None else chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="naive_rerank_benchmark",
            metadata={"hnsw:space": "cosine"},
        )
        self.model = get_shared_embedding_model()
        self.device = device

    def ingest(self, doc_paths: list[Path]) -> int:
        total = 0
        for path in doc_paths:
            if not path.is_file():
                continue
            chunks = shared_chunk_document(path)
            if not chunks:
                continue

            ids = [generate_chunk_id(c) for c in chunks]
            texts = [c.text for c in chunks]
            embeddings = self.model.encode(texts, convert_to_numpy=True).tolist()
            metadatas = [{**c.metadata, "chunk_index": c.chunk_index} for c in chunks]

            self.collection.upsert(
                ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas,
            )
            total += len(chunks)
        return total

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        # Over-fetch 3× candidates for reranking (same ratio as Candlekeep precise)
        embedding = self.model.encode([query], convert_to_numpy=True).tolist()
        results = self.collection.query(query_embeddings=embedding, n_results=k * 3)

        if not results["ids"][0]:
            return []

        candidates = [
            SearchResult(
                text=doc,
                metadata=meta,
                score=1 - dist,
                doc_id=doc_id,
            )
            for doc_id, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

        # Rerank with cross-encoder
        ce = _get_cross_encoder(self.device)
        pairs = [(query, r.text) for r in candidates]
        scores = ce.predict(pairs)

        reranked = []
        for result, score in zip(candidates, scores):
            s = float(score)
            if math.isnan(s):
                s = result.score
            reranked.append(SearchResult(
                text=result.text,
                metadata=result.metadata,
                score=s,
                doc_id=result.doc_id,
            ))

        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked[:k]

    def reset(self) -> None:
        self.client.delete_collection("naive_rerank_benchmark")
        self.collection = self.client.get_or_create_collection(
            name="naive_rerank_benchmark",
            metadata={"hnsw:space": "cosine"},
        )
