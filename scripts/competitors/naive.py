"""Naive vector search competitor.

The floor: ChromaDB top-k with cosine similarity, no post-processing.
This is what you get from any RAG quickstart tutorial.
"""
from pathlib import Path

import chromadb

from candlekeep.database.interface import SearchResult
from scripts.competitors.base import (
    Competitor,
    get_shared_embedding_model,
    shared_chunk_document,
    generate_chunk_id,
)


class NaiveVectorSearch(Competitor):
    """Raw ChromaDB top-k search. No expansion, no reranking, no filtering."""

    name = "naive"

    def __init__(self, db_path: str | None = None):
        self.client = chromadb.Client() if db_path is None else chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="naive_benchmark",
            metadata={"hnsw:space": "cosine"},
        )
        self.model = get_shared_embedding_model()

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
        embedding = self.model.encode([query], convert_to_numpy=True).tolist()
        results = self.collection.query(query_embeddings=embedding, n_results=k)

        if not results["ids"][0]:
            return []

        return [
            SearchResult(
                text=doc,
                metadata=meta,
                score=1 - dist,  # cosine distance → similarity
                doc_id=doc_id,
            )
            for doc_id, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def reset(self) -> None:
        self.client.delete_collection("naive_benchmark")
        self.collection = self.client.get_or_create_collection(
            name="naive_benchmark",
            metadata={"hnsw:space": "cosine"},
        )
