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
