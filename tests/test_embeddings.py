
import pytest
import unittest
from unittest.mock import MagicMock, patch
from candlekeep.database.embeddings import EmbeddingManager
from candlekeep.config import Settings

pytestmark = [pytest.mark.unit]

class TestEmbeddingCache(unittest.TestCase):
    def setUp(self):
        # Reset singleton for testing
        EmbeddingManager._instance = None
        self.settings = Settings.from_env()
        self.settings.embedding_cache_size = 100
        self.manager = EmbeddingManager.get_instance(self.settings)

    def test_cache_hits_misses(self):
        # Mock the actual embedding generation to verify cache behavior
        with patch.object(EmbeddingManager, 'embed') as mock_embed:
            # Return a dummy embedding
            mock_embed.return_value = [[0.1, 0.2, 0.3]]
            
            query = "test query"
            
            # First call - should be a miss
            emb1 = self.manager.embed_query(query)
            stats = self.manager.get_cache_stats()
            self.assertEqual(stats["embedding_cache_hits"], 0)
            self.assertEqual(stats["embedding_cache_misses"], 1)
            self.assertEqual(stats["embedding_cache_size"], 1)
            self.assertEqual(mock_embed.call_count, 1)
            
            # Second call with same query - should be a hit
            emb2 = self.manager.embed_query(query)
            stats = self.manager.get_cache_stats()
            self.assertEqual(stats["embedding_cache_hits"], 1)
            self.assertEqual(stats["embedding_cache_misses"], 1)
            self.assertEqual(stats["embedding_cache_size"], 1)
            self.assertEqual(mock_embed.call_count, 1) # Should not have called embed again
            
            self.assertEqual(emb1, emb2)

    def test_cache_lru_eviction(self):
        # Set max cache size to 2 for testing
        self.manager._max_cache_size = 2
        
        with patch.object(EmbeddingManager, 'embed') as mock_embed:
            mock_embed.side_effect = lambda texts, model_name=None, is_query=False: [[float(len(texts[0]))]]
            
            self.manager.embed_query("q1") # Size 1
            self.manager.embed_query("q2") # Size 2
            self.manager.embed_query("q3") # Size 2 (evicts q1)
            
            stats = self.manager.get_cache_stats()
            self.assertEqual(stats["embedding_cache_size"], 2)
            self.assertEqual(stats["embedding_cache_misses"], 3)
            
            # q1 should be evicted, so calling it again should be a miss
            self.manager.embed_query("q1")
            stats = self.manager.get_cache_stats()
            self.assertEqual(stats["embedding_cache_misses"], 4)
            self.assertEqual(stats["embedding_cache_hits"], 0)

    def test_cache_key_with_model_name(self):
        with patch.object(EmbeddingManager, 'embed') as mock_embed:
            mock_embed.return_value = [[0.1]]
            
            query = "test query"
            # Explicitly use different model names
            self.manager.embed_query(query, model_name="minilm")
            self.manager.embed_query(query, model_name="nomic")
            
            stats = self.manager.get_cache_stats()
            self.assertEqual(stats["embedding_cache_misses"], 2)
            self.assertEqual(stats["embedding_cache_size"], 2)

    def test_cache_disabled_when_size_zero(self):
        self.manager._max_cache_size = 0
        with patch.object(EmbeddingManager, 'embed') as mock_embed:
            mock_embed.return_value = [[0.1]]
            
            self.manager.embed_query("q1")
            self.manager.embed_query("q1")
            
            stats = self.manager.get_cache_stats()
            self.assertEqual(stats["embedding_cache_hits"], 0)
            self.assertEqual(stats["embedding_cache_size"], 0)
            self.assertEqual(mock_embed.call_count, 2)

if __name__ == "__main__":
    unittest.main()
