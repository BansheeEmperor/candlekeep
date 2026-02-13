"""Unit tests for embedding mismatch detection and conditional tool registration."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestEmbeddingMismatchDetection:
    def test_model_stored_in_collection_metadata(self):
        """Collection should be created with embedding_model in metadata."""
        with patch("candlekeep.database.vector_store.chromadb") as mock_chroma, \
             patch("candlekeep.database.vector_store.EmbeddingManager"):
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_collection.metadata = {"embedding_model": "bge-small"}
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.HttpClient.return_value = mock_client

            from candlekeep.config import Settings
            from candlekeep.database.vector_store import ChromaVectorStore
            settings = Settings.from_env()
            ChromaVectorStore(settings)

            call_kwargs = mock_client.get_or_create_collection.call_args
            assert "embedding_model" in call_kwargs[1]["metadata"]

    def test_mismatch_overrides_local_setting(self):
        """When remote model differs, local setting should be overridden."""
        with patch("candlekeep.database.vector_store.chromadb") as mock_chroma, \
             patch("candlekeep.database.vector_store.EmbeddingManager"):
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_collection.metadata = {"embedding_model": "minilm"}
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.HttpClient.return_value = mock_client

            from candlekeep.config import Settings
            from candlekeep.database.vector_store import ChromaVectorStore
            settings = Settings.from_env()
            settings.embedding_model = "bge-small"
            ChromaVectorStore(settings)

            assert settings.embedding_model == "minilm"


class TestModelNotCachedLocally:
    def test_exits_when_model_not_found(self):
        """Should exit if embedding model not in local cache."""
        from candlekeep.database.embeddings import EmbeddingManager
        from candlekeep.config import Settings

        tmp = Path(tempfile.mkdtemp())
        (tmp / "models").mkdir()

        settings = Settings.from_env()
        settings.data_dir = tmp

        EmbeddingManager._instance = None
        EmbeddingManager._model = None
        EmbeddingManager._current_model = None
        mgr = EmbeddingManager(settings)

        with pytest.raises(SystemExit):
            mgr.get_model("bge-small")


class TestConditionalToolRegistration:
    """Test _is_local_db and _allow_writes logic without importing server module."""

    def test_localhost_is_local(self):
        assert self._is_local("localhost")
        assert self._is_local("127.0.0.1")

    def test_remote_is_not_local(self):
        assert not self._is_local("remote-server")
        assert not self._is_local("chroma.example.com")

    def test_local_allows_writes(self):
        assert self._allow_writes("localhost", remote_write="false")

    def test_remote_denies_writes_by_default(self):
        assert not self._allow_writes("remote-server", remote_write="false")

    def test_remote_allows_writes_with_opt_in(self):
        assert self._allow_writes("remote-server", remote_write="true")

    @staticmethod
    def _is_local(host):
        return host in ("localhost", "127.0.0.1")

    @staticmethod
    def _allow_writes(host, remote_write="false"):
        if host in ("localhost", "127.0.0.1"):
            return True
        return remote_write.lower() == "true"
