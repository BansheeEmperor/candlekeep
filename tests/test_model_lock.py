"""Unit tests for the MPS model-call lock."""
import contextlib
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from candlekeep.database.embeddings import EmbeddingManager
from candlekeep.model_lock import _MPS_LOCK, MPS_SLICE, _FairRLock, call_in_slices, model_call_lock

pytestmark = [pytest.mark.unit]


def _lock_held_elsewhere() -> bool:
    """Whether another thread holds _MPS_LOCK right now (probes from a fresh thread)."""
    result = []

    def probe():
        got = _MPS_LOCK.acquire(blocking=False)
        if got:
            _MPS_LOCK.release()
        result.append(not got)

    t = threading.Thread(target=probe)
    t.start()
    t.join(timeout=5)
    return result == [True]


class TestModelCallLock:
    @pytest.mark.parametrize("device", ["mps", "mps:0", torch.device("mps"), torch.device("mps", 0)])
    def test_mps_devices_share_one_lock(self, device):
        assert model_call_lock(device) is _MPS_LOCK

    @pytest.mark.parametrize("device", ["cpu", "cuda:0", torch.device("cpu"), torch.device("cuda", 0)])
    def test_other_devices_take_no_lock(self, device):
        assert isinstance(model_call_lock(device), contextlib.nullcontext)


