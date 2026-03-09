"""Tests for search functionality."""
import pytest
from candlekeep.rag.search import preprocess_negation, search_with_preprocessing
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.database.interface import Chunk
from candlekeep.config import Settings

pytestmark = [pytest.mark.integration]


def test_negation_preprocessing():
    """Test negation clause removal."""
    test_cases = [
        ("query without negation", "query"),
        ("search not using keywords", "search"),
        ("find except specific items", "find"),
        ("results excluding certain types", "results"),
        ("normal query", "normal query"),
    ]
    
    for input_query, expected in test_cases:
        result = preprocess_negation(input_query)
        assert result == expected, f"Failed for: {input_query}"


def test_negation_preprocessing_preserves_content():
    """Test that preprocessing doesn't remove too much."""
    query = "vector database concepts"
    result = preprocess_negation(query)
    assert result == query


def test_negation_preprocessing_multiple_clauses():
    """Test handling multiple negation clauses."""
    query = "search without filters not using keywords"
    result = preprocess_negation(query)
    assert result == "search"


@pytest.fixture
def store_with_data():
    """Create store with test data."""
    settings = Settings.from_env()
    store = ChromaVectorStore(settings)
    
    chunks = [
        Chunk(
            text="Vector databases store embeddings for similarity search",
            metadata={"source": "test1.md", "filename": "test1.md", "title": "Vector Databases"},
            chunk_index=0
        ),
        Chunk(
            text="Document processing involves chunking text into smaller pieces",
            metadata={"source": "test2.md", "filename": "test2.md", "title": "Document Processing"},
            chunk_index=0
        )
    ]
    
    store.add_documents(chunks, collection="test")
    yield store
    
    # Cleanup
    store.delete_by_source("test1.md")
    store.delete_by_source("test2.md")


def test_search_with_preprocessing(store_with_data):
    """Test search with automatic preprocessing."""
    # Query with negation
    results = search_with_preprocessing(
        store_with_data,
        "vector databases without processing",
        n_results=1
    )
    
    assert len(results) > 0
    # Should find vector databases doc, not processing doc
    assert "vector" in results[0].text.lower() or "embeddings" in results[0].text.lower()


def test_search_title_boosting(store_with_data):
    """Test that title matching boosts results."""
    results = store_with_data.search("Vector Databases", n_results=2)
    
    assert len(results) > 0
    # Document with matching title should rank higher
    top_result = results[0]
    assert "vector" in top_result.text.lower() or "Vector Databases" in top_result.metadata.get("title", "")
