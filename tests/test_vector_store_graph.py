
import pytest
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.database.graph_store import GraphStore
from candlekeep.config import Settings

@pytest.mark.unit
def test_chroma_vector_store_has_graph_store():
    settings = Settings.from_env()
    # Use a dummy chroma_path to trigger PersistentClient but not a real connection failure
    settings.chroma_path = "/tmp/dummy_chroma"
    store = ChromaVectorStore(settings)
    
    assert hasattr(store, "graph_store")
    assert isinstance(store.graph_store, GraphStore)
