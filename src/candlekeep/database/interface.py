"""Abstract database interface for candlekeep."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class SearchResult:
    """Search result from vector database."""
    text: str
    metadata: Dict[str, Any]
    score: float
    doc_id: str


@dataclass
class Chunk:
    """Document chunk for indexing."""
    text: str
    metadata: Dict[str, Any]
    chunk_index: int


class VectorDatabase(ABC):
    """Abstract interface for vector database operations."""
    
    @property
    @abstractmethod
    def graph_store(self) -> Any:
        """Access the associated graph database."""
        pass

    @graph_store.setter
    @abstractmethod
    def graph_store(self, value: Any) -> None:
        """Set the associated graph database."""
        pass

    @abstractmethod
    def search(self, query: str, n_results: int = 5, category: str | None = None) -> List[SearchResult]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def add_documents(self, chunks: List[Chunk], collection: str = "default") -> int:
        """Add document chunks to database."""
        pass
    
    @abstractmethod
    def delete_by_source(self, source: str) -> int:
        """Delete all chunks from a source."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all documents from database."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        pass
    
    @abstractmethod
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents."""
        pass

    @abstractmethod
    def get_chunks_by_source(self, source: str) -> List[SearchResult]:
        """Get all chunks from a specific source document."""
        pass

    @abstractmethod
    def get_all_chunks(self) -> List[SearchResult]:
        """Get all chunks from the database."""
        pass

    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Get cached embedding for a single query."""
        pass

    @abstractmethod
    def get_stored_embeddings_by_source(self, source: str) -> Dict[int, List[float]]:

        """Get stored embeddings for all chunks from a source document.

        Returns a dict mapping chunk_index to the embedding vector that was
        computed at ingestion time. This avoids re-computing embeddings at
        query time for similarity-weighted expansion.
        """
        pass
