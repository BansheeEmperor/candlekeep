"""Pytest fixtures for benchmark tests."""
import pytest
import tempfile
import shutil
from pathlib import Path

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor


@pytest.fixture(scope="session")
def temp_db_dir():
    """Create temporary database directory."""
    temp_dir = tempfile.mkdtemp(prefix="candlekeep_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_settings(temp_db_dir):
    """Create test settings with temporary database."""
    settings = Settings.from_env()
    settings.chroma_path = temp_db_dir
    return settings


@pytest.fixture(scope="session")
def vector_store(test_settings):
    """Create vector store with test settings."""
    return ChromaVectorStore(test_settings)


@pytest.fixture(scope="session")
def document_processor(test_settings):
    """Create document processor."""
    return DocumentProcessor(test_settings)


@pytest.fixture(scope="session")
def seeded_store(vector_store, document_processor):
    """Vector store seeded with test documents required by the benchmark."""
    from tests.benchmark_queries import BENCHMARK_QUERIES
    
    # Get set of all expected source paths from the benchmark queries
    expected_sources = set()
    for q in BENCHMARK_QUERIES:
        for src in q.expected_sources:
            # Normalize to filename only for easier matching if needed
            expected_sources.add(Path(src).name)
            
    test_docs = Path(__file__).parent / "fixtures" / "sample_docs"
    
    ingested_count = 0
    for doc_file in test_docs.glob("*"):
        if doc_file.is_file() and doc_file.name in expected_sources:
            chunks = document_processor.process(str(doc_file))
            vector_store.add_documents(chunks)
            ingested_count += 1
            
    return vector_store
