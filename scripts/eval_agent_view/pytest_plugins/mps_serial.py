"""pytest plugin that serialises model calls in a CI run (protocol section 16, C-14).

On MPS, two threads calling a sentence-transformers model at the same time abort
the process with a Metal assertion. In the CI selection this happens when the
Rosetta Seal background rebuild embeds while the test thread embeds a query; the
code is the same in A, B and C. This plugin makes every SentenceTransformer.encode
and CrossEncoder.predict call hold one process-wide lock, so model calls run one at
a time. Inputs, models and outputs are unchanged; only their overlap is removed.

Loaded with `-p mps_serial` by `drive.py ci --serialize-models` (round 1: the
informational run only, never the pre-registered one), and by `drive.py ci` for every
state whose round file lists it under ci_plugins (round 2: A, whose code has no
model-call lock; B and C have one and run the command as written).
"""
import functools
import threading

_LOCK = threading.RLock()


def _serialised(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with _LOCK:
            return fn(*args, **kwargs)
    wrapper.__mps_serial__ = True
    return wrapper


def pytest_configure(config):
    from sentence_transformers import CrossEncoder, SentenceTransformer
    for cls, name in ((SentenceTransformer, "encode"), (CrossEncoder, "predict")):
        fn = getattr(cls, name)
        if not getattr(fn, "__mps_serial__", False):
            setattr(cls, name, _serialised(fn))
    config.stash_mps_serial = True


def pytest_report_header(config):
    return "mps_serial: SentenceTransformer.encode and CrossEncoder.predict are serialised"