def _two_threads_meet(device, timeout: float) -> bool:
    """Whether two threads embedding at once are inside encode at the same time."""
    barrier = threading.Barrier(2, timeout=timeout)
    met = []

    class FakeModel:
        def __init__(self):
            self.device = device

        def encode(self, texts, convert_to_numpy=True):
            try:
                barrier.wait()
                met.append(True)
            except threading.BrokenBarrierError:
                met.append(False)
            return np.zeros((len(texts), 3))

    em = EmbeddingManager.__new__(EmbeddingManager)
    em.settings = SimpleNamespace(embedding_model="bge-small")
    model = FakeModel()
    em.get_model = lambda name=None: model
    threads = [threading.Thread(target=em.embed, args=(["text"],)) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert len(met) == 2
    return all(met)


def test_mps_encodes_run_one_at_a_time():
    assert _two_threads_meet(torch.device("mps", 0), timeout=0.5) is False


def test_cpu_encodes_are_not_serialised():
    assert _two_threads_meet(torch.device("cpu"), timeout=5) is True


@pytest.mark.parametrize("device, locked", [(torch.device("mps", 0), True), (torch.device("cpu"), False)])
def test_reranker_holds_the_lock_only_on_mps(monkeypatch, device, locked):
    from candlekeep.database.interface import SearchResult
    from candlekeep.rag import reranker
    held = []

    class FakeEncoder:
        def __init__(self):
            self.device = device

        def predict(self, pairs):
            held.append(_lock_held_elsewhere())
            return [0.0 for _ in pairs]

    monkeypatch.setattr(reranker, "_get_cross_encoder", lambda *a, **k: FakeEncoder())
    reranker.rerank_results("q", [SearchResult(text="t", metadata={}, score=0.1, doc_id="d")], device=str(device))
    assert held == [locked]


def test_model_construction_holds_the_lock(monkeypatch, tmp_path):
    from candlekeep.database import embeddings
    (tmp_path / "models--BAAI--bge-small-en-v1.5").mkdir()
    held = []

    def fake_model(*args, **kwargs):
        held.append(_lock_held_elsewhere())
        return SimpleNamespace(device=torch.device("mps", 0))

    monkeypatch.setattr(embeddings, "SentenceTransformer", fake_model)
    em = EmbeddingManager.__new__(EmbeddingManager)
    em.settings = SimpleNamespace(embedding_model="bge-small", models_dir=tmp_path, device="mps")
    em._model = em._current_model = None
    em.get_model()
    assert held == [True]


def test_cross_encoder_construction_holds_the_lock(monkeypatch, tmp_path):
    from candlekeep.rag import reranker
    held = []

    def fake_encoder(*args, **kwargs):
        held.append(_lock_held_elsewhere())
        return SimpleNamespace(device=torch.device("mps", 0))

    monkeypatch.setattr(reranker, "CrossEncoder", fake_encoder)
    monkeypatch.setattr(reranker.Settings, "from_env", staticmethod(lambda: SimpleNamespace(models_dir=tmp_path)))
    monkeypatch.setattr(reranker, "_cross_encoder", None)
    monkeypatch.setattr(reranker, "_cross_encoder_key", None)
    first = reranker._get_cross_encoder("some/model", "mps")
    assert reranker._get_cross_encoder("some/model", "mps") is first   # cached
    assert held == [True]


class TestFairRLock:
    def test_reentrant(self):
        lock = _FairRLock()
        with lock:
            with lock:
                pass
        assert lock.acquire(blocking=False)
        lock.release()

    def test_hands_over_in_arrival_order(self):
        lock = _FairRLock()
        order = []
        lock.acquire()
        threads = []
        for k in range(3):
            def take(k=k):
                with lock:
                    order.append(k)
            t = threading.Thread(target=take)
            t.start()
            threads.append(t)
            deadline = time.monotonic() + 5
            while len(lock._waiting) < k + 1 and time.monotonic() < deadline:   # thread k is queued
                time.sleep(0.001)
        lock.release()
        for t in threads:
            t.join(timeout=5)
        assert order == [0, 1, 2]

    def test_release_by_another_thread_fails(self):
        lock = _FairRLock()
        lock.acquire()
        errors = []
        t = threading.Thread(target=lambda: errors.append(pytest.raises(RuntimeError, lock.release)))
        t.start()
        t.join(timeout=5)
        lock.release()
        assert len(errors) == 1


    def test_interrupted_waiter_leaves_the_queue(self):
        lock = _FairRLock()
        lock.acquire()
        real_wait = lock._cond.wait
        calls = []

        def wait_once_then_fail(*a, **k):
            if not calls:
                calls.append(1)
                raise KeyboardInterrupt
            return real_wait(*a, **k)

        lock._cond.wait = wait_once_then_fail
        errors = []
        t = threading.Thread(target=lambda: errors.append(pytest.raises(KeyboardInterrupt, lock.acquire)))
        t.start()
        t.join(timeout=5)
        lock._cond.wait = real_wait
        lock.release()
        assert errors and not lock._waiting
        got = []
        t2 = threading.Thread(target=lambda: got.append(lock.acquire(blocking=True)) or lock.release())
        t2.start()
        t2.join(timeout=5)
        assert got == [True]


class TestCallInSlices:
    def test_mps_runs_longest_first_slices_under_the_lock(self):
        items = ["x" * (i % 7 + 1) for i in range(2 * MPS_SLICE + 5)]
        calls = []

        def fn(batch):
            calls.append((len(batch), _lock_held_elsewhere()))
            return [len(s) for s in batch]

        out = call_in_slices(fn, items, torch.device("mps", 0))
        assert [n for n, _ in calls] == [MPS_SLICE, MPS_SLICE, 5]
        assert all(held for _, held in calls)
        assert list(out) == [len(s) for s in items]   # back in input order

    def test_other_devices_make_one_call(self):
        items = ["x"] * (3 * MPS_SLICE)
        calls = []
        out = call_in_slices(lambda batch: calls.append(len(batch)) or [0] * len(batch), items, torch.device("cpu"))
        assert calls == [len(items)] and len(out) == len(items)

    def test_slices_keep_rows_of_a_matrix(self):
        items = [f"text {i}" for i in range(MPS_SLICE + 3)]
        out = call_in_slices(lambda batch: np.array([[len(s), 1.0] for s in batch]), items, "mps")
        assert out.shape == (len(items), 2) and out[:, 0].tolist() == [len(s) for s in items]

    def test_a_short_call_waits_for_one_slice_not_the_whole_batch(self):
        items = [f"text {i}" for i in range(3 * MPS_SLICE)]
        events = []
        started = threading.Event()

        def slow(batch):
            events.append(("slice", time.monotonic()))
            started.set()
            time.sleep(0.05)
            return [0] * len(batch)

        long_call = threading.Thread(target=call_in_slices, args=(slow, items, "mps"))
        long_call.start()
        started.wait(timeout=5)
        call_in_slices(lambda batch: events.append(("short", time.monotonic())) or [0] * len(batch), ["q"], "mps")
        long_call.join(timeout=5)
        kinds = [k for k, _ in events]
        assert kinds.index("short") < len(kinds) - 1   # the short call ran before the batch's last slice

