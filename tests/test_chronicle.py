"""Unit tests for the Chronicle (agent memory) store."""
import pytest
import chromadb

from candlekeep.database.chronicle import (
    Chronicle,
    ChronicleEntry,
    MIN_RELEVANCE_SCORE,
    _encode_tags,
    _decode_tags,
)

pytestmark = [pytest.mark.unit]


class _FakeEmbedder:
    """Deterministic embedder: maps known phrases to fixed unit vectors so
    cosine similarity is predictable without downloading a model.

    Vectors live in a small space; unknown text gets a near-orthogonal vector
    so it scores below the relevance Ward.
    """

    # 4-dim one-hot-ish vectors for a handful of topics
    _VECTORS = {
        "boot": [1.0, 0.0, 0.0, 0.0],
        "pcr": [0.96, 0.28, 0.0, 0.0],      # close to "boot"
        "network": [0.0, 1.0, 0.0, 0.0],
        "fixture": [0.0, 0.0, 1.0, 0.0],
    }
    _UNKNOWN = [0.0, 0.0, 0.0, 1.0]

    def _vec(self, text: str) -> list[float]:
        low = text.lower()
        for key, vec in self._VECTORS.items():
            if key in low:
                return vec
        return list(self._UNKNOWN)

    def embed(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, query, model_name=None):
        return self._vec(query)


@pytest.fixture
def chronicle(tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    return Chronicle(client, _FakeEmbedder())


# ── tag encoding helpers ──────────────────────────────────────────────────

def test_encode_decode_tags_roundtrip():
    assert _encode_tags(["boot", "pcr"]) == "boot,pcr"
    assert _decode_tags("boot,pcr") == ["boot", "pcr"]


def test_encode_tags_empty():
    assert _encode_tags([]) == ""
    assert _decode_tags("") == []


def test_encode_tags_strips_blanks():
    assert _encode_tags([" boot ", "", "  "]) == "boot"


# ── record + recall ────────────────────────────────────────────────────────

def test_record_and_recall(chronicle):
    entry = chronicle.record(
        "device fails to boot when firmware is stale",
        tags=["boot", "device"],
        category="failure-pattern",
        author="agent-7",
        created_at="2026-06-21T10:00:00+00:00",
    )
    assert isinstance(entry, ChronicleEntry)
    assert entry.id

    results = chronicle.recall("boot problem")
    assert len(results) == 1
    assert results[0].id == entry.id
    assert results[0].tags == ["boot", "device"]
    assert results[0].category == "failure-pattern"
    assert results[0].author == "agent-7"
    assert results[0].score >= MIN_RELEVANCE_SCORE


def test_recall_empty_store(chronicle):
    assert chronicle.recall("anything") == []


def test_recall_relevance_threshold(chronicle):
    # "network" memory is orthogonal to a "boot" query → filtered by the Ward
    chronicle.record("network timeout tuning", created_at="2026-06-21T10:00:00+00:00")
    results = chronicle.recall("boot failure")
    assert results == []


def test_recall_with_tag_filter(chronicle):
    chronicle.record("boot issue one", tags=["boot", "urgent"], created_at="2026-06-21T10:00:00+00:00")
    chronicle.record("boot issue two", tags=["boot"], created_at="2026-06-21T10:01:00+00:00")

    # Only the entry tagged BOTH boot AND urgent should match
    results = chronicle.recall("boot", tags=["boot", "urgent"])
    assert len(results) == 1
    assert results[0].text == "boot issue one"


def test_tag_filter_no_substring_match(chronicle):
    # A "reboot" tag must NOT match a filter for "boot"
    chronicle.record("reboot loop", tags=["reboot"], created_at="2026-06-21T10:00:00+00:00")
    results = chronicle.recall("boot", tags=["boot"])
    assert results == []


def test_recall_with_category_filter(chronicle):
    chronicle.record("boot tip", category="debug-tip", created_at="2026-06-21T10:00:00+00:00")
    chronicle.record("boot bug", category="failure-pattern", created_at="2026-06-21T10:01:00+00:00")

    results = chronicle.recall("boot", category="debug-tip")
    assert len(results) == 1
    assert results[0].text == "boot tip"


# ── entries (list) ──────────────────────────────────────────────────────────

def test_entries_newest_first(chronicle):
    chronicle.record("boot old", created_at="2026-06-21T10:00:00+00:00")
    chronicle.record("boot new", created_at="2026-06-21T12:00:00+00:00")
    chronicle.record("boot mid", created_at="2026-06-21T11:00:00+00:00")

    listed = chronicle.entries()
    assert [e.text for e in listed] == ["boot new", "boot mid", "boot old"]


def test_entries_respects_limit(chronicle):
    for i in range(5):
        chronicle.record(f"boot {i}", created_at=f"2026-06-21T10:0{i}:00+00:00")
    assert len(chronicle.entries(limit=3)) == 3


def test_entries_by_category(chronicle):
    chronicle.record("boot tip", category="debug-tip", created_at="2026-06-21T10:00:00+00:00")
    chronicle.record("boot bug", category="failure-pattern", created_at="2026-06-21T10:01:00+00:00")

    listed = chronicle.entries(category="debug-tip")
    assert len(listed) == 1
    assert listed[0].category == "debug-tip"


def test_entries_empty(chronicle):
    assert chronicle.entries() == []


# ── strike (delete) + count ──────────────────────────────────────────────────

def test_strike(chronicle):
    entry = chronicle.record("boot note", created_at="2026-06-21T10:00:00+00:00")
    assert chronicle.count() == 1
    assert chronicle.strike(entry.id) is True
    assert chronicle.count() == 0


def test_strike_nonexistent(chronicle):
    assert chronicle.strike("deadbeef") is False


def test_count(chronicle):
    assert chronicle.count() == 0
    chronicle.record("boot a", created_at="2026-06-21T10:00:00+00:00")
    chronicle.record("network b", created_at="2026-06-21T10:01:00+00:00")
    assert chronicle.count() == 2


def test_isolation_from_main_collection(tmp_path):
    """A Chronicle uses its own 'memory' collection, separate from 'candlekeep'."""
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    chronicle = Chronicle(client, _FakeEmbedder())
    chronicle.record("boot memory", created_at="2026-06-21T10:00:00+00:00")

    # Simulate repopulate_database clearing only the main collection
    main = client.get_or_create_collection(name="candlekeep")
    main.add(ids=["x"], embeddings=[[0.1, 0.1, 0.1, 0.1]], documents=["doc"])
    client.delete_collection("candlekeep")

    # Memory survives
    assert chronicle.count() == 1
    names = {c.name for c in client.list_collections()}
    assert "memory" in names
    assert "candlekeep" not in names
