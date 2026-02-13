"""Tests for vector store operations."""
import pytest
from pathlib import Path
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.database.interface import Chunk
from candlekeep.config import Settings


@pytest.fixture
def store():
    """Create test vector store."""
    settings = Settings.from_env()
    return ChromaVectorStore(settings)


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing."""
    return [
        Chunk(
            text="Vector databases use embeddings for similarity search",
            metadata={"source": "test.md", "filename": "test.md", "category": "database"},
            chunk_index=0
        ),
        Chunk(
            text="Document processing involves chunking and metadata extraction",
            metadata={"source": "test.md", "filename": "test.md", "category": "processing"},
            chunk_index=1
        )
    ]


def test_add_and_search(store, sample_chunks):
    """Test adding documents and searching."""
    # Add documents
    count = store.add_documents(sample_chunks, collection="test")
    assert count == 2
    
    # Search
    results = store.search("embeddings similarity", n_results=1)
    assert len(results) > 0
    assert "embeddings" in results[0].text.lower() or "vector" in results[0].text.lower()
    
    # Cleanup
    store.delete_by_source("test.md")


def test_category_filtering(store, sample_chunks):
    """Test category-based filtering."""
    store.add_documents(sample_chunks, collection="test")
    
    # Search with category filter
    results = store.search("database", n_results=5, category="database")
    assert len(results) > 0
    
    # Cleanup
    store.delete_by_source("test.md")


def test_delete_document(store, sample_chunks):
    """Test document deletion."""
    store.add_documents(sample_chunks, collection="test")
    
    # Delete
    deleted = store.delete_by_source("test.md")
    assert deleted == 2
    
    # Verify deletion
    results = store.search("embeddings", n_results=5)
    matching = [r for r in results if r.metadata.get("source") == "test.md"]
    assert len(matching) == 0


def test_list_documents(store, sample_chunks):
    """Test listing documents."""
    store.add_documents(sample_chunks, collection="test")
    
    docs = store.list_documents()
    test_docs = [d for d in docs if d["source"] == "test.md"]
    assert len(test_docs) == 1
    assert test_docs[0]["chunks"] == 2
    
    # Cleanup
    store.delete_by_source("test.md")


def test_get_stats(store):
    """Test statistics retrieval."""
    stats = store.get_stats()
    
    assert "total_chunks" in stats
    assert "total_documents" in stats
    assert "database_size_human" in stats
    assert isinstance(stats["total_chunks"], int)
