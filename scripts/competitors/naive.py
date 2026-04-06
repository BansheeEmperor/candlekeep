"""Naive vector search competitor."""
from pathlib import Path
import chromadb
from candlekeep.database.interface import SearchResult
from scripts.competitors.base import Competitor, CHUNK_SIZE, CHUNK_OVERLAP, _parse_frontmatter

class NaiveVectorSearch(Competitor):
    """Naive vector search using ChromaDB and sentence-transformers."""

    name = "naive"

    def __init__(self):
        # Use ephemeral client to avoid state pollution
        self._client = chromadb.Client()
        self._collection = self._client.create_collection("naive_bench")

    def ingest(self, doc_paths: list[Path]) -> int:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")
        
        chunk_texts = []
        chunk_metadatas = []
        chunk_ids = []
        
        for path in doc_paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            frontmatter, content = _parse_frontmatter(text)
            
            # Very simple fixed-size chunking
            for i in range(0, len(content), CHUNK_SIZE - CHUNK_OVERLAP):
                chunk = content[i : i + CHUNK_SIZE]
                if len(chunk) < 10:
                    continue
                
                metadata = {"source": str(path), "filename": path.name, "chunk_index": i}
                metadata.update(frontmatter)
                
                chunk_texts.append(chunk)
                chunk_metadatas.append(metadata)
                chunk_ids.append(f"{path.name}_{i}")
        
        if chunk_texts:
            embeddings = model.encode(chunk_texts, normalize_embeddings=True).tolist()
            self._collection.add(
                ids=chunk_ids,
                documents=chunk_texts,
                metadatas=chunk_metadatas,
                embeddings=embeddings
            )
        return len(chunk_texts)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")
        query_embedding = model.encode([query], normalize_embeddings=True).tolist()
        
        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=k
        )
        
        output = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                output.append(SearchResult(
                    text=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    score=float(results["distances"][0][i]),
                    doc_id=results["ids"][0][i]
                ))
        return output

    def reset(self) -> None:
        self._client.delete_collection("naive_bench")
        self._collection = self._client.create_collection("naive_bench")
