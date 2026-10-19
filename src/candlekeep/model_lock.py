"""One lock for every model call on Apple's MPS backend.

PyTorch's MPS backend is not thread-safe. When two threads run a model at the
same time, the process aborts with a Metal command-buffer assertion, or
segfaults. In Candlekeep that happens when a search embeds its query while an
ingest or the background normalisation rebuild is embedding, and when concurrent
precise searches rerank. Candlekeep's model loads and its SentenceTransformer.encode
and CrossEncoder.predict calls hold this lock on an MPS device; calls on CPU and
CUDA do not take it. Route new model calls through EmbeddingManager.embed or
rerank_results. The lock is per process: uvicorn workers are spawned processes,
each with its own MPS context (a server that forks after importing torch would
inherit a lock that may never be released).

Rule: this is a leaf lock. It is taken after _write_lock and _reranker_semaphore;
while holding it, never take another Candlekeep lock, call back into Candlekeep,
or wait on another thread.

Long calls (an ingest embeds all its chunks at once) run in slices of MPS_SLICE
inputs, one lock hold per slice, and the lock hands over in arrival order. A
search therefore waits for at most one slice of an ingest, not the whole ingest.
"""
import collections
import contextlib
import threading

import numpy as np

MPS_SLICE = 128   # inputs per lock hold; a multiple of sentence-transformers' batch size (32)


class _FairRLock:
    """A re-entrant lock that hands over in arrival order.

    CPython's locks do not hand off to waiters: a thread that releases and
    re-acquires at once, as an ingest does slice after slice, can keep the lock
    while others wait. This lock gives it to the longest-waiting thread instead.
    """

    def __init__(self):
        self._cond = threading.Condition(threading.Lock())
        self._owner = None
        self._depth = 0
        self._waiting = collections.deque()

    def acquire(self, blocking: bool = True) -> bool:
        me = threading.get_ident()
        with self._cond:
            if self._owner == me:
                self._depth += 1
                return True
            if self._owner is None and not self._waiting:
                self._owner, self._depth = me, 1
                return True
            if not blocking:
                return False
            self._waiting.append(me)
            try:
                while self._owner is not None or self._waiting[0] != me:
                    self._cond.wait()
            except BaseException:   # e.g. KeyboardInterrupt: leave the queue, or it stays blocked
                self._waiting.remove(me)
                self._cond.notify_all()
                raise
            self._waiting.popleft()
            self._owner, self._depth = me, 1
            return True

    def release(self) -> None:
        with self._cond:
            if self._owner != threading.get_ident():
                raise RuntimeError("cannot release a lock held by another thread")
            self._depth -= 1
            if self._depth == 0:
                self._owner = None
                self._cond.notify_all()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


_MPS_LOCK = _FairRLock()


def model_call_lock(device) -> contextlib.AbstractContextManager:
    """The lock to hold around a model call on device ("mps", "mps:0" or a torch.device)."""
    return _MPS_LOCK if str(device).startswith("mps") else contextlib.nullcontext()


def _input_length(item) -> int:
    """Length the way sentence-transformers sorts inputs: characters of a text, or of a pair."""
    return len(item) if isinstance(item, str) else sum(len(x) for x in item)


def call_in_slices(fn, items: list, device, size: int = MPS_SLICE) -> np.ndarray:
    """fn(items) for a batched model call (encode, predict), holding the device's lock.

    On MPS, inputs over size run as slices of size, each under its own lock hold.
    The slices follow the model's own longest-first order and are multiples of its
    batch size, so it builds the same batches as for one call, up to the order of
    inputs of equal length. Outputs come back in input order. On the Centurion
    corpus (2,955 chunks) the embeddings, and 300 reranker scores, are bitwise
    equal to a single call's.
    """
    lock = model_call_lock(device)
    if lock is not _MPS_LOCK or len(items) <= size:
        with lock:
            return np.asarray(fn(items))
    order = sorted(range(len(items)), key=lambda i: -_input_length(items[i]))
    out = [None] * len(items)
    for start in range(0, len(order), size):
        idx = order[start:start + size]
        with lock:
            part = fn([items[i] for i in idx])
        for i, value in zip(idx, part):
            out[i] = value
    return np.asarray(out)
