"""Tests for document processor."""
import pytest
from pathlib import Path
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.config import Settings


@pytest.fixture
def processor():
    """Create document processor."""
    settings = Settings.from_env()
    return DocumentProcessor(settings)


@pytest.fixture
def sample_docs_dir():
    """Get sample documents directory."""
    return Path(__file__).parent / "fixtures" / "sample_docs"


def test_process_markdown_with_frontmatter(processor, sample_docs_dir):
    """Test processing markdown with YAML frontmatter."""
    doc_path = sample_docs_dir / "vector-databases.md"
    chunks = processor.process(doc_path)
    
    assert len(chunks) > 0
    
    # Check metadata extraction
    first_chunk = chunks[0]
    assert first_chunk.metadata["title"] == "Introduction to Vector Databases"
    assert first_chunk.metadata["category"] == "database"
    assert "vector database" in first_chunk.metadata["keywords"]


def test_process_plain_text(processor, sample_docs_dir):
    """Test processing plain text file."""
    doc_path = sample_docs_dir / "plain-text.txt"
    chunks = processor.process(doc_path)
    
    assert len(chunks) > 0
    assert all(chunk.text.strip() for chunk in chunks)


def test_process_directory(processor, sample_docs_dir):
    """Test processing entire directory."""
    chunks = processor.process_directory(sample_docs_dir)
    
    assert len(chunks) > 0
    
    # Should have chunks from multiple files
    sources = set(chunk.metadata["source"] for chunk in chunks)
    assert len(sources) >= 3  # At least 3 sample files


def test_chunking_respects_size(processor):
    """Test that chunks respect configured size."""
    # Create long text
    long_text = "word " * 1000
    chunks = processor._chunk_text(long_text)
    
    # Most chunks should be around chunk_size
    for chunk in chunks[:-1]:  # Exclude last chunk
        assert len(chunk) <= processor.settings.chunk_size * 1.5


def test_markdown_header_chunking(processor):
    """Test chunking at markdown headers."""
    text = """# Header 1
Content for section 1.

## Header 2
Content for section 2.

### Header 3
Content for section 3."""
    
    chunks = processor._chunk_text(text)
    
    # Should create separate chunks for sections
    assert len(chunks) >= 3
    assert any("Header 1" in chunk for chunk in chunks)
