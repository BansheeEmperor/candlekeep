"""Unit tests for collection self-healing, model cache location and the word cap."""
import tempfile
from pathlib import Path

import pytest

from candlekeep.config import Settings, get_models_dir
from candlekeep.database import vector_store as vs
from candlekeep.database.vector_store import ChromaVectorStore

pytestmark = [pytest.mark.unit]


class _Collection:
    def __init__(self, cid, fail_with=None):
        self.id = cid
        self.fail_with = fail_with

    def count(self):
        if self.fail_with:
            raise self.fail_with
        return 42


class _Client:
    """Hands out a fresh, healthy collection on every lookup."""

    def __init__(self):
        self.opened = 0

    def get_or_create_collection(self, name, metadata):
        self.opened += 1
        return _Collection(f"new-{self.opened}")


def _store(first_error, attempts=3):
    store = object.__new__(ChromaVectorStore)
    store.settings = Settings()
    store.client = _Client()
    store.collection = _Collection("old", fail_with=first_error)
    store._reconnect_attempts = attempts
    store._reconnect_backoff = 0.0
    return store


class TestErrorClassification:
    def test_stale_collection_detected(self):
        assert vs._is_stale_collection(Exception("Collection [abc] does not exist."))

    def test_unrelated_error_not_stale(self):
        assert not vs._is_stale_collection(ValueError("bad where clause"))

    def test_connection_error_detected(self):
        assert vs._is_chroma_unavailable(Exception("Connection refused"))

    def test_unrelated_error_not_unavailable(self):
        assert not vs._is_chroma_unavailable(ValueError("bad where clause"))


class TestCollectionOp:
    def test_stale_collection_reresolved(self):
        store = _store(Exception("Collection [old] does not exist."))
        assert store._count() == 42
        assert store.collection.id == "new-1"

    def test_unavailable_retried(self):
        store = _store(Exception("Could not connect to tenant"))
        assert store._count() == 42
        assert store.client.opened == 1

    def test_other_errors_reraised(self):
        store = _store(ValueError("bad where clause"))
        with pytest.raises(ValueError):
            store._count()
        assert store.client.opened == 0


class TestModelsDir:
    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CANDLEKEEP_MODELS_DIR", str(tmp_path / "m"))
        assert get_models_dir() == tmp_path / "m"

    def test_default_outside_data_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CANDLEKEEP_MODELS_DIR", raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        settings = Settings(data_dir=tmp_path / "data")
        assert settings.models_dir == tmp_path / "cache" / "candlekeep" / "models"

    def test_existing_cache_in_data_dir_kept(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CANDLEKEEP_MODELS_DIR", raising=False)
        legacy = tmp_path / "data" / "models"
        (legacy / "models--some-model").mkdir(parents=True)
        settings = Settings(data_dir=tmp_path / "data")
        assert settings.models_dir == legacy


def _long_doc(words):
    body = " ".join(["word"] * words)
    return (
        "---\ntitle: \"Long\"\ndescription: \"Long doc\"\nkeywords: [\"long\"]\n---\n\n"
        f"# Long\n\n## Part\n\n{body}\n"
    )


class TestQualityMaxWords:
    def _check(self, monkeypatch, limit, words):
        from candlekeep.mcp import server
        monkeypatch.setattr(server._settings, "quality_max_words", limit)
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write(_long_doc(words))
        f.close()
        return server.check_document_quality(Path(f.name))

    def test_default_cap_rejects(self, monkeypatch):
        issues = self._check(monkeypatch, 10000, 12000)
        assert any("too long" in i.lower() for i in issues)

    def test_raised_cap_accepts(self, monkeypatch):
        issues = self._check(monkeypatch, 50000, 12000)
        assert not any("too long" in i.lower() for i in issues)

    def test_zero_disables_cap(self, monkeypatch):
        issues = self._check(monkeypatch, 0, 12000)
        assert not any("too long" in i.lower() for i in issues)
