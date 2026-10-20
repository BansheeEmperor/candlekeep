#!/usr/bin/env python3
"""Independent verifier for the agent-view evaluation (protocol section 13).

The protocol is ``docs/AGENT_VIEW_EVALUATION.md``. This script shares no code
with the harness: it imports nothing from ``scripts/eval_agent_view/`` and
nothing from ``candlekeep`` except ``DocumentProcessor`` and ``Settings``, which
it loads in a subprocess running state B's interpreter to rebuild the CEN-G gold
chunks. Everything else (query records, metrics, statistics, criteria) is
re-derived here from the fixtures and the raw per-query rows.

Usage::

    verify.py --metrics-of FILE.json     print {"metrics": ...} recomputed from FILE
    verify.py --all [--render] [--check-doc]
    verify.py --render                   write verification/section15.md from summary.json
    verify.py --check-doc                diff section 15 of the protocol against the rendering
    verify.py --round FILE ...           any of the above for a later round (see below)

``--all`` runs V-01..V-07 and V-09 (V-08 is manual; a sample is written),
computes every number of section 15 and every criterion C-01..C-15, and writes
``verification/recomputed_<layer>_<file>.json``, ``verification/checks.json``,
``verification/spot_check_sample.json`` and ``summary.json`` under the results
root. Missing inputs are reported as ``missing``; the script never needs all
runs to exist.

Exit status: 0 when every automated check passes, 1 when any check fails,
2 when nothing fails but some inputs are missing or pending.

A later round of the protocol compares new states on the same suites. Its round file
(``--round FILE``, e.g. ``scripts/eval_agent_view/rounds/r2.json``) is read here as
data, with this script's own code, and sets: the refs of A and B (``STATE_REF``), C's
exact commit (``C_REF``, required; env/C.txt is still cross-checked against it), each
state's FastMCP version and the A and C checkouts, the default ``--root``, ``--doc``,
``--eval-home`` and ``--b-python`` (B's venv; B's checkout must be this repository), the
ingest document counts it lists, and the CI plugin rule: a state listed under
``ci_plugins`` must load exactly those pytest plugins (``-p``) in its CI command, every
other state none, and the run must record each plugin file's SHA-256 (``-k`` and
``--deselect`` stay forbidden; the informational ``ci_info/`` run is not subject to the
rule), and extra informational Layer 2 runs (``info_runs``: a state at another
``CANDLEKEEP_RESULT_CHARS`` on some suites, expected as
``L2/info_<state>_<chars>_<suite>.json``, checked like the other informational rows and
reported in section 15 next to its ``refs``, paired against the first). Every other
expectation is round 1's. With ``--round``, a ``--root`` or
``--eval-home`` that meets round 1's results or EVAL_HOME directories, another
``tests/results/agent_view_*`` tree or the A or C checkout is refused
(``round_isolation_problems``), and so is an empty ``--round`` value.

Where the data contract is silent, this verifier fixes the following
conventions (a V-05 mismatch on one of these points is a convention
difference to reconcile, not necessarily a computation error):

- MRR@5 uses the first 5 sources, also on BEIR (10 results).
- graded_ndcg_5 averages every CEN-G query with a non-empty graded_chunks
  dict (all 108, adversarial included), as BenchmarkRunner does.
- nDCG@10's ideal DCG uses the 10 highest qrel grades.
- goldtext_mean and goldshare_mean are computed for every suite (the contract
  restricts neither). A non-adversarial output whose parsed blocks all have
  empty bodies has goldshare 0.0 (no visible gold characters).
- The text of an empty (or all-whitespace) document has no shingles: it adds
  nothing to GoldText and is never visible for SupportVisible. A CEN-G gold
  chunk without shingles is skipped like an unresolvable key.
- Normalisation removes a backslash before _ * [ ] ( ) # . - ` | < > only.
- With no adversarial queries, adv_leak_count is 0 and adv_chars_mean is null.
  Per-query "leak" is null for non-adversarial queries. gpv_n is the number of
  eligible (non-adversarial, >= 1 gold chunk) queries: 0 outside CEN-G, where
  gpv and gpc are null.
- CEN-G gold chunks (``--gold-body``, default ``product``): chunk i of a
  document is chunk i of ``DocumentProcessor._chunk_text`` (512/50) applied to
  the body ``DocumentProcessor._parse_frontmatter`` keeps, i.e. the chunk the
  product indexed and the graded label refers to. It differs from the data
  contract's regex-stripped body only for documents whose YAML frontmatter fails
  to parse (the product then indexes the whole file). ``--gold-body contract``
  applies the contract's literal rule. A gold key whose chunk index does not
  exist is skipped and listed in checks.json.
- Raw outputs are split into lines on "\n" only.
- BEIR query order is queries.jsonl order restricted to test-qrels ids (equal
  to qrels order for both sets). BEIR category is only required not to be
  "adversarial", and gold_sources are compared as a multiset.
- multi_match_freq is the share over all results of a path. RQ3 uses the
  hybrid path. C-07, C-10, C-12 and C-13 cover all three paths of every suite.
- A criterion cell is computed only when every run it needs covers all of the
  suite's queries on that path; otherwise it is "missing". RQ1/RQ2 decisions
  stay "pending" until V-01..V-08 pass.
- Paired bootstrap: numpy default_rng(20261018), indices integers(0, n,
  (10000, n)), 2.5/97.5 percentiles of the resampled mean differences.
- CEN-A (section 16): the 78 non-adversarial CEN queries minus the two whose
  reference answer is empty (CEN-014, CEN-038), i.e. 76 queries; J1 has 228
  items, J1R round(0.2 x 228) = 46, J2 152.
- Chroma process (section 16, checked under V-02): every L1/L2 file records
  meta.chroma_process {pid, started, port} and an equal meta.chroma_process_end;
  per corpus, every protocol run of states A/B/C (reruns, kill switch and
  informational rows included) records the same process (files the protocol does
  not name are compared too, as warnings). Every L2 file records
  server_env.write_probe = "neutralised" (its server was started by serve.py).

Harness file formats read here (interfaces, not metric code):

- judges/: ``pack_<P>.json`` (list of {id, question, reference_answer,
  tool_output}), ``pack_<P>_part<k>.json``, ``keymap_<P>.json`` ({id:
  "qid|STATE"}; for the re-judge pack ``<P>R``: {R id: source id}) with
  ``.sha256`` sidecars, ``manifest_<P>.json``, judge outputs
  ``out_<P>_*.json`` (records {id, verdict, evidence}). Item ids are J#### (J1),
  K#### (J2), R#### (J1R).
  ``results_<P>.json`` (judge_pack.py's own unblinding) is cross-checked: its
  counts must equal the recomputation; a different set of non-verbatim items is
  a warning (this verifier splits evidence on " ... ", as the contract says).
- verification/ (CI step): ``ci_<S>.txt`` (a "# key: value" header, then the
  pytest log), ``ci_<S>.json`` (exit_code, command, git_sha, src_tree_sha,
  invalid, ...), ``ci_<S>_router_<path>_benchmark.json`` (A, B and C) and the
  ``compare_benchmarks.py`` renderings ``ci_<S>_compare_{A,archive}.md``.
  C-14 re-applies compare_benchmarks.py's rule (a drop of more than 0.01 in
  avg_precision or avg_recall is a red mark) to the router JSONs of every path
  in ``--ci-paths`` (default hybrid, precise, explore: the paths the project's
  CI compares) against A's run; a missing or zero baseline value is "missing".
  A's baseline run must itself complete (exit 0 and a pytest summary line); an
  aborted baseline fails the comparison closed (protocol section 16). The
  informational run under ``ci_info/verification/`` (model calls serialised,
  section 16) is compared with the same rule and reported, never decisive.
  A rendering's red-mark count must agree with the recomputation for the paths
  it shows.
- ingest/: the canonical record ``<I0x>_<name>.json`` (``*.replaced-*`` and
  ``*.failed`` records are ignored). When a result file's meta carries
  ``ingest_uuid`` / ``ingest_record_sha256`` they must equal the record's uuid
  and the record file's SHA-256; the data-directory marker named by the record
  must carry the same uuid.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

# ── Constants ────────────────────────────────────────────────────────

SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[2]
FIX = REPO / "tests" / "fixtures"
DEFAULT_ROOT = REPO / "tests" / "results" / "agent_view_eval"
DEFAULT_DOC = REPO / "docs" / "AGENT_VIEW_EVALUATION.md"
DEFAULT_EVAL_HOME = Path(os.environ.get("EVAL_HOME", str(Path.home() / ".cache" / "candlekeep-eval")))
DEFAULT_B_PYTHON = REPO / ".venv" / "bin" / "python"
ROUND1_ROOT, ROUND1_EVAL_HOME = DEFAULT_ROOT, DEFAULT_EVAL_HOME   # a run without --round (kept by apply_round)

SEED = 20261018
N_BOOT = 10_000
DELTA = 0.02            # non-inferiority margin (section 9)
TOL = 1e-9              # V-05 tolerance
DEAD_CHROMA = "http://127.0.0.1:65530"

PATHS = ("hybrid", "precise", "explore")
STATES = ("A", "B", "C")
SUITES = ("CEN", "CEN-G", "MH", "CD-LEG", "CD-MED", "CD-NAR", "CD-API", "CD-ALT", "BEIR-SF", "BEIR-NF")
CD_SUITES = ("CD-LEG", "CD-MED", "CD-NAR", "CD-API", "CD-ALT")
BEIR_SUITES = ("BEIR-SF", "BEIR-NF")
ADV_SUITES = ("CEN", "CEN-G") + CD_SUITES          # suites that contain adversarial queries
SUITE_CORPUS = {"CEN": "I01", "MH": "I01", "CEN-G": "I02", "CD-LEG": "I03", "CD-MED": "I04",
                "CD-NAR": "I05", "CD-API": "I06", "CD-ALT": "I07", "BEIR-SF": "I08", "BEIR-NF": "I09"}
CORPUS_SUITE = {"I01": "CEN", "I02": "CEN-G", "I03": "CD-LEG", "I04": "CD-MED", "I05": "CD-NAR",
                "I06": "CD-API", "I07": "CD-ALT", "I08": "BEIR-SF", "I09": "BEIR-NF"}
EXPECTED_N = {"CEN": 108, "CEN-G": 108, "MH": 30, "CD-LEG": 107, "CD-MED": 108, "CD-NAR": 108,
              "CD-API": 108, "CD-ALT": 104, "BEIR-SF": 300, "BEIR-NF": 323}
INGEST_DOCS = {"I01": 89, "I02": 89, "I03": 90, "I04": 91, "I05": 89, "I06": 95, "I07": 88,
               "I08": 5183, "I09": 3633}
CD_SPEC = {"CD-LEG": ("legal", "LEG"), "CD-MED": ("medical", "MED"), "CD-NAR": ("narrative", "NAR"),
           "CD-API": ("api_ref", "API"), "CD-ALT": ("alternating", "ALT")}
BEIR_SPEC = {"BEIR-SF": ("scifact", "SF"), "BEIR-NF": ("nfcorpus", "NF")}
_CEN_DIRS = (FIX / "sample_docs", FIX / "scale_docs")
CORPUS_DIRS = {"I01": _CEN_DIRS, "I02": _CEN_DIRS,
               "I03": (FIX / "cross_domain" / "legal_docs",),
               "I04": (FIX / "cross_domain" / "medical_docs",),
               "I05": (FIX / "cross_domain" / "narrative_docs",),
               "I06": (FIX / "cross_domain" / "api_ref_docs",),
               "I07": (FIX / "cross_domain" / "alternating_docs",)}
SUPPORTED_EXT = {".txt", ".md", ".pdf", ".rst", ".json", ".yaml", ".yml"}  # DocumentProcessor's set
STATE_REF = {"A": "6519cc7", "B": "d524652"}
C_REF = None              # C's exact commit: round 1 reads it from env/C.txt; a round file pins it
FASTMCP_VERSION = {"A": "2.14.5", "B": "3.4.9", "C": "3.4.9"}
STATE_CHECKOUT: dict = {}  # A and C checkouts; round 1: <eval home>/worktrees/{A,C}; a round file names them
CI_PLUGINS = None         # round 1: not checked; a round file: {state: the -p plugins its CI command must load}
INFO_RUNS: list = []      # a round file's extra informational L2 runs (L2/info_<state>_<result_chars>_<suite>.json)
ROUND = None              # the round file applied with --round (load_round's dict)
QUERY_FIELDS = ("qid", "query", "category", "gold_sources", "graded_chunks", "graded_docs", "supporting")
N_RESULTS = {s: (10 if s in BEIR_SUITES else 5) for s in SUITES}
JUDGE_PACKS = {"J1": {"path": "hybrid", "states": ("A", "B", "C"), "optional": False, "rejudge": True},
               "J2": {"path": "precise", "states": ("B", "C"), "optional": True, "rejudge": False}}
REJUDGE_FRACTION = 0.2
# Section 16: CEN-014 and CEN-038 have empty reference answers and are not judged.
CEN_A_N = 76                                          # 78 non-adversarial CEN queries minus those two
CEN_A_EXCLUDED = ("CEN-014", "CEN-038")
JUDGE_N = {"J1": 228, "J2": 152}                      # CEN_A_N x states
REJUDGE_N = {"J1R": 46}                               # round(0.2 x 228)
CHROMA_PROCESS_KEYS = ("pid", "started", "port")      # meta.chroma_process (section 16)
VERDICTS = ("full", "partial", "none")
CI_MARK = "unit or (benchmark and not slow)"
CI_PATHS = ("hybrid", "precise", "explore")          # the paths the project's CI compares
CI_METRICS = ("avg_precision", "avg_recall")          # compare_benchmarks.py's "precision"-type rows
CI_RED_DROP = 0.01                                    # compare_benchmarks.py: delta < -0.01 is red
CI_LABEL = {"hybrid": "Hybrid Path", "precise": "Precise Path", "explore": "Explore Path"}
VERIFY_GATE = ("V-01", "V-02", "V-03", "V-04", "V-05", "V-06", "V-07", "V-08")

L1_PQ = {"mrr_5": "rr", "ndcg_5": "ndcg5", "hit_1": "hit1", "hit_5": "hit5", "p_5": "p5",
         "graded_ndcg_5": "graded_ndcg5", "support_all_5": "support_all5",
         "ndcg_10": "ndcg10", "recall_10": "recall10"}
PRIMARY = {"CEN-G": "gpv", "MH": "support_visible"}       # every other suite: goldtext
PRIMARY_LABEL = {"gpv": "GPV", "support_visible": "SupportVisible", "goldtext": "GoldText"}

STATUS_ORDER = {"pass": 0, "warn": 1, "pending": 2, "missing": 3, "fail": 4}


def primary_of(suite: str) -> str:
    return PRIMARY.get(suite, "goldtext")


# ── Generic helpers ──────────────────────────────────────────────────

def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def load_json_safe(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "missing"
    except Exception as e:  # noqa: BLE001 - report, never crash
        return None, f"unreadable: {type(e).__name__}: {e}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (set, frozenset, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def write_json(path: Path, obj) -> None:
    # A round must never write round 1's results (round_isolation_problems guards the roots it
    # is given; this guards every write, including one made by code that builds its own root).
    if ROUND is not None and within(Path(path), ROUND1_ROOT):
        raise SystemExit(f"refusing to write {path} in round {ROUND['name']!r}: it lies in round 1's results root")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, default=_json_default)
        f.write("\n")
    os.replace(tmp, path)


def is_num(x) -> bool:
    return isinstance(x, (int, float, np.integer, np.floating))


def values_equal(a, b, tol: float = TOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if is_num(a) and is_num(b):
        fa, fb = float(a), float(b)
        if math.isnan(fa) or math.isnan(fb):
            return math.isnan(fa) and math.isnan(fb)
        return abs(fa - fb) <= tol
    return a == b


def mean(vals):
    vals = [float(v) for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def pct(vals, q):
    vals = [float(v) for v in vals if v is not None]
    if not vals:
        return None
    return float(np.percentile(np.asarray(vals, dtype=float), q))


def basename(p) -> str:
    return str(p).replace("\\", "/").rsplit("/", 1)[-1]


def worst(statuses) -> str:
    statuses = list(statuses)
    if not statuses:
        return "missing"
    return max(statuses, key=lambda s: STATUS_ORDER.get(s, 4))


def item(name: str, status: str, detail="") -> dict:
    return {"name": name, "status": status, "detail": detail}


def check_status(items) -> str:
    """Overall status of a check from its items: fail > missing > pending > pass (warn counts as pass)."""
    if not items:
        return "missing"
    w = worst(i["status"] for i in items)
    return "pass" if w == "warn" else w


def git(repo: Path, *args, timeout: int = 60):
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return None, str(e), -1
    return p.stdout.strip(), p.stderr.strip(), p.returncode


def git_out(repo: Path, *args):
    out, _err, rc = git(repo, *args)
    return out if rc == 0 else None


def norm_pkg(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# ── Text normalisation and shingles (data contract) ─────────────────

_ESC_RE = re.compile(r"\\([_*\[\]()#.\-`|<>])")
_WS_RE = re.compile(r"\s+")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)   # DocumentProcessor.FRONTMATTER_PATTERN
SHINGLE_LEN = 150
SHINGLE_STEP = 25


def normalise(text: str) -> str:
    text = _ESC_RE.sub(r"\1", text)
    text = _WS_RE.sub(" ", text)
    return text.lower().strip()


def shingles(text: str) -> frozenset:
    s = normalise(text)
    if not s:
        return frozenset()          # an empty text has no shingles (see module docstring)
    if len(s) < SHINGLE_LEN:
        return frozenset([s])
    return frozenset(s[i:i + SHINGLE_LEN] for i in range(0, len(s) - SHINGLE_LEN + 1, SHINGLE_STEP))


def strip_frontmatter(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    return text[m.end():] if m else text


def read_doc(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ── Query records re-derived from the fixtures ──────────────────────

def _query_list(obj):
    if isinstance(obj, dict) and "queries" in obj:
        return obj["queries"]
    return obj


def _record(qid, query, category, gold, graded_chunks=None, graded_docs=None, supporting=None) -> dict:
    return {"qid": qid, "query": query, "category": category, "gold_sources": gold,
            "graded_chunks": graded_chunks, "graded_docs": graded_docs, "supporting": supporting}


def _beir_queries(suite: str) -> list:
    name, prefix = BEIR_SPEC[suite]
    base = FIX / "beir" / name
    texts, order = {}, []
    with open(base / "queries.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            qid = str(d["_id"])
            if qid not in texts:
                order.append(qid)
            texts[qid] = d.get("text", "")
    rels: dict = {}
    with open(base / "qrels" / "test.tsv", encoding="utf-8") as f:
        for n, line in enumerate(f):
            cols = line.rstrip("\n").rstrip("\r").split("\t")
            if len(cols) < 3:
                continue
            if n == 0 and not re.fullmatch(r"-?\d+", cols[2].strip()):
                continue  # header row
            rels.setdefault(cols[0].strip(), []).append((cols[1].strip(), int(cols[2].strip())))
    out = []
    for qid in order:
        if qid not in rels:
            continue
        r = rels[qid]
        out.append(_record(f"{prefix}-{qid}", texts[qid], "beir",
                           [f"{d}.md" for d, g in r if g > 0],
                           graded_docs={f"{d}.md": g for d, g in r}))
    return out


_QCACHE: dict = {}


def derive_queries(suite: str) -> list:
    if suite in _QCACHE:
        return _QCACHE[suite]
    if suite in ("CEN", "CEN-G"):
        with open(FIX / "eval_suite_100.json", encoding="utf-8") as f:
            qs = _query_list(json.load(f))
        prefix = "CEN" if suite == "CEN" else "CENG"
        out = []
        for i, q in enumerate(qs, 1):
            graded = None
            if suite == "CEN-G":
                graded = {}
                for key, grade in (q.get("graded_relevance") or {}).items():
                    src, _, idx = str(key).rpartition(":")
                    graded[f"{basename(src)}:{idx}"] = grade
            out.append(_record(f"{prefix}-{i:03d}", q["query"], q.get("category"),
                               [basename(s) for s in q.get("expected_sources") or []],
                               graded_chunks=graded))
    elif suite == "MH":
        with open(FIX / "track2_multi_hop_queries.json", encoding="utf-8") as f:
            qs = _query_list(json.load(f))
        out = []
        for i, q in enumerate(qs, 1):
            docs = [basename(s) for s in q.get("supporting_docs") or []]
            out.append(_record(f"MH-{i:02d}", q["query"], "multihop", list(docs), supporting=list(docs)))
    elif suite in CD_SPEC:
        name, prefix = CD_SPEC[suite]
        with open(FIX / "cross_domain" / f"eval_suite_{name}.json", encoding="utf-8") as f:
            qs = _query_list(json.load(f))
        out = [_record(f"{prefix}-{i:03d}", q["query"], q.get("category"),
                       [basename(s) for s in q.get("expected_sources") or []])
               for i, q in enumerate(qs, 1)]
    elif suite in BEIR_SPEC:
        out = _beir_queries(suite)
    else:
        raise KeyError(f"unknown suite {suite!r}")
    _QCACHE[suite] = out
    return out


def cen_answers() -> list:
    with open(FIX / "eval_suite_with_answers.json", encoding="utf-8") as f:
        return _query_list(json.load(f))


def compare_queries(file_qs, derived: list, suite: str) -> list:
    """Return a list of human-readable differences between the file's records and the derivation."""
    issues = []
    if not isinstance(file_qs, list):
        return ["'queries' is not a list"]
    recs = [q for q in file_qs if isinstance(q, dict)]
    if len(recs) != len(file_qs):
        issues.append("non-object entries in 'queries'")
    f_ids = [q.get("qid") for q in recs]
    d_ids = [q["qid"] for q in derived]
    if len(f_ids) != len(set(f_ids)):
        issues.append("duplicate qids in 'queries'")
    if f_ids != d_ids:
        if set(f_ids) == set(d_ids):
            issues.append("qid order differs from fixture order")
        else:
            miss = [q for q in d_ids if q not in set(f_ids)]
            extra = [q for q in f_ids if q not in set(d_ids)]
            issues.append(f"qid sets differ: {len(miss)} missing {miss[:5]}, {len(extra)} extra {extra[:5]}")
    by_id = {q.get("qid"): q for q in recs}
    beir = suite in BEIR_SUITES
    bad = []
    for d in derived:
        f = by_id.get(d["qid"])
        if f is None:
            continue
        diff = []
        for key in QUERY_FIELDS:
            fv, dv = f.get(key, "<absent>"), d[key]
            if beir and key == "category":
                # The contract leaves the BEIR category unspecified; it only must not be adversarial.
                if not isinstance(fv, str) or fv == "adversarial":
                    diff.append(key)
                continue
            if beir and key == "gold_sources" and isinstance(fv, list):
                if sorted(map(str, fv)) != sorted(dv):
                    diff.append(key)
                continue
            if fv != dv:
                diff.append(key)
        extra_keys = sorted(set(f) - set(QUERY_FIELDS))
        if diff:
            bad.append(f"{d['qid']}: {','.join(diff)}")
        if extra_keys and len(issues) < 50:
            issues.append(f"{d['qid']}: extra keys {extra_keys}")
    if bad:
        issues.append(f"{len(bad)} records differ from the fixtures: {bad[:8]}")
    return issues


# ── Corpora: gold document text and CEN-G gold chunks ───────────────

class Corpus:
    """Gold-document bodies (frontmatter stripped) for one ingested corpus."""

    def __init__(self, cid: str, eval_home: Path):
        self.cid = cid
        self.paths: dict = {}
        self.jsonl_text: dict | None = None
        self.jsonl_title: dict | None = None
        self.staging_dir: Path | None = None
        self._sh: dict = {}
        if cid in ("I08", "I09"):
            suite = CORPUS_SUITE[cid]
            for cand in (eval_home / "staging" / cid, eval_home / "staging" / suite,
                         eval_home / "staging" / BEIR_SPEC[suite][0]):
                if cand.is_dir():
                    self.staging_dir = cand
                    break
            if self.staging_dir is not None:
                for p in sorted(self.staging_dir.rglob("*.md")):
                    self.paths.setdefault(p.name, p)
                self.origin = f"staging:{self.staging_dir}"
            else:
                self.origin = "corpus.jsonl (staging directory missing)"
        else:
            for d in CORPUS_DIRS[cid]:
                for p in sorted(d.rglob("*")):
                    if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
                        self.paths.setdefault(p.name, p)
            self.origin = "fixtures"

    def _load_jsonl(self):
        if self.jsonl_text is None:
            name = BEIR_SPEC[CORPUS_SUITE[self.cid]][0]
            self.jsonl_text, self.jsonl_title = {}, {}
            with open(FIX / "beir" / name / "corpus.jsonl", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        self.jsonl_text[f"{d['_id']}.md"] = d.get("text", "")
                        self.jsonl_title[f"{d['_id']}.md"] = d.get("title", "")

    def body(self, name: str):
        p = self.paths.get(name)
        if p is not None:
            return strip_frontmatter(read_doc(p))
        if self.cid in ("I08", "I09") and self.staging_dir is None:
            self._load_jsonl()
            return self.jsonl_text.get(name)
        return None

    def shingles(self, name: str) -> frozenset:
        if name not in self._sh:
            b = self.body(name)
            self._sh[name] = shingles(b) if b is not None else frozenset()
        return self._sh[name]


CHUNKER = r'''
import json, sys
req = json.load(open(sys.argv[1], encoding="utf-8"))
from candlekeep.config import Settings
from candlekeep.rag.processor import DocumentProcessor
import candlekeep.rag.processor as _proc
s = Settings(chunk_size=512, chunk_overlap=50, data_dir=req["data_dir"], vlm_provider="",
             llm_provider="", device="mps")
dp = DocumentProcessor(s)
out = {
    "module": _proc.__file__,
    "chunk_size": s.chunk_size, "chunk_overlap": s.chunk_overlap,
    "contract": {n: dp._chunk_text(b) for n, b in req["bodies"].items()},
    "product": {n: dp._chunk_text(dp._parse_frontmatter(t)[1]) for n, t in req["texts"].items()},
}
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(out, f)
'''


class GoldChunks:
    """CEN-G gold chunks from the product chunker at 512/50.

    mode "product" (default) chunks the body DocumentProcessor itself keeps (``_parse_frontmatter``): the
    chunks the product indexed at overlap 50, to which the graded labels' chunk indices refer. It differs
    from mode "contract" (the body left by the frontmatter regex, the data contract's literal wording)
    only when a document's YAML frontmatter fails to parse, so the product indexes the whole file.
    """

    def __init__(self, b_python: Path, mode: str = "product"):
        self.b_python = Path(b_python)
        self.mode = mode
        self.loaded = False
        self.error = None
        self.chunks: dict = {}
        self.product: dict = {}
        self.module = None
        self._sh: dict = {}
        self.unresolved: set = set()

    def load(self):
        if self.loaded:
            return
        self.loaded = True
        if not self.b_python.exists():
            self.error = f"state B interpreter not found: {self.b_python}"
            return
        texts = {}
        for d in _CEN_DIRS:
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
                    texts.setdefault(p.name, read_doc(p))
        bodies = {n: strip_frontmatter(t) for n, t in texts.items()}
        with tempfile.TemporaryDirectory(prefix="verify_chunks_") as tmp:
            req, out = Path(tmp) / "req.json", Path(tmp) / "out.json"
            data_dir = Path(tmp) / "ck_data"
            with open(req, "w", encoding="utf-8") as f:
                json.dump({"bodies": bodies, "texts": texts, "data_dir": str(data_dir)}, f)
            env = dict(os.environ)
            env.update({"CHROMA_URL": DEAD_CHROMA, "CANDLEKEEP_DATA_DIR": str(data_dir),
                        "CANDLEKEEP_DEVICE": "mps", "CANDLEKEEP_VLM_PROVIDER": "",
                        "CANDLEKEEP_LLM_PROVIDER": "", "CANDLEKEEP_TRANSPORT": "stdio",
                        "PYTHONDONTWRITEBYTECODE": "1"})       # write nothing under src/
            try:
                p = subprocess.run([str(self.b_python), "-I", "-c", CHUNKER, str(req), str(out)],
                                   env=env, cwd=tmp, capture_output=True, text=True, timeout=900)
            except Exception as e:  # noqa: BLE001
                self.error = f"chunker subprocess failed: {e}"
                return
            if p.returncode != 0 or not out.exists():
                self.error = f"chunker exited {p.returncode}: {p.stderr.strip()[-600:]}"
                return
            with open(out, encoding="utf-8") as f:
                res = json.load(f)
        self.chunks = res["contract"]
        self.product = res["product"]
        self.module = res.get("module")
        if res.get("chunk_size") != 512 or res.get("chunk_overlap") != 50:
            self.error = f"chunker ran with {res.get('chunk_size')}/{res.get('chunk_overlap')}"

    def text(self, name: str, idx: int):
        self.load()
        ch = (self.product if self.mode == "product" else self.chunks).get(name)
        if ch is None or not (0 <= idx < len(ch)):
            return None
        return ch[idx]

    def gold_sets(self, graded_chunks) -> list:
        """Shingle sets of the query's gold chunks (grade >= 2) that can be rebuilt."""
        self.load()
        out = []
        for key, grade in (graded_chunks or {}).items():
            try:
                if grade is None or float(grade) < 2:
                    continue
            except (TypeError, ValueError):
                continue
            name, _, idx = str(key).rpartition(":")
            try:
                idx_i = int(idx)
            except ValueError:
                self.unresolved.add(key)
                continue
            if key not in self._sh:
                t = self.text(name, idx_i)
                self._sh[key] = shingles(t) if t is not None else None
            if not self._sh[key]:          # chunk index absent, or a chunk without shingles
                self.unresolved.add(key)
                continue
            out.append(self._sh[key])
        return out


# ── Layer 1 metrics (semantics of src/candlekeep/eval/metrics.py) ───

def m_rr(retrieved, gold) -> float:
    for i, d in enumerate(retrieved):
        if d in gold:
            return 1.0 / (i + 1)
    return 0.0


def m_ndcg(retrieved, gold, k) -> float:
    if not gold:
        return 0.0
    uniq, seen = [], set()
    for d in retrieved[:k]:
        if d not in seen:
            uniq.append(d)
            seen.add(d)
    dcg = sum(1.0 / math.log2(i + 2) for i, d in enumerate(uniq[:k]) if d in gold)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg if idcg else 0.0


def m_hit(retrieved, gold, k) -> float:
    if not gold:
        return 1.0 if not retrieved else 0.0
    return 1.0 if any(d in gold for d in retrieved[:k]) else 0.0


def m_prec(retrieved, gold, k) -> float:
    if not retrieved:
        return 1.0 if not gold else 0.0
    kk = min(len(retrieved), k)
    return sum(1 for d in retrieved[:kk] if d in gold) / kk


def m_ndcg_graded(retrieved, grades: dict, k) -> float:
    if not grades:
        return 0.0
    dcg = 0.0
    for i, d in enumerate(retrieved[:k]):
        g = grades.get(d, 0)
        if g > 0:
            dcg += g / math.log2(i + 2)
    ideal = sorted(grades.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal) if g > 0)
    return dcg / idcg if idcg else 0.0


def _dedupe(seq):
    out, seen = [], set()
    for d in seq:
        if d not in seen:
            out.append(d)
            seen.add(d)
    return out


def m_beir_ndcg10(sources, grades: dict) -> float:
    top = _dedupe(sources)[:10]
    dcg = sum(float(grades.get(d, 0)) / math.log2(rank + 1) for rank, d in enumerate(top, 1) if grades.get(d, 0) > 0)
    ideal = sorted((float(g) for g in grades.values() if g > 0), reverse=True)[:10]
    idcg = sum(g / math.log2(rank + 1) for rank, g in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def m_beir_recall10(sources, grades: dict) -> float:
    rel = {d for d, g in grades.items() if g > 0}
    if not rel:
        return 0.0
    return len(rel & set(_dedupe(sources)[:10])) / len(rel)


def index_rows(rows):
    """{(path, qid): first row}, plus duplicate keys and rows with an unknown path."""
    idx, dups, unknown = {}, [], []
    for r in rows or []:
        if not isinstance(r, dict):
            unknown.append("<non-object row>")
            continue
        key = (r.get("path"), r.get("qid"))
        if key[0] not in PATHS:
            unknown.append(key)
        if key in idx:
            dups.append(key)
        else:
            idx[key] = r
    return idx, dups, unknown


def _paths_present(idx) -> list:
    present = {p for p, _ in idx}
    return [p for p in PATHS if p in present] + sorted(str(p) for p in present if p not in PATHS)


def _flags(suite, queries):
    if suite in SUITES:
        return suite == "CEN-G", suite == "MH", suite in BEIR_SUITES
    qs = [q for q in queries if isinstance(q, dict)]
    return (any(q.get("graded_chunks") is not None for q in qs),
            any(q.get("supporting") is not None for q in qs),
            any(q.get("graded_docs") is not None for q in qs))


def l1_metrics(doc: dict, queries: list, suite: str, state: str) -> dict:
    idx, _d, _u = index_rows(doc.get("rows"))
    graded, mh, beir = _flags(suite, queries)
    out = {}
    for path in _paths_present(idx):
        pq, cats, toks, lats = {}, {}, [], []
        mm = total = 0
        for q in queries:
            if not isinstance(q, dict):
                continue
            row = idx.get((path, q.get("qid")))
            if row is None:
                continue
            results = row.get("results") or []
            srcs = [r.get("source") for r in results]
            gold = set(q.get("gold_sources") or [])
            adv = q.get("category") == "adversarial"
            top5 = srcs[:5]
            rec = {
                "rr": m_rr(top5, gold),
                "ndcg5": m_ndcg(srcs, gold, 5),
                "hit1": m_hit(srcs, gold, 1),
                "hit5": m_hit(srcs, gold, 5),
                "p5": m_prec(srcs, gold, 5),
                "graded_ndcg5": None, "support_all5": None, "ndcg10": None, "recall10": None,
                "leak": (1 if results else 0) if adv else None,
                "latency_ms": None if row.get("latency_ms") is None else float(row["latency_ms"]),
            }
            if graded and q.get("graded_chunks"):
                ids = [f"{r.get('source')}:{r.get('chunk_index')}" for r in results]
                rec["graded_ndcg5"] = m_ndcg_graded(ids, q["graded_chunks"], 5)
            if mh:
                sup = q.get("supporting") or []
                rec["support_all5"] = 1 if all(s in top5 for s in sup) else 0
            if beir:
                grades = q.get("graded_docs") or {}
                rec["ndcg10"] = m_beir_ndcg10(srcs, grades)
                rec["recall10"] = m_beir_recall10(srcs, grades)
            pq[q["qid"]] = rec
            cats[q["qid"]] = adv
            toks.append(sum(len(r.get("text") or "") for r in results) // 4)
            lats.append(rec["latency_ms"])
            for r in results:
                total += 1
                nm = r.get("n_matches")
                if nm is not None and nm >= 2:
                    mm += 1
        recs = list(pq.values())
        non = [pq[q] for q in pq if not cats[q]]
        adv_recs = [pq[q] for q in pq if cats[q]]
        out[path] = {
            "n": len(recs),
            "mrr_5": mean(r["rr"] for r in recs),
            "ndcg_5": mean(r["ndcg5"] for r in recs),
            "hit_1": mean(r["hit1"] for r in recs),
            "hit_5": mean(r["hit5"] for r in recs),
            "p_5": mean(r["p5"] for r in recs),
            "mrr_5_nonadv": mean(r["rr"] for r in non),
            "ndcg_5_nonadv": mean(r["ndcg5"] for r in non),
            "hit_5_nonadv": mean(r["hit5"] for r in non),
            "graded_ndcg_5": mean(r["graded_ndcg5"] for r in recs) if graded else None,
            "support_all_5": mean(r["support_all5"] for r in recs) if mh else None,
            "ndcg_10": mean(r["ndcg10"] for r in recs) if beir else None,
            "recall_10": mean(r["recall10"] for r in recs) if beir else None,
            "adv_n": len(adv_recs),
            "adv_leak_count": sum(r["leak"] for r in adv_recs),
            "latency_p50_ms": pct(lats, 50),
            "latency_p95_ms": pct(lats, 95),
            "fulltext_tokens_mean": mean(toks),
            "multi_match_freq": (mm / total if total else None) if state == "C" else None,
            "per_query": pq,
        }
    return out


def l1_extras(doc: dict, queries: list) -> tuple:
    """Rankings, scores, texts and multi-match counts per path, for cross-file checks."""
    idx, _d, _u = index_rows(doc.get("rows"))
    rank, detail, mm = {}, {}, {}
    for path in _paths_present(idx):
        rank[path], detail[path] = {}, {}
        k = t = 0
        for q in queries:
            row = idx.get((path, q.get("qid")))
            if row is None:
                continue
            res = row.get("results") or []
            rank[path][q["qid"]] = tuple((r.get("source"), r.get("chunk_index")) for r in res)
            detail[path][q["qid"]] = (tuple(r.get("score") for r in res), tuple(r.get("text") for r in res))
            for r in res:
                t += 1
                nm = r.get("n_matches")
                if nm is not None and nm >= 2:
                    k += 1
        mm[path] = (k, t)
    return rank, detail, mm


# ── Layer 2: raw-output parsing and metrics ─────────────────────────

HEADER_RE = re.compile(r"^\*\*Score: (-?[0-9.]+)\*\* \| Source: (.+)$")
FENCE = "```"


def parse_output(raw) -> list:
    """Result blocks of a raw search output: [(score, source, body)]."""
    if not raw:
        return []
    lines = raw.split("\n")
    heads = []
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if m:
            heads.append((i, m))
    blocks = []
    for j, (i, m) in enumerate(heads):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(lines)
        seg = lines[i + 1:end]
        fences = [k for k, line in enumerate(seg) if line == FENCE]
        body = "\n".join(seg[fences[0] + 1:fences[-1]]) if len(fences) >= 2 else ""
        try:
            score = float(m.group(1))
        except ValueError:
            score = None
        blocks.append((score, m.group(2), body))
    return blocks


def is_anomalous_output(raw, blocks) -> bool:
    """True for outputs that are neither result blocks nor the empty-result message."""
    if blocks:
        return False
    return (raw or "").strip() != "No results found."


class L2Context:
    def __init__(self, corpus: Corpus | None, gold: GoldChunks | None):
        self.corpus = corpus
        self.gold = gold


def l2_metrics(doc: dict, queries: list, suite: str, state: str, ctx: L2Context) -> dict:
    idx, _d, _u = index_rows(doc.get("rows"))
    graded, mh, _beir = _flags(suite, queries)
    corpus = ctx.corpus
    gold_union_cache: dict = {}
    out = {}
    for path in _paths_present(idx):
        pq, cats, chars, lats = {}, {}, [], []
        errors = 0
        for q in queries:
            if not isinstance(q, dict):
                continue
            row = idx.get((path, q.get("qid")))
            if row is None:
                continue
            if row.get("error") is not None:
                errors += 1
            raw = row.get("raw_output")
            raw = raw if isinstance(raw, str) else ""
            blocks = parse_output(raw)
            norm = normalise(raw)
            gold = set(q.get("gold_sources") or [])
            adv = q.get("category") == "adversarial"
            srcs = [b[1] for b in blocks]
            rec = {"srcvis": m_hit(srcs, gold, 5), "gpv": None, "gpc": None, "support_visible": None,
                   "goldtext": None, "goldshare": None, "chars": len(raw),
                   "leak": (1 if blocks else 0) if adv else None,
                   "latency_ms": None if row.get("latency_ms") is None else float(row["latency_ms"])}
            if graded and not adv and ctx.gold is not None:
                sets = ctx.gold.gold_sets(q.get("graded_chunks"))
                if sets:
                    found = [sum(1 for s in S if s in norm) for S in sets]
                    rec["gpv"] = 1 if any(found) else 0
                    rec["gpc"] = sum(f / len(S) for f, S in zip(found, sets)) / len(sets)
            if mh and corpus is not None:
                sup = q.get("supporting") or []
                rec["support_visible"] = 1 if all(any(s in norm for s in corpus.shingles(d)) for d in sup) else 0
            if not adv and corpus is not None:
                qid = q["qid"]
                if qid not in gold_union_cache:
                    u = set()
                    for d in sorted(gold):
                        u |= corpus.shingles(d)
                    gold_union_cache[qid] = u
                rec["goldtext"] = sum(1 for s in gold_union_cache[qid] if s in norm)
            if not adv and blocks:
                tot = sum(len(b[2]) for b in blocks)
                rec["goldshare"] = (sum(len(b[2]) for b in blocks if b[1] in gold) / tot) if tot > 0 else 0.0
            pq[q["qid"]] = rec
            cats[q["qid"]] = adv
            chars.append(rec["chars"])
            lats.append(rec["latency_ms"])
        recs = list(pq.values())
        adv_recs = [pq[q] for q in pq if cats[q]]
        gpv_vals = [r["gpv"] for r in recs if r["gpv"] is not None]
        out[path] = {
            "n": len(recs),
            "errors": errors,
            "srcvis_5": mean(r["srcvis"] for r in recs),
            "gpv": mean(gpv_vals) if graded else None,
            "gpv_n": len(gpv_vals),            # eligible queries; 0 outside CEN-G
            "gpc": mean(r["gpc"] for r in recs) if graded else None,
            "support_visible": mean(r["support_visible"] for r in recs) if mh else None,
            "goldtext_mean": mean(r["goldtext"] for r in recs),
            "goldshare_mean": mean(r["goldshare"] for r in recs),
            "chars_mean": mean(chars),
            "chars_p95": pct(chars, 95),
            "adv_chars_mean": mean(r["chars"] for r in adv_recs),
            "adv_leak_count": sum(r["leak"] for r in adv_recs),
            "latency_p50_ms": pct(lats, 50),
            "latency_p95_ms": pct(lats, 95),
            "per_query": pq,
        }
    return out


# ── Statistics (section 9) ──────────────────────────────────────────

def paired_bootstrap(diffs) -> dict | None:
    """Percentile 95% CI of the mean paired difference: 10,000 resamples, seed 20261018."""
    d = np.asarray(list(diffs), dtype=float)
    n = int(d.size)
    if n == 0:
        return None
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n, size=(N_BOOT, n))
    boot = d[idx].mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"n": n, "diff": float(d.mean()), "lo": float(lo), "hi": float(hi)}


def mcnemar(pairs) -> dict | None:
    """Exact McNemar on (reference, candidate) binary pairs: b = only reference succeeds, c = only candidate."""
    pairs = list(pairs)
    if not pairs:
        return None
    b = sum(1 for r, c in pairs if r and not c)
    c = sum(1 for r, c in pairs if c and not r)
    if b + c == 0:
        p = 1.0
    else:
        from scipy.stats import binomtest
        p = float(binomtest(c, b + c, 0.5, alternative="two-sided").pvalue)
    return {"n": len(pairs), "b": b, "c": c, "p": p}


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: (kv[1], kv[0]))
    m, running, adj = len(items), 0.0, {}
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def cohen_kappa(a: list, b: list, labels=VERDICTS):
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in labels)
    if pe >= 1.0:
        return None
    return (po - pe) / (1.0 - pe)


def spearman(xs, ys):
    if len(xs) < 3:
        return None, None
    from scipy.stats import spearmanr
    r = spearmanr(xs, ys)
    rho, p = float(r.statistic if hasattr(r, "statistic") else r[0]), float(r.pvalue if hasattr(r, "pvalue") else r[1])
    if math.isnan(rho):
        return None, None
    return rho, p


# ── Metric comparison (V-05) ────────────────────────────────────────

_ABSENT = object()


def compare_metrics(stored, recomputed, tol: float = TOL) -> dict:
    mism, unverified, compared = [], set(), 0
    if not isinstance(stored, dict):
        return {"status": "fail", "n_compared": 0, "n_mismatches": 1,
                "mismatches": [{"where": "metrics", "issue": "stored metrics missing or not an object"}],
                "unverified_keys": []}
    paths = [p for p in PATHS if p in stored or p in recomputed] + \
        sorted(str(p) for p in set(stored) | set(recomputed) if p not in PATHS)
    for path in paths:
        s, r = stored.get(path), recomputed.get(path)
        if not isinstance(s, dict) or r is None:
            mism.append({"where": path, "issue": "path present only in " + ("recomputation" if r else "file")})
            continue
        for key in sorted(set(s) | set(r)):
            if key == "per_query":
                continue
            sv, rv = s.get(key, _ABSENT), r.get(key, _ABSENT)
            if rv is _ABSENT:
                unverified.add(key)
                continue
            if sv is _ABSENT:
                if rv is not None:
                    mism.append({"where": f"{path}.{key}", "stored": "<absent>", "recomputed": rv})
                continue
            compared += 1
            if not values_equal(sv, rv, tol):
                mism.append({"where": f"{path}.{key}", "stored": sv, "recomputed": rv})
        spq, rpq = s.get("per_query"), r.get("per_query") or {}
        if not isinstance(spq, dict):
            mism.append({"where": f"{path}.per_query", "issue": "stored per_query missing"})
            continue
        for qid in list(rpq) + [q for q in spq if q not in rpq]:
            sq, rq = spq.get(qid), rpq.get(qid)
            if not isinstance(sq, dict) or rq is None:
                mism.append({"where": f"{path}.per_query.{qid}", "issue": "query present only in " + ("recomputation" if rq else "file")})
                continue
            for key in set(sq) | set(rq):
                sv, rv = sq.get(key, _ABSENT), rq.get(key, _ABSENT)
                if rv is _ABSENT:
                    unverified.add(f"per_query.{key}")
                    continue
                if sv is _ABSENT:
                    if rv is not None:
                        mism.append({"where": f"{path}.per_query.{qid}.{key}", "stored": "<absent>", "recomputed": rv})
                    continue
                compared += 1
                if not values_equal(sv, rv, tol):
                    mism.append({"where": f"{path}.per_query.{qid}.{key}", "stored": sv, "recomputed": rv})
    return {"status": "pass" if not mism else "fail", "n_compared": compared, "n_mismatches": len(mism),
            "mismatches": mism[:200], "unverified_keys": sorted(unverified)}


# ── Results inventory ───────────────────────────────────────────────

def expected_runs() -> list:
    """(layer, stem, state, suite, tag, role) for every run named by the protocol."""
    out = []
    for layer in ("L1", "L2"):
        for state in STATES:
            for suite in SUITES:
                out.append((layer, f"{state}_{suite}", state, suite, None, "main"))
        out.append((layer, "B_CEN_rerun", "B", "CEN", "rerun", "rerun"))
    out.append(("L2", "C_CEN_killswitch", "C", "CEN", "killswitch", "killswitch"))
    for s in ("CEN", "MH"):
        out.append(("L2", f"info_A_emptygraph_{s}", "A", s, "emptygraph", "info"))
        out.append(("L2", f"info_B_500_{s}", "B", s, "500", "info"))
    for r in INFO_RUNS:     # a round file's extra informational runs
        for s in r["suites"]:
            out.append(("L2", f"info_{r['state']}_{r['result_chars']}_{s}", r["state"], s, str(r["result_chars"]), "info"))
    return out


def info_result_chars() -> dict:
    """{stem prefix: CANDLEKEEP_RESULT_CHARS} of the informational runs that set it."""
    return {"info_B_500_": 500, **{f"info_{r['state']}_{r['result_chars']}_": r["result_chars"] for r in INFO_RUNS}}


def parse_stem(stem: str):
    parts = stem.split("_")
    if parts[0] == "info" and len(parts) >= 4:
        return parts[1], parts[-1], "_".join(parts[2:-1]) or None
    state = parts[0] if parts else None
    suite = parts[1] if len(parts) > 1 else None
    return state, suite, ("_".join(parts[2:]) or None)


class Run:
    def __init__(self, layer, stem, state, suite, tag, role, path: Path):
        self.layer, self.stem, self.state, self.suite, self.tag, self.role = layer, stem, state, suite, tag, role
        self.path = path
        self.present = path.exists()
        self.doc = None
        self.error = None
        self.sha256 = None
        self.agg: dict = {}
        self.pq: dict = {}
        self.rank: dict = {}
        self.detail: dict = {}
        self.mm: dict = {}
        self.raw: dict = {}
        self.items = {"V-02": [], "V-03": [], "V-05": []}
        self.comparison = None
        self.queries_ok = None
        self.loaded = False

    @property
    def ok(self) -> bool:
        return self.loaded

    @property
    def label(self) -> str:
        return f"{self.layer}/{self.stem}.json"


class Verifier:
    def __init__(self, root: Path, doc: Path, repo: Path, eval_home: Path, b_python: Path, gold_body: str = "product"):
        self.root, self.doc_path, self.repo, self.eval_home = root, doc, repo, eval_home
        self.vdir = root / "verification"
        self.gold = GoldChunks(b_python, gold_body)
        self._corpora: dict = {}
        self.runs: dict = {}
        self.extra_runs: list = []
        self.checks: dict = {}
        self.notes: list = []
        self._git_cache: dict = {}
        self._env_cache: dict = {}
        self._doc_text = None

    # -- shared resources

    def corpus(self, cid: str) -> Corpus:
        if cid not in self._corpora:
            self._corpora[cid] = Corpus(cid, self.eval_home)
        return self._corpora[cid]

    def doc_text(self) -> str:
        if self._doc_text is None:
            try:
                self._doc_text = self.doc_path.read_text(encoding="utf-8")
            except OSError:
                self._doc_text = ""
        return self._doc_text

    def rev(self, ref: str):
        key = ("rev", ref)
        if key not in self._git_cache:
            self._git_cache[key] = git_out(self.repo, "rev-parse", ref)
        return self._git_cache[key]

    def env_info(self, state: str):
        if state not in self._env_cache:
            p = self.root / "env" / f"{state}.txt"
            self._env_cache[state] = parse_env_file(p) if p.exists() else None
        return self._env_cache[state]

    def expected_tree(self, state: str):
        """(tree sha, source description) expected for a state's src/."""
        if state in STATE_REF:
            return self.rev(f"{STATE_REF[state]}:src"), f"git rev-parse {STATE_REF[state]}:src"
        if state == "C" and C_REF:
            return self.rev(f"{C_REF}:src"), f"git rev-parse {C_REF}:src"
        env = self.env_info("C")
        if env is None:
            return None, "env/C.txt missing"
        if env.get("src_tree_sha"):
            return env["src_tree_sha"], "env/C.txt src tree"
        if env.get("git_sha"):
            t = self.rev(f"{env['git_sha']}:src")
            return t, f"git rev-parse {env['git_sha'][:12]}:src (git SHA from env/C.txt)"
        return None, "env/C.txt has no git SHA"

    # -- per-file processing

    def load_runs(self):
        known = set()
        for layer, stem, state, suite, tag, role in expected_runs():
            r = Run(layer, stem, state, suite, tag, role, self.root / layer / f"{stem}.json")
            self.runs[(layer, stem)] = r
            known.add((layer, stem))
        for layer in ("L1", "L2"):
            d = self.root / layer
            if d.is_dir():
                for p in sorted(d.glob("*.json")):
                    if (layer, p.stem) not in known:
                        st, su, tg = parse_stem(p.stem)
                        r = Run(layer, p.stem, st, su, tg, "extra", p)
                        self.extra_runs.append(r)
        for r in list(self.runs.values()) + self.extra_runs:
            if r.present:
                self.process(r)

    def l2_ctx(self, suite: str) -> L2Context:
        cid = SUITE_CORPUS.get(suite)
        return L2Context(self.corpus(cid) if cid else None, self.gold if suite == "CEN-G" else None)

    def process(self, run: Run):
        doc, err = load_json_safe(run.path)
        run.sha256 = sha256_file(run.path)
        if doc is None or not isinstance(doc, dict):
            run.error = err or "not a JSON object"
            for v in run.items:
                run.items[v].append(item(run.label, "fail", run.error))
            return
        run.doc = doc
        meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
        if run.role == "extra":
            run.state = run.state if run.state in STATES else meta.get("state")
            run.suite = run.suite if run.suite in SUITES else meta.get("suite")
        suite = run.suite
        if suite not in SUITES:
            run.items["V-03"].append(item(run.label, "fail", f"unknown suite {suite!r}"))
            return
        derived = derive_queries(suite)
        file_qs = doc.get("queries")
        issues = compare_queries(file_qs, derived, suite)
        run.queries_ok = not issues
        run.items["V-03"].append(item(f"{run.label}: query records equal the fixture derivation",
                                      "pass" if not issues else "fail", issues[:10]))
        self.count_checks(run, derived)
        self.provenance_checks(run, meta)
        try:
            self._recompute(run, doc, meta, suite, derived, file_qs)
        except Exception as e:  # noqa: BLE001 - a malformed file is a failed check, not a crash
            import traceback
            run.items["V-05"].append(item(f"{run.label}: recomputation", "fail",
                                          f"{type(e).__name__}: {e}; {traceback.format_exc(limit=3)[-600:]}"))
            run.doc = {"meta": meta}

    def _recompute(self, run: Run, doc: dict, meta: dict, suite: str, derived: list, file_qs):
        # V-05: recompute from the file's own queries and rows; compare with the stored metrics.
        fq = [q for q in file_qs if isinstance(q, dict)] if isinstance(file_qs, list) else []
        if run.layer == "L1":
            rec_file = l1_metrics(doc, fq, suite, run.state)
            rec = rec_file if run.queries_ok else l1_metrics(doc, derived, suite, run.state)
            run.rank, run.detail, run.mm = l1_extras(doc, derived)
            if not (run.state == "B" and suite == "CEN" and run.role in ("main", "rerun")):
                run.detail = {}   # texts are only needed for the V-01 comparison
        else:
            ctx = self.l2_ctx(suite)
            rec_file = l2_metrics(doc, fq, suite, run.state, ctx)
            rec = rec_file if run.queries_ok else l2_metrics(doc, derived, suite, run.state, ctx)
            idx, _d, _u = index_rows(doc.get("rows"))
            run.raw = {p: {q["qid"]: idx[(p, q["qid"])].get("raw_output") for q in derived if (p, q["qid"]) in idx}
                       for p in _paths_present(idx)}
        run.comparison = compare_metrics(doc.get("metrics"), rec_file)
        unv = run.comparison["unverified_keys"]
        run.items["V-05"].append(item(
            f"{run.label}: stored metrics equal the independent recomputation (tol {TOL:g})",
            run.comparison["status"],
            {"n_compared": run.comparison["n_compared"], "n_mismatches": run.comparison["n_mismatches"],
             "first": run.comparison["mismatches"][:5]}))
        if unv:
            run.items["V-05"].append(item(f"{run.label}: keys not in the contract (not verified)", "warn", unv))
        if suite == "CEN-G" and run.layer == "L2" and self.gold.error:
            run.items["V-05"].append(item(f"{run.label}: CEN-G gold chunks", "fail", self.gold.error))
        rules = {k: meta[k] for k in ("cen_g_gold_body", "cen_g_chunk_body") if meta.get(k) is not None}
        if suite == "CEN-G" and run.layer == "L2" and rules:
            says = {}
            for k, rule in rules.items():
                low = json.dumps(rule).lower()
                says[k] = "product" if ("parse_frontmatter" in low or "product" in low) else \
                    ("contract" if ("contract" in low or "regex" in low) else None)
            st = "fail" if any(m is not None and m != self.gold.mode for m in says.values()) else \
                ("warn" if None in says.values() else "pass")
            run.items["V-05"].append(item(
                f"{run.label}: the file's CEN-G chunk-body rule equals the verifier's ({self.gold.mode})", st,
                {"recorded": rules, "read_as": says}))
        run.agg = {p: {k: v for k, v in m.items() if k != "per_query"} for p, m in rec.items()}
        run.pq = {p: m["per_query"] for p, m in rec.items()}
        payload = {"source": str(run.path), "sha256": run.sha256, "layer": run.layer, "state": run.state,
                   "suite": suite, "tag": run.tag, "queries_match_fixtures": run.queries_ok,
                   "metrics": rec_file, "comparison": run.comparison}
        if not run.queries_ok:
            payload["metrics_from_fixture_queries"] = rec
        run.payload = payload          # written by cmd_all, not here: loading runs must not write files
        run.loaded = True
        run.doc = {"meta": meta}   # release rows and texts; everything needed later has been extracted

    def count_checks(self, run: Run, derived: list):
        doc, suite = run.doc, run.suite
        n_exp = EXPECTED_N[suite]
        nq = len(doc.get("queries") or []) if isinstance(doc.get("queries"), list) else 0
        run.items["V-03"].append(item(f"{run.label}: n queries = {n_exp}", "pass" if nq == n_exp else "fail",
                                      f"file has {nq}, fixtures give {len(derived)}"))
        rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
        idx, dups, unknown = index_rows(rows)
        missing = [(p, q["qid"]) for q in derived for p in PATHS if (p, q["qid"]) not in idx]
        qids = {q["qid"] for q in derived}
        extra = [k for k in idx if k[1] not in qids]
        ok = not missing and not dups and not unknown and not extra and len(rows) == n_exp * len(PATHS)
        run.items["V-03"].append(item(
            f"{run.label}: every query x {len(PATHS)} paths exactly once", "pass" if ok else "fail",
            {"rows": len(rows), "expected": n_exp * len(PATHS), "missing": missing[:5], "n_missing": len(missing),
             "duplicates": dups[:5], "unknown_path": unknown[:5], "unknown_qid": extra[:5]}))
        order_qm = [(p, q["qid"]) for q in derived for p in PATHS]
        order_pm = [(p, q["qid"]) for p in PATHS for q in derived]
        actual = [(r.get("path"), r.get("qid")) for r in rows if isinstance(r, dict)]
        if ok and actual not in (order_qm, order_pm):
            run.items["V-03"].append(item(f"{run.label}: row order", "warn",
                                          "rows are complete but not in query-major or path-major fixture order"))
        if run.layer == "L2":
            bad = []
            for r in rows:
                if not isinstance(r, dict):
                    continue
                raw = r.get("raw_output")
                if r.get("error") is not None or not isinstance(raw, str) or is_anomalous_output(raw, parse_output(raw)):
                    bad.append((r.get("path"), r.get("qid"), (r.get("error") or str(raw)[:60])))
            run.items["V-03"].append(item(f"{run.label}: every output is result blocks or 'No results found.'",
                                          "pass" if not bad else "fail", {"n_anomalous": len(bad), "first": bad[:5]}))
        else:
            bad = [(r.get("path"), r.get("qid")) for r in rows if isinstance(r, dict) and
                   (not isinstance(r.get("results"), list) or r.get("latency_ms") is None)]
            run.items["V-03"].append(item(f"{run.label}: every row has results and latency",
                                          "pass" if not bad else "fail", bad[:5]))

    def provenance_checks(self, run: Run, meta: dict):
        it = run.items["V-02"]
        lab = run.label
        suite, state = run.suite, run.state

        def chk(name, ok, detail=""):
            it.append(item(f"{lab}: {name}", "pass" if ok else "fail", detail))

        chk("meta.layer", meta.get("layer") == run.layer, meta.get("layer"))
        chk("meta.state", meta.get("state") == state, meta.get("state"))
        chk("meta.suite", meta.get("suite") == suite, meta.get("suite"))
        tag = meta.get("tag")
        if run.tag is None:
            chk("meta.tag is null", tag in (None, ""), tag)
        elif tag is None or str(tag) not in run.stem:
            it.append(item(f"{lab}: meta.tag", "warn", f"meta.tag={tag!r} for tagged run {run.stem}"))
        corpus = meta.get("corpus")
        exp_c = SUITE_CORPUS[suite]
        chk(f"meta.corpus = {exp_c}", corpus == exp_c or (run.role == "info" and str(corpus).startswith(exp_c)), corpus)
        chk("meta.device = mps", meta.get("device") == "mps", meta.get("device"))
        chk(f"meta.n_results = {N_RESULTS[suite]}", meta.get("n_results") == N_RESULTS[suite], meta.get("n_results"))
        if run.layer == "L1":
            exp_o = 50 if suite == "CEN-G" else 100
            chk(f"meta.chunk_overlap = {exp_o}", meta.get("chunk_overlap") == exp_o, meta.get("chunk_overlap"))
        py = str(meta.get("python") or "")
        if run.layer == "L1" or py:
            chk("meta.python is 3.11", py.startswith("3.11"), py)
        for k in ("started_at", "finished_at"):
            ok = True
            try:
                _dt.datetime.fromisoformat(str(meta.get(k)).replace("Z", "+00:00"))
            except ValueError:
                ok = False
            chk(f"meta.{k} is ISO-8601", ok, meta.get(k))
        # Code identity.
        sha = str(meta.get("git_sha") or "")
        tree = meta.get("src_tree_sha")
        exp_tree, how = self.expected_tree(state) if state in STATES else (None, "unknown state")
        if exp_tree is None:
            it.append(item(f"{lab}: src tree expected for state {state}", "missing", how))
        else:
            chk(f"meta.src_tree_sha = {how}", tree == exp_tree, {"recorded": tree, "expected": exp_tree})
        full = self.rev(f"{sha}^{{commit}}") if re.fullmatch(r"[0-9a-fA-F]{7,40}", sha) else None
        chk("meta.git_sha resolves to a commit", full is not None, sha)
        if "src_dirty" in meta:
            chk("meta.src_dirty is false (src/ had no uncommitted changes)", not meta.get("src_dirty"), meta.get("src_dirty"))
        if full:
            committed = self.rev(f"{full}:src")
            if tree and committed != tree:
                it.append(item(f"{lab}: git_sha's committed src equals src_tree_sha", "warn",
                               {"committed": committed, "recorded": tree}))
            if state == "A":
                chk(f"git_sha is state A ({STATE_REF['A']})", full == self.rev(STATE_REF["A"]), full)
            elif state == "B":
                _o, _e, rc = git(self.repo, "diff", "--quiet", STATE_REF["B"], full, "--", "src")
                chk(f"git diff {STATE_REF['B']} <git_sha> -- src is empty", rc == 0, full)
            elif state == "C":
                if C_REF:
                    chk(f"git_sha is state C ({C_REF})", full == self.rev(C_REF), full)
                env = self.env_info("C")
                if env and env.get("git_sha"):
                    chk("git_sha equals env/C.txt", full == self.rev(env["git_sha"]), {"file": full, "env": env["git_sha"]})
                else:
                    it.append(item(f"{lab}: C git SHA in env/C.txt", "missing", "env/C.txt missing or without SHA"))
                rec = registry_sha(self.doc_text(), "C")
                if rec is None:
                    it.append(item(f"{lab}: C SHA recorded in section 14", "pending", "section 14 still says TBD"))
                else:
                    chk("git_sha matches the C SHA in section 14", full.startswith(rec.lower()), {"s14": rec, "file": full})
        # Packages.
        pk = meta.get("packages")
        if not isinstance(pk, dict) or not pk:
            chk("meta.packages recorded", False, "missing")
        else:
            npk = {norm_pkg(k): str(v) for k, v in pk.items()}
            if state in FASTMCP_VERSION:
                chk(f"fastmcp {FASTMCP_VERSION[state]}", npk.get("fastmcp") == FASTMCP_VERSION[state], npk.get("fastmcp"))
            env = self.env_info(state) if state in STATES else None
            if env is None:
                it.append(item(f"{lab}: env/{state}.txt", "missing", "cannot cross-check packages"))
            else:
                diff = {k: (v, env["packages"][k]) for k, v in npk.items()
                        if k in env["packages"] and env["packages"][k] != v}
                chk(f"packages equal env/{state}.txt pip freeze", not diff, dict(list(diff.items())[:10]))
        if run.layer == "L2":
            senv = meta.get("server_env") if isinstance(meta.get("server_env"), dict) else None
            if senv is None:
                chk("meta.server_env recorded", False, "missing")
            else:
                for k in ("CANDLEKEEP_RATE_LIMIT_SEARCH", "CANDLEKEEP_RATE_LIMIT_WRITE"):
                    chk(f"server_env {k}=0", str(senv.get(k, "")).strip() == "0", senv.get(k))
                dev = senv.get("CANDLEKEEP_DEVICE")
                chk("server_env CANDLEKEEP_DEVICE=mps", dev is None or str(dev) == "mps", dev)
                extra = senv.get("CANDLEKEEP_RESULT_EXTRA_CHARS")
                chars = senv.get("CANDLEKEEP_RESULT_CHARS")
                if run.role == "killswitch":
                    chk("server_env CANDLEKEEP_RESULT_EXTRA_CHARS=0", str(extra).strip() == "0", extra)
                elif state == "C" and extra is not None:
                    chk("server_env CANDLEKEEP_RESULT_EXTRA_CHARS=2500", str(extra).strip() == "2500", extra)
                want = next((n for pre, n in info_result_chars().items() if run.stem.startswith(pre)), None)
                if want is not None:
                    chk(f"server_env CANDLEKEEP_RESULT_CHARS={want}", str(chars).strip() == str(want), chars)
                elif chars is not None:
                    chk("server_env CANDLEKEEP_RESULT_CHARS=1000", str(chars).strip() == "1000", chars)
                chk('server_env write_probe = "neutralised" (server started through serve.py, section 16)',
                    senv.get("write_probe") == "neutralised", senv.get("write_probe"))
                chk("server_env PYTHONHASHSEED=20261018 (section 16)",
                    str(senv.get("PYTHONHASHSEED", "")).strip() == "20261018", senv.get("PYTHONHASHSEED"))
            chk("meta.client_fastmcp recorded", bool(meta.get("client_fastmcp")), meta.get("client_fastmcp"))
            chk("meta.server_url recorded", bool(meta.get("server_url")), meta.get("server_url"))
        if run.layer == "L1":
            chk("meta.hash_seed = 20261018 (PYTHONHASHSEED, section 16)",
                str(meta.get("hash_seed") or "").strip() == "20261018", meta.get("hash_seed"))
        # Chroma process identity (section 16); the per-corpus comparison is in chroma_items().
        cp, cpe = meta.get("chroma_process"), meta.get("chroma_process_end")
        chk("meta.chroma_process recorded as {pid, started, port}", chroma_identity_ok(cp), cp)
        chk("meta.chroma_process_end equals meta.chroma_process (one Chroma process for the whole run)",
            chroma_identity_ok(cp) and cpe == cp, {"start": cp, "end": cpe})
        # Ingest record of the corpus.
        cid = SUITE_CORPUS[suite]
        hits = self.ingest_records(cid)
        if not hits:
            it.append(item(f"{lab}: ingest record {cid}", "missing", f"ingest/{cid}_*.json"))
        else:
            it.append(item(f"{lab}: ingest record {cid}", "pass", hits[0].name))
            rec = self.ingest_record_obj(hits[0])
            # Ingest identity fields the file carries (meta "ingest_<x>") must equal the record's "<x>" or "ingest_<x>".
            fields = {k: val for k, val in meta.items() if k.startswith("ingest_")}
            if isinstance(meta.get("ingest"), dict):
                fields.update({f"ingest.{k}": val for k, val in meta["ingest"].items()})
            for k, val in fields.items():
                if isinstance(val, (dict, list)) or not isinstance(rec, dict):
                    continue
                base = k.split(".", 1)[1] if k.startswith("ingest.") else k[len("ingest_"):]
                rk = next((x for x in (k, base, f"ingest_{base}") if x in rec and not isinstance(rec[x], (dict, list))), None)
                if rk is not None:
                    chk(f"meta.{k} equals {hits[0].name} {rk}", rec[rk] == val, {"meta": val, "record": rec[rk]})
            if meta.get("ingest_record_sha256") is not None:
                digest = self.file_sha(hits[0])
                chk(f"meta.ingest_record_sha256 equals the SHA-256 of {hits[0].name} (the run used the current ingest)",
                    str(meta["ingest_record_sha256"]).lower() == digest, {"meta": meta["ingest_record_sha256"], "file": digest})
            if isinstance(meta.get("ingest_record"), str):
                chk(f"meta.ingest_record names {hits[0].name}", basename(meta["ingest_record"]) == hits[0].name,
                    meta["ingest_record"])
            if isinstance(rec, dict) and rec.get("ingest_uuid") and "ingest_uuid" not in meta:
                chk("meta.ingest_uuid recorded (the ingest record has one)", False, rec.get("ingest_uuid"))

    def file_sha(self, path: Path) -> str:
        key = ("sha256", str(path))
        if key not in self._env_cache:
            self._env_cache[key] = sha256_file(path)
        return self._env_cache[key]

    def ingest_record_obj(self, path: Path):
        key = ("ingest", str(path))
        if key not in self._env_cache:
            self._env_cache[key] = load_json_safe(path)[0]
        return self._env_cache[key]

    def ingest_records(self, cid: str) -> list:
        """Canonical ingest records ingest/<cid>_<name>.json (not *.replaced-*.json or *.failed.json)."""
        d = self.root / "ingest"
        if not d.is_dir():
            return []
        return [p for p in sorted(d.glob(f"{cid}_*.json")) if "." not in p.stem]

    # -- cross-file checks

    def main(self, layer, state, suite, role="main"):
        stem = {"main": f"{state}_{suite}", "rerun": f"{state}_{suite}_rerun",
                "killswitch": f"{state}_{suite}_killswitch"}[role]
        r = self.runs.get((layer, stem))
        return r if r is not None and r.ok and r.pq else None

    def check_v01(self):
        items = []
        for layer in ("L1", "L2"):
            a, b = self.main(layer, "B", "CEN"), self.main(layer, "B", "CEN", "rerun")
            name = f"{layer} B_CEN vs B_CEN_rerun"
            if a is None or b is None:
                items.append(item(name, "missing", "one or both runs absent"))
                continue
            if layer == "L1":
                diff = [(p, q) for p in PATHS for q in a.rank.get(p, {})
                        if a.rank[p].get(q) != b.rank.get(p, {}).get(q)]
                diff += [(p, q) for p in PATHS for q in b.rank.get(p, {}) if q not in a.rank.get(p, {})]
                n = sum(len(a.rank.get(p, {})) for p in PATHS)
                items.append(item(f"{name}: identical rankings", "pass" if not diff and n else "fail",
                                  {"compared": n, "differing": len(diff), "first": diff[:5]}))
                sdiff = [(p, q) for p in PATHS for q in a.detail.get(p, {})
                         if a.detail[p][q] != b.detail.get(p, {}).get(q)]
                if sdiff:
                    items.append(item(f"{name}: scores and texts", "warn",
                                      {"differing": len(sdiff), "first": sdiff[:5]}))
            else:
                diff = [(p, q) for p in PATHS for q in a.raw.get(p, {})
                        if a.raw[p].get(q) != b.raw.get(p, {}).get(q)]
                diff += [(p, q) for p in PATHS for q in b.raw.get(p, {}) if q not in a.raw.get(p, {})]
                n = sum(len(a.raw.get(p, {})) for p in PATHS)
                items.append(item(f"{name}: identical raw outputs", "pass" if not diff and n else "fail",
                                  {"compared": n, "differing": len(diff), "first": diff[:5]}))
        self.checks["V-01"] = {"title": "Determinism", "items": items}

    def check_v04(self):
        b, k = self.main("L2", "B", "CEN"), self.main("L2", "C", "CEN", "killswitch")
        if b is None or k is None:
            items = [item("L2 C_CEN_killswitch vs B_CEN", "missing", "one or both runs absent")]
            self.v04 = None
        else:
            diff, n = [], 0
            for p in PATHS:
                keys = set(b.raw.get(p, {})) | set(k.raw.get(p, {}))
                for q in sorted(keys):
                    n += 1
                    x, y = b.raw.get(p, {}).get(q), k.raw.get(p, {}).get(q)
                    if x is None or y is None or x.encode("utf-8") != y.encode("utf-8"):
                        diff.append((p, q))
            self.v04 = {"compared": n, "differing": len(diff), "first": diff[:10]}
            items = [item("L2 C_CEN_killswitch equals B_CEN byte for byte",
                          "pass" if not diff and n == EXPECTED_N["CEN"] * len(PATHS) else "fail", self.v04)]
        self.checks["V-04"] = {"title": "Kill switch", "items": items}

    def check_v07(self):
        items = []
        for state in STATES:
            for suite in SUITES:
                for role in ("main", "rerun") if (state, suite) == ("B", "CEN") else ("main",):
                    l1, l2 = self.main("L1", state, suite, role), self.main("L2", state, suite, role)
                    name = f"{state}_{suite}{'_rerun' if role == 'rerun' else ''}"
                    if l1 is None or l2 is None:
                        items.append(item(name, "missing", "L1 or L2 run absent"))
                        continue
                    for p in PATHS:
                        h, s = l1.agg.get(p, {}).get("hit_5"), l2.agg.get(p, {}).get("srcvis_5")
                        per = [q for q in l1.pq.get(p, {}) if q in l2.pq.get(p, {}) and
                               l1.pq[p][q]["hit5"] != l2.pq[p][q]["srcvis"]]
                        ok = h is not None and s is not None and abs(h - s) <= TOL
                        items.append(item(f"{name} {p}: SrcVis@5 = Hit@5", "pass" if ok else "fail",
                                          {"hit_5": h, "srcvis_5": s, "per_query_differences": len(per)}))
                        if ok and per:
                            items.append(item(f"{name} {p}: per-query SrcVis vs Hit", "warn", per[:5]))
        self.checks["V-07"] = {"title": "L1/L2 consistency", "items": items}

    def collect_file_checks(self):
        all_runs = list(self.runs.values()) + self.extra_runs
        for v, title in (("V-02", "Provenance"), ("V-03", "Counts"), ("V-05", "Independent recomputation")):
            items = []
            for r in all_runs:
                if not r.present:
                    if r.role != "extra":
                        items.append(item(r.label, "missing", "file absent"))
                    continue
                if r.role == "extra":
                    # Files the protocol does not name (pilots P*, ad-hoc runs) never count toward a
                    # criterion; their findings are reported without failing the check.
                    items.extend(dict(i, status="warn" if i["status"] != "pass" else "pass",
                                      name=i["name"] + " (extra file, not a protocol run)") for i in r.items[v])
                else:
                    items.extend(r.items[v])
            self.checks[v] = {"title": title, "items": items}
        # Global provenance items.
        g = self.checks["V-02"]["items"]
        for state in STATES:
            p = self.root / "env" / f"{state}.txt"
            env = self.env_info(state)
            if env is None:
                g.append(item(f"env/{state}.txt", "missing", str(p)))
                continue
            ok = bool(env.get("git_sha")) and env.get("device_mps")
            detail = {"git_sha": env.get("git_sha"), "src_tree_sha": env.get("src_tree_sha"),
                      "mps": env.get("device_mps"), "packages": len(env.get("packages") or {})}
            g.append(item(f"env/{state}.txt records git SHA and mps", "pass" if ok else "fail", detail))
            if state in STATE_REF and env.get("git_sha"):
                full = self.rev(env["git_sha"])
                if state == "A":
                    g.append(item(f"env/A.txt git SHA is {STATE_REF['A']}",
                                  "pass" if full == self.rev(STATE_REF["A"]) else "fail", full))
                else:
                    _o, _e, rc = git(self.repo, "diff", "--quiet", STATE_REF["B"], env["git_sha"], "--", "src")
                    g.append(item(f"env/B.txt: git diff {STATE_REF['B']} <sha> -- src is empty",
                                  "pass" if rc == 0 else "fail", env["git_sha"]))
            elif state == "C" and C_REF and env.get("git_sha"):
                full = self.rev(env["git_sha"])
                g.append(item(f"env/C.txt git SHA is {C_REF}", "pass" if full == self.rev(C_REF) else "fail", full))
        a, b = self.env_info("A"), self.env_info("B")
        if a and b:
            allowed = {"fastmcp", "fastmcp-slim", "py-key-value-aio", "py-key-value-shared", "candlekeep"}
            diff = {k: (v, b["packages"][k]) for k, v in a["packages"].items()
                    if k in b["packages"] and b["packages"][k] != v and k not in allowed}
            g.append(item("A packages equal B's freeze except fastmcp and py-key-value-aio", "warn" if diff else "pass",
                          dict(list(diff.items())[:15])))
        g.extend(self.checkout_items())
        g.extend(self.chroma_items())
        for cid in sorted(INGEST_DOCS):
            g.extend(self.ingest_items(cid))
        for cid in ("I08", "I09"):
            g.extend(self.staging_items(cid))

    def chroma_items(self):
        """Section 16: per corpus, one Chroma process served every L1/L2 run. Every protocol
        run of states A/B/C (main, rerun, kill switch, informational) must record the same
        meta.chroma_process; a mismatch fails and lists the files of each process. Files the
        protocol does not name are compared with that process and reported as warnings."""
        groups: dict = {}
        for r in list(self.runs.values()) + self.extra_runs:
            if not r.present or r.suite not in SUITES or r.state not in STATES or not isinstance(r.doc, dict):
                continue
            meta = r.doc.get("meta") if isinstance(r.doc.get("meta"), dict) else {}
            cp = meta.get("chroma_process")
            key = json.dumps(cp, sort_keys=True) if chroma_identity_ok(cp) else None
            groups.setdefault(SUITE_CORPUS[r.suite], []).append((r, key))
        out = []
        for cid in sorted(groups):
            entries = groups[cid]
            suites = ", ".join(sorted({r.suite for r, _ in entries}))
            proto: dict = {}
            for r, key in entries:
                if r.role != "extra":
                    proto.setdefault(key, []).append(r.label)
            extra = [(r.label, key) for r, key in entries if r.role == "extra"]
            ref = None
            if proto:
                ok = len(proto) == 1 and None not in proto
                ref = next(iter(proto)) if ok else None
                n = sum(len(v) for v in proto.values())
                detail = {"files": n, "chroma_process": json.loads(ref)} if ok else {
                    "files": n, "processes": {("<no valid meta.chroma_process>" if k is None else k): sorted(v)
                                              for k, v in proto.items()}}
                out.append(item(f"{cid} ({suites}): every L1/L2 file of states A/B/C (reruns, kill switch and "
                                f"informational rows included) ran against one Chroma process",
                                "pass" if ok else "fail", detail))
            if extra and (ref is not None or not proto):
                keys = {key for _, key in extra} | ({ref} if ref is not None else set())
                if len(keys) > 1 or None in keys:
                    listed = [(label, key) for label, key in extra if ref is None or key != ref]
                    out.append(item(f"{cid}: files the protocol does not name ran against another Chroma process",
                                    "warn", {"reference": json.loads(ref) if ref else None,
                                             "files": sorted(f"{label}: {key or '<no valid meta.chroma_process>'}"
                                                             for label, key in listed)[:50]}))
        return out

    def checkout_items(self):
        """State checkouts at verification time: HEAD and uncommitted src/ changes (signals, not proof)."""
        out = []
        env_c = self.env_info("C")
        head_c = self.rev(C_REF) if C_REF else (self.rev(env_c["git_sha"]) if env_c and env_c.get("git_sha") else None)
        wanted = {"A": (STATE_CHECKOUT.get("A", self.eval_home / "worktrees" / "A"), self.rev(STATE_REF["A"])),
                  "B": (self.repo, None),
                  "C": (STATE_CHECKOUT.get("C", self.eval_home / "worktrees" / "C"), head_c)}
        for state, (path, head_expected) in wanted.items():
            if not (path / ".git").exists():
                out.append(item(f"checkout {state} ({path})", "warn", "not found at verification time"))
                continue
            dirty, _e, rc = git(path, "status", "--porcelain", "--", "src")
            head = git_out(path, "rev-parse", "HEAD")
            ok_head = head_expected is None or head == head_expected
            if state == "B" and head:
                _o, _e2, rcb = git(self.repo, "diff", "--quiet", STATE_REF["B"], head, "--", "src")
                ok_head = rcb == 0
            status = "pass" if rc == 0 and not dirty and ok_head else "warn"
            out.append(item(f"checkout {state}: HEAD as expected and src/ clean", status,
                            {"path": str(path), "head": head, "expected": head_expected, "uncommitted_src": (dirty or "")[:300]}))
        return out

    def ingest_items(self, cid):
        hits = self.ingest_records(cid)
        if not hits:
            return [item(f"ingest/{cid}", "missing", "no ingest record")]
        out = []
        if len(hits) > 1:
            out.append(item(f"ingest/{cid}: exactly one record", "fail", [h.name for h in hits]))
        p = hits[0]
        lab = f"ingest/{p.name}"
        obj, err = load_json_safe(p)
        if not isinstance(obj, dict):
            return out + [item(lab, "fail", err or "not a JSON object")]
        counts = obj.get("counts") if isinstance(obj.get("counts"), dict) else {}
        n, field = counts.get("documents"), "counts.documents"
        if not isinstance(n, int) or isinstance(n, bool):
            found = find_doc_count(obj)
            field, n = found if found else (None, None)
        if n is None:
            out.append(item(f"{lab}: document count", "warn", "no document-count field found"))
        else:
            out.append(item(f"{lab}: {INGEST_DOCS[cid]} documents", "pass" if n == INGEST_DOCS[cid] else "fail",
                            {"field": field, "value": n}))
        ident = obj.get("ingest_id", obj.get("corpus"))
        if ident is not None:
            out.append(item(f"{lab}: ingest id {cid}", "pass" if ident == cid else "fail", ident))
        if "ok" in obj:
            out.append(item(f"{lab}: ingest succeeded", "pass" if obj.get("ok") is True else "fail", obj.get("failure")))
        exp_o = 50 if cid == "I02" else 100
        if "chunk_overlap" in obj:
            out.append(item(f"{lab}: chunk_overlap {exp_o}", "pass" if obj.get("chunk_overlap") == exp_o else "fail",
                            obj.get("chunk_overlap")))
        if "state" in obj:
            out.append(item(f"{lab}: ingested by state B", "pass" if obj.get("state") == "B" else "fail", obj.get("state")))
            senv = obj.get("server_env") if isinstance(obj.get("server_env"), dict) else {}
            out.append(item(f"{lab}: ingest server PYTHONHASHSEED=20261018 (section 16)",
                            "pass" if str(senv.get("PYTHONHASHSEED", "")).strip() == "20261018" else "fail",
                            senv.get("PYTHONHASHSEED")))
        sha = str(obj.get("git_sha") or "")
        if sha:
            _o, _e, rc = git(self.repo, "diff", "--quiet", STATE_REF["B"], sha, "--", "src")
            out.append(item(f"{lab}: git diff {STATE_REF['B']} <git_sha> -- src is empty",
                            "pass" if rc == 0 else "fail", sha))
        if obj.get("src_tree_sha"):
            exp = self.rev(f"{STATE_REF['B']}:src")
            out.append(item(f"{lab}: src_tree_sha = {STATE_REF['B']}:src",
                            "pass" if obj["src_tree_sha"] == exp else "fail",
                            {"recorded": obj["src_tree_sha"], "expected": exp}))
        if obj.get("src_dirty"):
            out.append(item(f"{lab}: src/ clean at ingest", "fail", obj.get("src_dirty")))
        if obj.get("ingest_uuid"):
            mp = Path(obj["data_marker"]) if obj.get("data_marker") else self.eval_home / "data" / cid / "ingest_marker.json"
            mk, merr = load_json_safe(mp)
            if not isinstance(mk, dict):
                out.append(item(f"{lab}: data-directory marker {mp}", "warn", merr or "not a JSON object"))
            else:
                out.append(item(f"{lab}: data-directory marker names this ingest (ingest_uuid)",
                                "pass" if mk.get("ingest_uuid") == obj["ingest_uuid"] else "fail",
                                {"record": obj["ingest_uuid"], "marker": mk.get("ingest_uuid")}))
        chk = obj.get("checks")
        if isinstance(chk, dict):
            bad = sorted(k for k, val in chk.items() if val is False)
            out.append(item(f"{lab}: the record's own consistency checks", "pass" if not bad else "fail", bad))
        side = sorted(q.name for q in p.parent.glob(f"{cid}_*.json") if "." in q.stem)
        if side:
            out.append(item(f"ingest/{cid}: replaced or failed records present (not used)", "warn", side))
        return out

    def staging_items(self, cid):
        c = self.corpus(cid)
        if c.staging_dir is None:
            return [item(f"BEIR staging {cid}", "missing", f"{self.eval_home / 'staging' / cid} absent; "
                                                            "gold text falls back to corpus.jsonl")]
        name = BEIR_SPEC[CORPUS_SUITE[cid]][0]
        texts = {}
        with open(FIX / "beir" / name / "corpus.jsonl", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dd = json.loads(line)
                    texts[f"{dd['_id']}.md"] = dd.get("text", "")
        missing = [n for n in texts if n not in c.paths]
        extra = [n for n in c.paths if n not in texts]
        bad = [n for n in texts if n in c.paths and normalise(c.body(n)) != normalise(texts[n])]
        ok = not missing and not extra and not bad
        return [item(f"BEIR staging {cid}: {len(texts)} docs, bodies equal corpus.jsonl text", "pass" if ok else "fail",
                     {"staged": len(c.paths), "missing": missing[:5], "extra": extra[:5], "body_mismatch": bad[:5],
                      "n_body_mismatch": len(bad)})]

    def check_v03_global(self):
        it = self.checks["V-03"]["items"]
        for suite in SUITES:
            n = len(derive_queries(suite))
            it.append(item(f"fixtures give n({suite}) = {EXPECTED_N[suite]}", "pass" if n == EXPECTED_N[suite] else "fail", n))
        ans, cen = cen_answers(), derive_queries("CEN")
        off = [q["qid"] for q, a in zip(cen, ans) if a.get("query") != q["query"] or a.get("category") != q["category"]]
        it.append(item("CEN-A fixture: 108 queries in eval_suite_100.json order (query and category equal)",
                       "pass" if len(ans) == len(cen) == EXPECTED_N["CEN"] and not off else "fail",
                       {"n": len(ans), "differing": off[:5]}))
        non_adv = [q["qid"] for q in cen if q["category"] != "adversarial"]
        empty = [q["qid"] for q, a in zip(cen, ans)
                 if q["category"] != "adversarial" and not str(a.get("reference_answer") or "").strip()]
        it.append(item(f"CEN-A: {CEN_A_N} judged queries = {len(non_adv)} non-adversarial minus the empty reference "
                       f"answers {list(CEN_A_EXCLUDED)} (section 16)",
                       "pass" if len(non_adv) - len(empty) == CEN_A_N and tuple(empty) == CEN_A_EXCLUDED else "fail",
                       {"non_adversarial": len(non_adv), "empty_reference_answer": empty,
                        "judged": len(non_adv) - len(empty)}))
        qs = derive_queries("CEN-G")
        non = [q for q in qs if q["category"] != "adversarial"]
        no_key = [q["qid"] for q in non if not any(g >= 2 for g in (q["graded_chunks"] or {}).values())]
        self.gold.load()
        mod = str(self.gold.module or "")
        ok = self.gold.error is None and mod.startswith(str(self.repo / "src"))
        self.checks["V-02"]["items"].append(item(
            f"CEN-G gold chunks built by state B's DocumentProcessor at 512/50 (body rule: {self.gold.mode})",
            "pass" if ok else "fail", {"module": self.gold.module, "error": self.gold.error}))
        if self.gold.error:
            it.append(item("CEN-G exclusion count", "fail", self.gold.error))
            self.cen_g_exclusion = None
            return
        no_chunk = [q["qid"] for q in non if not self.gold.gold_sets(q["graded_chunks"])]
        self.cen_g_exclusion = {"non_adversarial": len(non), "excluded": len(no_chunk), "included": len(non) - len(no_chunk),
                                "excluded_qids": no_chunk, "no_grade2_key": len(no_key),
                                "unresolvable_gold_keys": sorted(self.gold.unresolved)}
        it.append(item(f"CEN-G exclusion count: {len(no_chunk)} of {len(non)} non-adversarial queries have no gold chunk",
                       "pass", self.cen_g_exclusion))

    def data_notes(self):
        """Facts about the fixtures that bear on interpretation (reported, not judged)."""
        notes = []
        if self.gold.loaded and not self.gold.error:
            differ = sorted(n for n in self.gold.chunks if self.gold.chunks[n] != self.gold.product.get(n))
            affected = []
            for q in derive_queries("CEN-G"):
                for key, g in (q["graded_chunks"] or {}).items():
                    if g >= 2 and key.rpartition(":")[0] in differ:
                        affected.append((q["qid"], key))
            if differ:
                notes.append({"topic": "CEN-G gold chunks",
                              "note": "For these documents the YAML frontmatter fails to parse, so the product indexes the "
                                      "full text (frontmatter included), while the data contract's wording re-chunks the "
                                      "regex-stripped body; chunk texts and indices differ between the two rules. This run "
                                      f"uses the '{self.gold.mode}' rule ('product' = the chunks the graded labels refer to). "
                                      "The choice belongs in the Deviations Log as a pre-run clarification of the gold-chunk "
                                      "derivation.",
                              "rule": self.gold.mode, "documents": differ, "grade2_keys_affected": len(affected),
                              "queries_affected": sorted({a for a, _ in affected}),
                              "unresolvable_gold_keys": sorted(self.gold.unresolved)})
        # Effective non-inferiority margins: adversarial queries score RR = nDCG = 0 in every state, so their
        # paired difference is 0 and the all-query mean difference is n_answerable / n_all of the answerable one.
        margins = {}
        for name, suites in (("CEN", ("CEN",)), ("CD pooled", CD_SUITES)):
            qs = [q for s in suites for q in derive_queries(s)]
            na = sum(1 for q in qs if q["category"] != "adversarial")
            margins[name] = {"n_all": len(qs), "n_answerable": na,
                             "delta_on_answerable": round(DELTA * len(qs) / na, 4) if na else None}
        per_suite = {s: round(0.03 * len(derive_queries(s)) / sum(1 for q in derive_queries(s) if q["category"] != "adversarial"), 4)
                     for s in CD_SUITES}
        notes.append({"topic": "Non-inferiority margins (C-01, C-02)",
                      "note": "MRR@5 and nDCG@5 means include adversarial queries (pre-run deviation for section 6), whose "
                              "paired B-A difference is exactly 0. The registered margins therefore correspond to larger "
                              "margins on answerable queries. summary.json also reports the non-adversarial-only CIs "
                              "(criteria C-01/C-02 'secondary_nonadversarial'); the decision uses the registered rule.",
                      "margins": margins, "c02_per_suite_limit_on_answerable": per_suite})
        with open(FIX / "eval_suite_100.json", encoding="utf-8") as f:
            cen = _query_list(json.load(f))
        missing_paths = sorted({s for q in cen for s in q.get("expected_sources", []) if not (REPO / s).exists()})
        if missing_paths:
            notes.append({"topic": "CEN gold paths", "note": "expected_sources paths that do not exist; matching is by "
                          "basename, so a same-named corpus file still counts", "paths": missing_paths})
        empty = [f"CEN-{i:03d}" for i, q in enumerate(cen_answers(), 1)
                 if q.get("category") != "adversarial" and not q.get("reference_answer")]
        if empty:
            notes.append({"topic": "CEN-A", "note": "non-adversarial queries with an empty reference answer; not judged "
                                                    "(section 16), so CEN-A has 76 queries", "qids": empty})
        self.notes = notes


def chroma_identity_ok(value) -> bool:
    """A Chroma process identity as the runs record it: {pid: int, started: str, port: int}."""
    return (isinstance(value, dict) and set(value) == set(CHROMA_PROCESS_KEYS)
            and all(isinstance(value[k], int) and not isinstance(value[k], bool) for k in ("pid", "port"))
            and isinstance(value["started"], str) and bool(value["started"]))


def parse_env_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    dev = re.search(r"^\s*device:\s*(\S+)", text, re.M | re.I)
    info = {"git_sha": None, "src_tree_sha": None, "packages": {},
            "device_mps": (dev.group(1).lower() == "mps") if dev else ("mps" in text.lower())}
    hexre = re.compile(r"\b[0-9a-f]{40}\b", re.I)
    for line in text.splitlines():
        low = line.lower()
        pm = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)==([^\s;#]+)", line)
        if pm:
            info["packages"][norm_pkg(pm.group(1))] = pm.group(2)
            continue
        if any(w in low for w in ("model", "snapshot", "revision", "blob", "hugging", "pyproject")):
            continue
        m = hexre.search(line)
        if not m:
            continue
        if "tree" in low:
            info["src_tree_sha"] = info["src_tree_sha"] or m.group(0).lower()
        elif any(w in low for w in ("git", "commit", "head", "sha")):
            info["git_sha"] = info["git_sha"] or m.group(0).lower()
    # env.py's explicit "git_sha:" and "src_tree_sha (...):" lines take precedence over the heuristics above.
    g = re.search(r"^\s*git_sha\s*:\s*([0-9a-f]{40})\b", text, re.M | re.I)
    t = re.search(r"^\s*src_tree_sha\b.*?:\s*([0-9a-f]{40})\b", text, re.M | re.I)
    if g:
        info["git_sha"] = g.group(1).lower()
    if t:
        info["src_tree_sha"] = t.group(1).lower()
    return info


def find_doc_count(obj, prefix=""):
    """(field, value) of the first document-count field found in an ingest record."""
    if isinstance(obj, dict):
        for k in ("n_docs", "docs", "documents", "n_documents", "doc_count", "documents_ingested", "files", "n_files"):
            v = obj.get(k)
            if isinstance(v, int) and not isinstance(v, bool):
                return prefix + k, v
            if isinstance(v, list):
                return prefix + k, len(v)
        for k, v in obj.items():
            if isinstance(v, dict):
                found = find_doc_count(v, prefix + k + ".")
                if found is not None:
                    return found
    return None


def extract_section(text: str, start_prefix: str) -> str | None:
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(start_prefix)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def registry_rows(doc_text: str) -> list:
    sec = extract_section(doc_text, "## 14.") or ""
    rows = []
    for line in sec.split("\n"):
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append((cols, line))
    return rows[1:] if rows else []


def registry_sha(doc_text: str, state: str):
    for cols, _line in registry_rows(doc_text):
        if len(cols) >= 3 and cols[1].strip() == state and re.fullmatch(r"[0-9a-fA-F]{7,40}", cols[2].strip()):
            return cols[2].strip()
    return None


def registry_keymap_sha(doc_text: str, pack: str):
    for cols, line in registry_rows(doc_text):
        if cols and cols[0].strip() in (pack, f"{pack} (opt.)"):
            m = re.search(r"\b[0-9a-fA-F]{64}\b", line)
            return m.group(0).lower() if m else None
    return None


# ── Judges (V-06, C-11, section 15.3) ───────────────────────────────

ITEM_ID_RE = re.compile(r"^[A-Z]\d{4,}$")         # J#### (J1), K#### (J2), R#### (re-judge)
PACK_ITEM_KEYS = ("id", "question", "reference_answer", "tool_output")
LABEL_KEYS = ("state", "path", "query_type", "source", "sources", "qid", "query_id", "cen_qid", "suite", "key")
ID_KEYS = ("id", "item_id", "jid", "item")
OUTPUT_KEYS = ("tool_output", "raw_output", "output", "search_output", "tool_result")
QUESTION_KEYS = ("question", "query")
REFERENCE_KEYS = ("reference_answer", "reference")
VERDICT_KEYS = ("verdict", "label", "rating", "judgement", "judgment", "grade", "value")
EVIDENCE_KEYS = ("evidence", "quotes", "evidence_quotes", "quote", "snippets", "evidence_snippets")
LIST_KEYS = ("items", "judgements", "judgments", "verdicts", "results", "outputs", "records", "entries", "data")


def _first(d: dict, keys):
    for k in keys:
        if k in d:
            return d[k]
    return None


def rec_id(r: dict):
    v = _first(r, ID_KEYS)
    return None if v is None else str(v)


def find_records(obj) -> list:
    """Records of a pack or judge-output file: a list, a list under a known key, or a dict keyed by item id."""
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict):
        for key in LIST_KEYS:
            v = obj.get(key)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
        keyed = {str(k): v for k, v in obj.items() if ITEM_ID_RE.match(str(k))}
        return [dict(v, id=k) if isinstance(v, dict) else {"id": k, "value": v} for k, v in keyed.items()]
    return []


def keymap_entries(obj) -> dict:
    """{item id: value} of a key map: {id: "qid|STATE"}, {R id: source id}, or a list of records."""
    if isinstance(obj, dict):
        for k in ("map", "keymap", "items", "entries"):
            if isinstance(obj.get(k), (dict, list)):
                return keymap_entries(obj[k])
        return {str(k): v for k, v in obj.items() if ITEM_ID_RE.match(str(k))}
    if isinstance(obj, list):
        return {rec_id(r): r for r in obj if isinstance(r, dict) and rec_id(r) is not None}
    return {}


def unblind_value(v):
    """(qid, state) of a key-map value "qid|STATE" (or of a record with qid and state)."""
    if isinstance(v, str):
        parts = [p.strip() for p in v.split("|")]
        return (parts[0], parts[1]) if len(parts) == 2 and all(parts) else None
    if isinstance(v, dict):
        q, s = _first(v, ("qid", "query_id", "cen_qid")), v.get("state")
        if q is not None and s is not None:
            return str(q), str(s)
        if isinstance(v.get("key"), str):
            return unblind_value(v["key"])
    return None


def source_value(v):
    """Source item id of a re-judge key-map value: "J0042", or a record naming its source."""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        s = _first(v, ("source", "source_id", "of", "original", "jid"))
        return None if s is None else str(s)
    return None


def evidence_parts(ev) -> list:
    if ev is None:
        return []
    if isinstance(ev, str):
        ev = [ev]
    parts = []
    for e in ev if isinstance(ev, list) else [ev]:
        if isinstance(e, dict):
            e = _first(e, ("quote", "text", "snippet", "evidence")) or ""
        for p in str(e).split(" ... "):
            if p.strip():
                parts.append(p)
    return parts


def snippet_found(part: str, output: str) -> bool:
    if part in output or part.strip() in output:
        return True
    t = part.strip().strip("\"'\u201c\u201d").strip()
    t = re.sub(r"^(\.\.\.|\u2026)\s*", "", t)
    t = re.sub(r"\s*(\.\.\.|\u2026)$", "", t)
    return bool(t) and t in output


def cen_number(qid) -> int | None:
    m = re.search(r"(\d+)$", str(qid or ""))
    return int(m.group(1)) if m else None


def _part_no(path: Path):
    m = re.search(r"_part(\d+)$", path.stem)
    return int(m.group(1)) if m else None


def _agreement(pairs):
    return (sum(1 for x, y in pairs if x == y) / len(pairs)) if pairs else None


class Judges:
    """V-06 and the Layer 3 tallies, from the files judge_pack.py writes (see the module docstring)."""

    def __init__(self, v: Verifier):
        self.v = v
        self.jdir = v.root / "judges"
        self.packs: dict = {}
        self.bad_ev: dict = {}
        self.j1d = None          # R2-3 (a round only): discordant_rejudge()
        cen = derive_queries("CEN")
        self.non_adv = [q["qid"] for q in cen if q["category"] != "adversarial"]
        self.answers = {q["qid"]: a for q, a in zip(cen, cen_answers())}
        # Section 16: queries whose reference answer is empty are not judged (CEN-A = 76 queries).
        self.excluded = [q for q in self.non_adv if not str(self.answers.get(q, {}).get("reference_answer") or "").strip()]
        self.judged = [q for q in self.non_adv if q not in self.excluded]

    def run(self):
        items = []
        for pack, spec in JUDGE_PACKS.items():
            res = self.pack(pack, spec)
            self.packs[pack] = res
            items.extend(res["items"])
        if ROUND is not None:
            self.j1d = self.discordant_rejudge(items)
        self.v.checks["V-06"] = {"title": "Judge integrity", "items": items}

    # -- file-level helpers

    def _load_items(self, path: Path, name: str, it: list):
        """{id: item} of a pack file, or None when it cannot be read."""
        obj, err = load_json_safe(path)
        if obj is None:
            it.append(item(f"{name}: {path.name} readable", "missing" if err == "missing" else "fail", err))
            return None
        recs = find_records(obj)
        ids = [rec_id(r) for r in recs]
        cnt: dict = {}
        for i in ids:
            cnt[i] = cnt.get(i, 0) + 1
        bad = [i for i in ids if i is None or not ITEM_ID_RE.match(i)]
        dup = sorted(i for i, c in cnt.items() if i is not None and c > 1)
        prefixes = sorted({i[0] for i in ids if i})
        ok = bool(recs) and not bad and not dup and len(prefixes) == 1
        it.append(item(f"{name}: {path.name} has unique item ids of one form (letter + 4 digits)",
                       "pass" if ok else "fail",
                       {"n": len(recs), "malformed": bad[:5], "duplicates": dup[:5], "prefixes": prefixes}))
        return {i: r for i, r in zip(ids, recs) if i is not None}

    def _manifest(self, name: str, it: list, expect: dict):
        obj, err = load_json_safe(self.jdir / f"manifest_{name}.json")
        if not isinstance(obj, dict):
            it.append(item(f"{name}: manifest_{name}.json", "warn", err or "not a JSON object"))
            return None
        diffs = {k: {"manifest": obj.get(k), "protocol": val} for k, val in expect.items()
                 if k in obj and obj.get(k) != val}
        it.append(item(f"{name}: manifest records the protocol's parameters", "pass" if not diffs else "fail", diffs))
        return obj

    def _hash(self, name: str, kf: Path, it: list, manifest, section14: bool) -> str:
        digest = sha256_file(kf)
        side = next((p for p in (kf.with_name(kf.name + ".sha256"), kf.with_suffix(".sha256")) if p.exists()), None)
        if side is None:
            it.append(item(f"{name}: key-map .sha256 file", "missing", f"{kf.name}.sha256"))
        else:
            m = re.search(r"\b[0-9a-fA-F]{64}\b", side.read_text(encoding="utf-8", errors="replace"))
            rec = m.group(0).lower() if m else None
            it.append(item(f"{name}: key-map SHA-256 equals {side.name}", "pass" if rec == digest else "fail",
                           {"computed": digest, "recorded": rec}))
        if manifest is not None and manifest.get("keymap_sha256") is not None:
            rec = str(manifest["keymap_sha256"]).lower()
            it.append(item(f"{name}: key-map SHA-256 equals manifest_{name}.json", "pass" if rec == digest else "fail",
                           {"computed": digest, "manifest": rec}))
        if section14:
            s14 = registry_keymap_sha(self.v.doc_text(), name)
            if s14 is None:
                it.append(item(f"{name}: key-map SHA-256 recorded in section 14 before judging", "pending", "not recorded"))
            else:
                it.append(item(f"{name}: key-map SHA-256 equals section 14", "pass" if s14 == digest else "fail",
                               {"computed": digest, "section14": s14}))
        return digest

    def _labels(self, name: str, items: dict, it: list):
        labelled = sorted(i for i, r in items.items() if any(k in r for k in LABEL_KEYS))
        it.append(item(f"{name}: items carry no state, path, source or query labels", "pass" if not labelled else "fail",
                       labelled[:5]))
        incomplete = sorted(i for i, r in items.items() if any(k not in r for k in PACK_ITEM_KEYS))
        it.append(item(f"{name}: every item has id, question, reference_answer and tool_output",
                       "pass" if not incomplete else "fail", incomplete[:5]))
        extra = sorted({k for r in items.values() for k in r if k not in PACK_ITEM_KEYS and k not in LABEL_KEYS})
        if extra:
            it.append(item(f"{name}: item fields beyond the protocol's content", "warn", extra))

    def _parts(self, name: str, items: dict, it: list) -> dict:
        """{part number: ids} of pack_<name>_part<k>.json; they must partition the pack with identical items."""
        files = sorted(self.jdir.glob(f"pack_{name}_part*.json"), key=lambda p: (_part_no(p) or 0, p.name))
        if not files:
            return {}
        seen, issues, by_part = {}, [], {}
        for p in files:
            obj, err = load_json_safe(p)
            if obj is None:
                issues.append(f"{p.name}: {err}")
                continue
            ids = set()
            for r in find_records(obj):
                i = rec_id(r)
                ids.add(i)
                if i in seen:
                    issues.append(f"{i} in {seen[i]} and {p.name}")
                seen[i] = p.name
                if i not in items:
                    issues.append(f"{p.name}: unknown id {i}")
                elif r != items[i]:
                    issues.append(f"{p.name}: {i} differs from pack_{name}.json")
            by_part[_part_no(p)] = ids
        missing = sorted(set(items) - set(seen))
        sizes = [len(by_part[k]) for k in sorted(by_part, key=lambda x: x or 0)]
        it.append(item(f"{name}: parts partition the pack (each item once, identical content)",
                       "pass" if not issues and not missing else "fail",
                       {"parts": len(files), "sizes": sizes, "issues": issues[:5], "in_no_part": missing[:5]}))
        if any(not 25 <= n <= 30 for n in sizes):
            it.append(item(f"{name}: part sizes within the protocol's 25-30 items per judge", "warn", sizes))
        return by_part

    def _judged(self, name: str, items: dict, it: list, parts: dict):
        """{id: {verdict, file}} from out_<name>_*.json, with the V-06 output checks."""
        files = sorted(self.jdir.glob(f"out_{name}_*.json")) if self.jdir.is_dir() else []
        if not files:
            it.append(item(f"{name}: judge outputs", "missing", f"judges/out_{name}_*.json"))
            return None
        seen: dict = {}
        unknown, invalid, unreadable, no_ev, bad_ev, part_mismatch = [], [], [], [], [], []
        n_parts = 0
        for f in files:
            obj, err = load_json_safe(f)
            if obj is None:
                unreadable.append(f"{f.name}: {err}")
                continue
            recs = find_records(obj)
            if not recs:
                unreadable.append(f"{f.name}: no records")
                continue
            here = set()
            for r in recs:
                jid = rec_id(r)
                here.add(jid)
                if jid not in items:
                    unknown.append(jid)
                    continue
                vd = str(_first(r, VERDICT_KEYS) or "").strip().lower()
                if vd not in VERDICTS:
                    invalid.append(jid)
                parts_ev = evidence_parts(_first(r, EVIDENCE_KEYS))
                output = _first(items[jid], OUTPUT_KEYS) or ""
                for part in parts_ev:
                    n_parts += 1
                    if not snippet_found(part, output):
                        bad_ev.append((jid, part[:80]))
                if not parts_ev and vd in ("full", "partial"):
                    no_ev.append(jid)
                seen.setdefault(jid, []).append({"verdict": vd, "file": f.name})
            k = _part_no(f)
            if parts and k in parts and here != parts[k]:
                part_mismatch.append(f.name)
        multi = sorted(j for j, val in seen.items() if len(val) > 1)
        never = sorted(set(items) - set(seen))
        self.bad_ev[name] = {j for j, _ in bad_ev}
        it.append(item(f"{name}: outputs readable", "pass" if not unreadable else "fail", unreadable[:5]))
        it.append(item(f"{name}: every item judged exactly once",
                       "pass" if not multi and not never and not unknown and not unreadable else "fail",
                       {"items": len(items), "judged": len(seen), "more_than_once": multi[:5], "never": never[:5],
                        "n_never": len(never), "unknown_ids": unknown[:5]}))
        it.append(item(f"{name}: verdicts are full/partial/none", "pass" if not invalid else "fail", invalid[:5]))
        it.append(item(f"{name}: every evidence snippet occurs verbatim in its tool output",
                       "pass" if not bad_ev else "fail",
                       {"snippets": n_parts, "not_found": len(bad_ev), "first": bad_ev[:5]}))
        if no_ev:
            it.append(item(f"{name}: full/partial verdicts without evidence", "warn", no_ev[:10]))
        if part_mismatch:
            it.append(item(f"{name}: an output file's ids differ from its pack part", "warn", part_mismatch[:5]))
        return {j: val[0] for j, val in seen.items()}

    def _content(self, name: str, spec: dict, items: dict, unblind: dict, n_exp: int, it: list):
        out_bad, q_bad, missing_l2, compared = [], [], set(), 0
        for jid, (st, qid) in unblind.items():
            pr = items.get(jid) or {}
            l2 = self.v.main("L2", st, "CEN")
            if l2 is None:
                missing_l2.add(st)
            else:
                compared += 1
                if _first(pr, OUTPUT_KEYS) != l2.raw.get(spec["path"], {}).get(qid):
                    out_bad.append(jid)
            a = self.answers.get(qid, {})
            if _first(pr, QUESTION_KEYS) != a.get("query") or \
                    (_first(pr, REFERENCE_KEYS) or "") != (a.get("reference_answer") or ""):
                q_bad.append(jid)
        name_out = f"{name}: tool outputs equal L2 {{{','.join(spec['states'])}}}_CEN raw outputs ({spec['path']})"
        if missing_l2:
            it.append(item(name_out, "missing", f"L2 CEN missing for {sorted(missing_l2)}"))
        else:
            it.append(item(name_out, "pass" if not out_bad and compared == n_exp else "fail",
                           {"compared": compared, "expected": n_exp, "differing": len(out_bad), "first": out_bad[:5]}))
        it.append(item(f"{name}: question and reference answer equal the CEN-A fixture",
                       "pass" if not q_bad and len(unblind) == n_exp else "fail",
                       {"compared": len(unblind), "expected": n_exp, "differing": len(q_bad), "first": q_bad[:5]}))

    def _manifest_inputs(self, name: str, manifest, spec: dict, it: list):
        if not manifest or not isinstance(manifest.get("inputs"), dict):
            return
        diffs, absent = {}, []
        for st in spec["states"]:
            rec = manifest["inputs"].get(st)
            run = self.v.runs.get(("L2", f"{st}_CEN"))
            if run is None or not run.present:
                absent.append(st)
                continue
            want = rec.get("sha256") if isinstance(rec, dict) else None
            if want != run.sha256:
                diffs[st] = {"manifest": want, "verified_file": run.sha256}
        label = f"{name}: built from the L2 CEN files verified here (SHA-256 in the manifest)"
        if absent:
            it.append(item(label, "missing", f"L2 CEN missing for {absent}"))
        else:
            it.append(item(label, "pass" if not diffs else "fail", diffs))

    def _harness_results(self, name: str, counts, it: list):
        """Cross-check judge_pack.py's own unblinding (results_<name>.json) against this recomputation."""
        obj, err = load_json_safe(self.jdir / f"results_{name}.json")
        if not isinstance(obj, dict):
            if err != "missing":
                it.append(item(f"{name}: results_{name}.json", "warn", err or "not a JSON object"))
            return
        theirs = obj.get("counts_by_state")
        if counts is not None and isinstance(theirs, dict):
            same = set(theirs) == set(counts) and all(theirs.get(s) == counts[s] for s in counts)
            it.append(item(f"{name}: harness unblinding (results_{name}.json) counts equal the recomputation",
                           "pass" if same else "fail", {"harness": theirs, "verifier": counts}))
        nv = obj.get("evidence_not_verbatim")
        if isinstance(nv, list):
            theirs_nv = {str(x.get("id")) if isinstance(x, dict) else str(x) for x in nv}
            mine = self.bad_ev.get(name, set())
            if theirs_nv != mine:
                it.append(item(f"{name}: results_{name}.json flags different items as non-verbatim", "warn",
                               {"harness": len(theirs_nv), "verifier": len(mine),
                                "harness_only": sorted(theirs_nv - mine)[:5], "verifier_only": sorted(mine - theirs_nv)[:5],
                                "rule": "the verifier splits evidence on ' ... ' (data contract) and accepts surrounding "
                                        "quotes or ellipses"}))

    def _seeded(self, name: str, spec: dict, unblind: dict, items: dict, it: list):
        """Does the key map reproduce random.Random(seed).shuffle of the state-major item list? (warn only)"""
        prefix = next(iter(items))[0] if items else "J"
        order = [(st, q) for st in spec["states"] for q in self.judged]
        random.Random(SEED).shuffle(order)
        expected = {f"{prefix}{i:04d}": pair for i, pair in enumerate(order, 1)}
        it.append(item(f"{name}: ids follow random.Random({SEED}).shuffle of the (state, query) list, state-major",
                       "pass" if expected == unblind else "warn",
                       "" if expected == unblind else "order differs from this reconstruction of the shuffle"))

    # -- packs

    def pack(self, name: str, spec: dict) -> dict:
        res = {"pack": name, "status": "missing", "items": [], "counts": None, "by_state": None, "kappa": None,
               "kappa_by_state": None, "complete": False, "n_expected": None}
        it = res["items"]
        pf, kf = self.jdir / f"pack_{name}.json", self.jdir / f"keymap_{name}.json"
        outs = sorted(self.jdir.glob(f"out_{name}_*.json")) if self.jdir.is_dir() else []
        if not pf.exists() and not kf.exists() and not outs:
            if spec["optional"]:
                res["status"] = "not_run"
                return res
            it.append(item(f"{name}: pack, key map and outputs", "missing", str(self.jdir)))
            return res
        items = self._load_items(pf, name, it)
        kobj, kerr = load_json_safe(kf)
        if kobj is None:
            it.append(item(f"{name}: keymap_{name}.json readable", "missing" if kerr == "missing" else "fail", kerr))
        if items is None or kobj is None:
            return res
        n_exp = JUDGE_N[name]
        res["n_expected"] = n_exp
        derived = len(self.judged) * len(spec["states"])
        it.append(item(f"{name}: the fixtures give section 16's {n_exp} items ({CEN_A_N} CEN-A queries = "
                       f"{len(self.non_adv)} non-adversarial minus {list(CEN_A_EXCLUDED)}, x {len(spec['states'])} states)",
                       "pass" if derived == n_exp and len(self.judged) == CEN_A_N
                       and tuple(self.excluded) == CEN_A_EXCLUDED else "fail",
                       {"judged_queries": len(self.judged), "excluded": self.excluded, "items": derived}))
        manifest = self._manifest(name, it, {"pack": name, "path": spec["path"], "states": list(spec["states"]),
                                             "seed": SEED, "n_items": n_exp, "queries_per_state": CEN_A_N,
                                             "excluded_qids": list(CEN_A_EXCLUDED)})
        self._hash(name, kf, it, manifest, section14=True)
        self._manifest_inputs(name, manifest, spec, it)
        it.append(item(f"{name}: {n_exp} items ({CEN_A_N} CEN-A queries x {len(spec['states'])} states)",
                       "pass" if len(items) == n_exp else "fail", len(items)))
        self._labels(name, items, it)
        parts = self._parts(name, items, it)
        # Key map: id -> "qid|STATE"; the path is the pack's (section 8).
        km = keymap_entries(kobj)
        it.append(item(f"{name}: key map covers exactly the pack items", "pass" if set(km) == set(items) and km else "fail",
                       {"pack_only": sorted(set(items) - set(km))[:5], "keymap_only": sorted(set(km) - set(items))[:5]}))
        unblind, bad = {}, []
        valid = set(self.judged)
        for jid, val in km.items():
            uv = unblind_value(val)
            n = cen_number(uv[0]) if uv else None
            qid = f"CEN-{n:03d}" if n is not None else None
            if uv is None or uv[1] not in spec["states"] or qid not in valid:
                bad.append((jid, val))
                continue
            unblind[jid] = (uv[1], qid)
        dup = len(unblind) - len(set(unblind.values()))
        it.append(item(f"{name}: key map is (state x CEN-A query), each pair once",
                       "pass" if not bad and not dup and len(unblind) == n_exp and set(unblind) == set(items) else "fail",
                       {"mapped": len(unblind), "expected": n_exp, "invalid": bad[:5], "duplicate_pairs": dup}))
        self._seeded(name, spec, unblind, items, it)
        self._content(name, spec, items, unblind, n_exp, it)
        first = self._judged(name, items, it, parts) or {}
        valid_first = {j: r["verdict"] for j, r in first.items() if r["verdict"] in VERDICTS}
        # Re-judged subset.
        rmap, second = {}, {}
        if spec["rejudge"] or (self.jdir / f"pack_{name}R.json").exists():
            rmap, second = self.rejudge(name, items, n_exp, it, required=spec["rejudge"])
        # Unblinded tallies.
        counts = {s: {vd: 0 for vd in VERDICTS} for s in spec["states"]}
        by_state = {s: {} for s in spec["states"]}
        for jid, (st, qid) in unblind.items():
            vd = valid_first.get(jid)
            if vd is not None:
                counts[st][vd] += 1
                by_state[st][qid] = vd
        complete = len(unblind) == n_exp and all(len(by_state[s]) == len(self.judged) for s in spec["states"])
        res["complete"] = complete
        if unblind and valid_first:
            res["counts"], res["by_state"] = counts, by_state
            res["status"] = "ok" if complete else "incomplete"
        self._harness_results(name, counts if unblind and valid_first else None, it)
        res["_unblind"], res["_verdicts"], res["_items"] = unblind, valid_first, items   # for discordant_rejudge
        if rmap and second:
            rcounts = {s: {vd: 0 for vd in VERDICTS} for s in spec["states"]}
            for rid, src in rmap.items():
                vd = second.get(rid, {}).get("verdict")
                if vd in VERDICTS and src in unblind:
                    rcounts[unblind[src][0]][vd] += 1
            res["counts_rejudge"] = rcounts
            self._harness_results(f"{name}R", rcounts, it)
        n_exp_r = REJUDGE_N.get(f"{name}R", round(REJUDGE_FRACTION * n_exp))
        if rmap and second:
            pairs = [(valid_first.get(src), second[rid]["verdict"], unblind.get(src, (None,))[0])
                     for rid, src in rmap.items() if rid in second]
            pairs = [p for p in pairs if p[0] in VERDICTS and p[1] in VERDICTS]
            res["kappa"] = {"n": len(pairs), "expected": n_exp_r, "complete": len(pairs) == n_exp_r,
                            "kappa": cohen_kappa([p[0] for p in pairs], [p[1] for p in pairs]),
                            "agreement": _agreement([(p[0], p[1]) for p in pairs])}
            res["kappa_by_state"] = {}
            for s in spec["states"]:
                sp = [(p[0], p[1]) for p in pairs if p[2] == s]
                res["kappa_by_state"][s] = {"n": len(sp), "kappa": cohen_kappa([a for a, _ in sp], [b for _, b in sp]),
                                            "agreement": _agreement(sp)}
        return res

    def discordant_rejudge(self, it: list) -> dict:
        """R2-3 (a round only): C-11's discordant queries re-judged, recomputed from the files.

        A CEN-A query is discordant when its J1 verdicts for B and C differ on full. Each of
        its B and C items is re-issued under a D id (keymap_J1D.json: D id -> J1 id) in
        judges/pack_J1D_part<k>.json, no part holding both states of one query, and judged
        by two new judges (out_J1D_part<k>_<judge>.json). An item counts as full when at
        least 2 of its 3 verdicts (J1's and the two new) say full; b and c compare B and C
        on that, over all CEN-A queries (a concordant query keeps its J1 verdicts). It is
        informational: its checks join V-06 as pass or warn, never fail."""
        name, local = "J1D", []
        res = {"status": "missing", "queries": None, "n_items": None, "judges_per_item": None, "b": None, "c": None,
               "mcnemar": None, "rows": []}

        def done(status):
            res["status"] = status
            it.extend(dict(i, status="warn") if i["status"] == "fail" else i for i in local)
            return res

        j1 = self.packs.get("J1") or {}
        unblind, verdicts, j1_items = j1.get("_unblind"), j1.get("_verdicts") or {}, j1.get("_items") or {}
        kf = self.jdir / "keymap_J1D.json"
        parts_f = sorted(self.jdir.glob("pack_J1D_part*.json"), key=lambda q: (_part_no(q) or 0, q.name))
        outs_f = sorted(self.jdir.glob("out_J1D_part*_*.json"))
        if not kf.exists() and not parts_f and not outs_f:
            local.append(item(f"{name}: pack, key map and outputs (R2-3)", "warn", "missing"))
            return done("missing")
        if not (j1.get("complete") and unblind):
            local.append(item(f"{name}: J1 complete (its verdicts select the queries)", "fail", "J1 incomplete"))
            return done("invalid")
        jid_of = {(st, q): jid for jid, (st, q) in unblind.items()}
        queries = [q for q in self.judged if (verdicts.get(jid_of.get(("B", q))) == "full")
                   != (verdicts.get(jid_of.get(("C", q))) == "full")]
        want = {jid_of[(st, q)]: (st, q) for q in queries for st in ("B", "C")}
        res["queries"] = queries
        kobj, kerr = load_json_safe(kf)
        km = {d: source_value(v) for d, v in keymap_entries(kobj).items()} if kobj is not None else {}
        local.append(item(f"{name}: key map gives each B and C item of the {len(queries)} discordant queries one D id",
                          "pass" if km and sorted(km.values()) == sorted(want) else "fail",
                          {"error": kerr, "mapped": len(km), "expected": len(want),
                           "not_discordant": sorted(set(km.values()) - set(want))[:5],
                           "not_mapped": sorted(set(want) - set(km.values()))[:5]}))
        if kobj is not None:
            self._hash(name, kf, local, None, section14=True)
        # Parts: each item equals its J1 item; no part holds both states of one query.
        part_ids, content_bad, both = {}, [], []
        for pf in parts_f:
            obj, err = load_json_safe(pf)
            recs = find_records(obj) if obj is not None else []
            if obj is None:
                content_bad.append(f"{pf.name}: {err}")
            ids = [rec_id(r) for r in recs]
            part_ids[_part_no(pf)] = set(ids)
            for r in recs:
                src = j1_items.get(km.get(rec_id(r)))
                if src is None or any(r.get(k) != src.get(k) for k in PACK_ITEM_KEYS if k != "id"):
                    content_bad.append(rec_id(r))
            qs = [want.get(km.get(i), (None, None))[1] for i in ids]
            both += sorted({q for q in qs if q is not None and qs.count(q) > 1})
        all_ids = [i for ids in part_ids.values() for i in ids]
        local.append(item(f"{name}: parts hold every D id once, each equal to its J1 item",
                          "pass" if parts_f and not content_bad and sorted(all_ids) == sorted(km) else "fail",
                          {"parts": len(parts_f), "sizes": [len(v) for v in part_ids.values()],
                           "differing": content_bad[:5]}))
        local.append(item(f"{name}: no part holds both states of one query", "pass" if parts_f and not both else "fail",
                          both[:5]))
        # Outputs: two new judges per part, each with exactly the part's ids.
        new, per_part, bad_files, bad_ev, n_snip = {}, {}, [], [], 0
        for f in outs_f:
            m = re.search(r"_part(\d+)_([a-z])$", f.stem)
            obj, err = load_json_safe(f)
            recs = find_records(obj) if obj is not None else []
            k = int(m.group(1)) if m else None
            if m is None or obj is None or k not in part_ids or {rec_id(r) for r in recs} != part_ids[k] \
                    or len(recs) != len(part_ids[k]):
                bad_files.append(f.name)
                continue
            per_part.setdefault(k, []).append(m.group(2))
            for r in recs:
                vd = str(_first(r, VERDICT_KEYS) or "").strip().lower()
                if vd not in VERDICTS:
                    bad_files.append(f"{f.name}: {rec_id(r)} verdict {vd!r}")
                    continue
                new.setdefault(rec_id(r), []).append(vd)
                src = j1_items.get(km.get(rec_id(r))) or {}
                for part in evidence_parts(_first(r, EVIDENCE_KEYS)):
                    n_snip += 1
                    if not snippet_found(part, _first(src, OUTPUT_KEYS) or ""):
                        bad_ev.append((rec_id(r), part[:80]))
        local.append(item(f"{name}: two judge outputs per part, each with exactly the part's ids and valid verdicts",
                          "pass" if part_ids and not bad_files and all(len(per_part.get(k, [])) == 2 for k in part_ids)
                          else "fail", {"judges_per_part": {k: per_part.get(k, []) for k in sorted(part_ids)},
                                        "bad": bad_files[:5]}))
        local.append(item(f"{name}: every evidence snippet occurs verbatim in its tool output", "pass" if not bad_ev
                          else "warn", {"snippets": n_snip, "not_found": len(bad_ev), "first": bad_ev[:5]}))
        # Majority of three, then b and c over every CEN-A query.
        votes = {jid: [verdicts.get(jid)] + [v for d, s in km.items() if s == jid for v in new.get(d, [])]
                 for jid in want}
        res["n_items"], res["judges_per_item"] = len(want), sorted({len(v) for v in votes.values()})
        full = {jid: sum(v == "full" for v in vs) >= 2 for jid, vs in votes.items()}
        pairs = []
        for q in self.judged:
            b_id, c_id = jid_of[("B", q)], jid_of[("C", q)]
            if q in queries:
                pairs.append((full[b_id], full[c_id]))
                res["rows"].append({"qid": q, "B": votes[b_id], "C": votes[c_id]})
            else:
                pairs.append((verdicts.get(b_id) == "full", verdicts.get(c_id) == "full"))
        complete = all(len(v) == 3 for v in votes.values())
        if complete:
            res["mcnemar"] = mcnemar(pairs)
            res["b"], res["c"] = res["mcnemar"]["b"], res["mcnemar"]["c"]
        failed = any(i["status"] == "fail" for i in local)
        return done("invalid" if failed else "ok" if complete else "incomplete")

    def rejudge(self, name: str, items: dict, n_src: int, it: list, required: bool):
        """The re-judged subset <name>R: R ids mapped to source ids; returns ({R id: source id}, {R id: verdict rec})."""
        rname = f"{name}R"
        rp, rk = self.jdir / f"pack_{rname}.json", self.jdir / f"keymap_{rname}.json"
        routs = sorted(self.jdir.glob(f"out_{rname}_*.json")) if self.jdir.is_dir() else []
        if not rp.exists() and not rk.exists() and not routs:
            it.append(item(f"{rname}: re-judge pack, key map and outputs", "missing" if required else "warn", str(self.jdir)))
            return {}, {}
        ritems = self._load_items(rp, rname, it)
        kobj, kerr = load_json_safe(rk)
        if kobj is None:
            it.append(item(f"{rname}: keymap_{rname}.json readable", "missing" if kerr == "missing" else "fail", kerr))
        if ritems is None or kobj is None:
            return {}, {}
        n_exp = REJUDGE_N.get(rname, round(REJUDGE_FRACTION * n_src))
        it.append(item(f"{rname}: section 16's {n_exp} items = round({REJUDGE_FRACTION} x {n_src})",
                       "pass" if round(REJUDGE_FRACTION * n_src) == n_exp else "fail",
                       {"round": round(REJUDGE_FRACTION * n_src), "expected": n_exp}))
        manifest = self._manifest(rname, it, {"pack": rname, "source_pack": name, "seed": SEED,
                                              "fraction": REJUDGE_FRACTION, "n_items": n_exp, "source_items": n_src})
        if manifest is not None and manifest.get("source_keymap_sha256") is not None:
            src = sha256_file(self.jdir / f"keymap_{name}.json")
            rec = str(manifest["source_keymap_sha256"]).lower()
            it.append(item(f"{rname}: manifest's source key-map SHA-256 equals keymap_{name}.json",
                           "pass" if rec == src else "fail", {"computed": src, "manifest": rec}))
        self._hash(rname, rk, it, manifest, section14=False)
        it.append(item(f"{rname}: {n_exp} items (round({REJUDGE_FRACTION} x {n_src}))",
                       "pass" if len(ritems) == n_exp else "fail", len(ritems)))
        self._labels(rname, ritems, it)
        rparts = self._parts(rname, ritems, it)
        km = keymap_entries(kobj)
        rmap, bad = {}, []
        for rid, val in km.items():
            src = source_value(val)
            if src not in items:
                bad.append((rid, val))
                continue
            rmap[rid] = src
        dup = len(rmap) - len(set(rmap.values()))
        it.append(item(f"{rname}: key map sends each re-judge item to a distinct {name} item",
                       "pass" if not bad and not dup and set(rmap) == set(ritems) and rmap else "fail",
                       {"mapped": len(rmap), "invalid": bad[:5], "duplicate_sources": dup,
                        "pack_only": sorted(set(ritems) - set(km))[:5], "keymap_only": sorted(set(km) - set(ritems))[:5]}))
        same = [rid for rid, src in rmap.items() if rid in ritems and
                all(ritems[rid].get(k) == items[src].get(k) for k in PACK_ITEM_KEYS if k != "id")]
        it.append(item(f"{rname}: each re-judge item equals its {name} item (question, reference answer, tool output)",
                       "pass" if rmap and len(same) == len(rmap) == len(ritems) else "fail",
                       {"equal": len(same), "items": len(ritems)}))
        prefix = next(iter(ritems))[0] if ritems else "R"
        expected = {f"{prefix}{i:04d}": s for i, s in enumerate(random.Random(SEED).sample(sorted(items), n_exp), 1)} \
            if n_exp <= len(items) else {}
        it.append(item(f"{rname}: sample follows random.Random({SEED}).sample of the sorted {name} ids",
                       "pass" if expected == rmap else "warn",
                       "" if expected == rmap else "differs from this reconstruction of the sample"))
        second = self._judged(rname, ritems, it, rparts) or {}
        return rmap, second


# ── CI gates (C-14) ─────────────────────────────────────────────────

def parse_pytest(text: str) -> dict:
    summ = None
    for line in text.splitlines():
        if re.search(r"\b\d+ (passed|failed|errors?)\b", line) and re.search(r"\bin [0-9.]+s", line):
            summ = line.strip()
    if summ is None:
        return {"ok": False, "summary": None}
    failed = re.search(r"\b(\d+) failed\b", summ)
    errors = re.search(r"\b(\d+) errors?\b", summ)
    passed = re.search(r"\b(\d+) passed\b", summ)
    return {"ok": bool(passed) and int(passed.group(1)) > 0 and not failed and not errors, "summary": summ}


def parse_ci_header(text: str) -> dict:
    """The "# key: value" header the CI step writes before the pytest log."""
    lines = text.split("\n")
    head = {}
    if lines and lines[0].startswith("# CI run for state "):
        head["state"] = lines[0][len("# CI run for state "):].strip()
    for line in lines[1:]:
        if not line.startswith("# "):
            break
        key, sep, val = line[2:].partition(": ")
        if sep:
            head[key.strip()] = val
    return head


def pytest_plugins_of(cmd: list) -> list:
    """The plugins a pytest command line loads, as pytest's pre-parse reads them: -p NAME or -pNAME."""
    args = cmd[cmd.index("pytest") + 1:] if "pytest" in cmd else list(cmd)
    out = []
    for i, a in enumerate(args):
        if a == "-p" and i + 1 < len(args):
            out.append(args[i + 1])
        elif a.startswith("-p") and len(a) > 2:
            out.append(a[2:])
    return out


def ci_run(v: Verifier, state: str, decisive: bool = True) -> dict:
    """Provenance and outcome of one CI run (verification/ci_<state>.json and .txt). With --round,
    a decisive run's command must load exactly the round's plugins for the state (CI_PLUGINS) and
    record the SHA-256 of each plugin file (json plugin_sha256 and the "# plugins:" header line);
    a plugin file that differs now leaves the run unverifiable."""
    jp, tp = v.vdir / f"ci_{state}.json", v.vdir / f"ci_{state}.txt"
    rec, err = load_json_safe(jp)
    res = {"state": state, "files": [jp.name, tp.name]}
    if not isinstance(rec, dict) or not tp.exists():
        bad = rec is not None or err not in (None, "missing")
        res.update(status="fail" if bad else "missing",
                   detail={jp.name: err or ("present" if rec is not None else "missing"),
                           tp.name: "present" if tp.exists() else "missing"})
        return res
    text = tp.read_text(encoding="utf-8", errors="replace")
    head = parse_ci_header(text)
    probs, unverifiable = [], []
    if rec.get("state") != state or head.get("state") != state:
        probs.append(f"state: json {rec.get('state')!r}, header {head.get('state')!r}")
    cmd = rec.get("command")
    if not isinstance(cmd, list):
        probs.append("ci json has no command list")
    else:
        sc = [str(c) for c in cmd]
        if not ("pytest" in sc and any(sc[i] == "-m" and sc[i + 1] == CI_MARK for i in range(len(sc) - 1))):
            probs.append(f"command is not pytest -m {CI_MARK!r}: {sc}")
        if any(c == "-k" or c.startswith("-k") for c in sc[1:]) or any(c.startswith("--deselect") for c in sc):
            probs.append(f"command restricts the test selection: {sc}")
        if head.get("command") != " ".join(sc):
            probs.append("header command differs from the json command")
        if decisive and CI_PLUGINS is not None:   # --round: exactly the round's plugins for this state
            used, allowed = sorted(pytest_plugins_of(sc)), CI_PLUGINS.get(state, [])
            res["plugins"] = used
            if used != allowed:
                probs.append(f"command loads pytest plugins {used}; the round allows {allowed} for state {state}")
            recorded = rec.get("plugins", used)
            if not isinstance(recorded, list) or sorted(map(str, recorded)) != used:
                probs.append(f"ci json records plugins {recorded!r}; the command loads {used}")
            # The plugin files lie outside the state's checkout: the run records their SHA-256.
            digests = rec.get("plugin_sha256", {} if not used else None)
            try:
                head_digests = json.loads(head["plugins"]) if "plugins" in head else {}
            except ValueError:
                head_digests = None
            if not (isinstance(digests, dict) and sorted(digests) == used and all(
                    isinstance(h, str) and re.fullmatch(r"[0-9a-f]{64}", h) for h in digests.values())):
                probs.append(f"ci json records plugin SHA-256 {digests!r} for the plugins {used}")
            elif head_digests != digests:
                probs.append("header and json plugin SHA-256 differ")
            else:
                res["plugin_sha256"] = digests
                for name, h in sorted(digests.items()):
                    f = SCRIPT.parent / "pytest_plugins" / f"{name}.py"
                    now = sha256_file(f) if f.is_file() else None
                    if now != h:
                        unverifiable.append(f"pytest_plugins/{name}.py has SHA-256 {now} now; the run loaded {h}")
    try:
        env = json.loads(head.get("env", ""))
    except ValueError:
        env = None
    if not isinstance(env, dict) or env.get("CANDLEKEEP_DEVICE") != "mps":
        probs.append(f"CANDLEKEEP_DEVICE in the run's environment: {env.get('CANDLEKEEP_DEVICE') if isinstance(env, dict) else 'not recorded'}")
    sha, tree = str(rec.get("git_sha") or ""), rec.get("src_tree_sha")
    if head.get("git_sha") != sha or head.get("src_tree_sha") != tree:
        probs.append("header and json git_sha / src_tree_sha differ")
    exp_tree, how = v.expected_tree(state)
    if exp_tree is None:
        unverifiable.append(how)
    elif tree != exp_tree:
        probs.append(f"src_tree_sha {tree} is not {how} ({exp_tree})")
    full = v.rev(f"{sha}^{{commit}}") if re.fullmatch(r"[0-9a-fA-F]{7,40}", sha) else None
    if full is None:
        probs.append(f"git_sha {sha!r} does not resolve")
    elif state == "A" and full != v.rev(STATE_REF["A"]):
        probs.append(f"git_sha {full} is not {STATE_REF['A']}")
    elif state == "B":
        _o, _e, rc = git(v.repo, "diff", "--quiet", STATE_REF["B"], full, "--", "src")
        if rc != 0:
            probs.append(f"git diff {STATE_REF['B']} {full[:12]} -- src is not empty")
    elif state == "C":
        if C_REF and full != v.rev(C_REF):
            probs.append(f"git_sha {full} is not {C_REF}")
        env_c = v.env_info("C")
        if not env_c or not env_c.get("git_sha"):
            unverifiable.append("env/C.txt git SHA")
        elif full != v.rev(env_c["git_sha"]):
            probs.append(f"git_sha {full} differs from env/C.txt {env_c['git_sha']}")
    if rec.get("src_dirty"):
        probs.append("src/ had uncommitted changes during the run")
    if rec.get("invalid"):
        probs.append(f"the CI step marked the run invalid: {rec['invalid']}")
    if rec.get("provenance_unchanged") is False:
        probs.append("the checkout changed during the run")
    py = parse_pytest(text)
    if state in ("A", "B", "C"):   # A is the baseline: it must complete too (section 16)
        if rec.get("exit_code") != 0 or rec.get("passed") is False:
            probs.append(f"pytest exit code {rec.get('exit_code')}")
        if not py["ok"]:
            probs.append(f"pytest summary line: {py['summary']}")
    res.update(status="fail" if probs else ("missing" if unverifiable else "pass"), problems=probs,
               unverifiable=unverifiable, exit_code=rec.get("exit_code"), pytest=py["summary"], git_sha=sha,
               src_tree_sha=tree, counts=rec.get("counts"), checkout=rec.get("checkout"),
               git_status_unchanged=rec.get("git_status_unchanged"))
    return res


def router_summary(path: Path):
    obj, err = load_json_safe(path)
    if not isinstance(obj, dict) or not isinstance(obj.get("summary"), dict):
        return None, err or "no 'summary' object"
    return obj["summary"], None


def ci_compare(v: Verifier, state: str, base_files: dict, base_status: str, md: Path | None,
               cur_dir: Path | None = None) -> dict:
    """compare_benchmarks.py's rule re-applied to the router benchmark JSONs: red when current - baseline < -0.01
    for avg_precision or avg_recall. A missing file or a zero baseline value (the script prints "New") is missing."""
    rows, missing, probs = [], [], []
    for p in CI_PATHS:
        bs, be = router_summary(base_files[p])
        cs, ce = router_summary((cur_dir or v.vdir) / f"ci_{state}_router_{p}_benchmark.json")
        if bs is None or cs is None:
            missing.append({"path": p, "baseline": be or "ok", "current": ce or "ok"})
            continue
        for key in CI_METRICS:
            b_val, c_val = bs.get(key, 0), cs.get(key, 0)
            if not (is_num(b_val) and is_num(c_val)):
                probs.append(f"{p} {key}: non-numeric ({b_val!r}, {c_val!r})")
                continue
            if b_val == 0:
                missing.append({"path": p, "metric": key, "baseline": "0 (compare_benchmarks.py prints 'New', never red)"})
                continue
            d = float(c_val) - float(b_val)
            rows.append({"path": p, "metric": key, "baseline": b_val, "current": c_val, "delta": d,
                         "red": d < -CI_RED_DROP})
        bl, cl = bs.get("avg_latency_ms"), cs.get("avg_latency_ms")
        if is_num(bl) and is_num(cl) and bl:
            rows.append({"path": p, "metric": "avg_latency_ms", "baseline": bl, "current": cl,
                         "change": (cl - bl) / bl, "red": False, "info": True})
    red = [r for r in rows if r["red"]]
    md_info = None
    if md is not None and md.exists():
        text = md.read_text(encoding="utf-8", errors="replace")
        shown = [p for p in CI_PATHS if CI_LABEL[p] in text]
        mine = sum(1 for r in red if r["path"] in shown)
        md_info = {"file": md.name, "paths_shown": shown, "red_marks": text.count("\U0001F534"), "recomputed_red": mine}
        if md_info["red_marks"] != mine:
            probs.append(f"{md.name} shows {md_info['red_marks']} red marks; the rule gives {mine} for {shown}")
    if red or probs or base_status == "fail":
        status = "fail"
    elif missing or base_status != "pass":
        status = "missing"
    else:
        status = "pass"
    return {"status": status, "red": len(red), "rows": rows, "missing": missing, "problems": probs,
            "baseline_run": base_status, "rendering": md_info}


def _cmp_txt(c: dict) -> str:
    """A comparison's outcome; "(N red)" only when the rule could be applied to every path."""
    if c.get("missing") or c.get("baseline_run") != "pass":
        return f"{c['status']} (not compared: baseline {c.get('baseline_run')})"
    return f"{c['status']} ({c.get('red')} red)"


def _info_txt(ci: dict) -> str:
    """The informational run's comparison (section 16), with every red row."""
    info = ci.get("info")
    if not info:
        return ""
    parts = []
    for s in ("B", "C"):
        c = info.get(f"compare_{s}") or {}
        reds = "; ".join(f"{r['path']} {r['metric'].replace('avg_', '')} {r['baseline']:.3f}→{r['current']:.3f}"
                         for r in c.get("rows", []) if r.get("red"))
        parts.append(f"{s} {c.get('red')} red" + (f" ({reds})" if reds else ""))
    tests = ", ".join(f"{s} {info['runs'][s]['status']}" for s in STATES)
    return f"informational run, model calls serialised (not a decision): tests {tests}; vs A: " + ", ".join(parts) + "; "


def ci_gates(v: Verifier) -> dict:
    out = {}
    runs = {s: ci_run(v, s) for s in STATES}
    out["baseline_A"] = runs["A"]
    a_files = {p: v.vdir / f"ci_A_router_{p}_benchmark.json" for p in CI_PATHS}
    for s in ("B", "C"):
        out[f"tests_{s}"] = runs[s]
        out[f"compare_{s}"] = ci_compare(v, s, a_files, runs["A"]["status"], v.vdir / f"ci_{s}_compare_A.md")
        checkout = Path(runs[s].get("checkout") or (v.repo if s == "B" else
                                                    STATE_CHECKOUT.get("C", v.eval_home / "worktrees" / "C")))
        arch = {p: checkout / "tests" / "results" / "archive" / f"router_{p}_benchmark.json" for p in CI_PATHS}
        a = ci_compare(v, s, arch, "pass", v.vdir / f"ci_{s}_compare_archive.md")
        out[f"archive_{s}"] = {"status": "info", "red": a["red"], "missing": a["missing"], "rows": a["rows"],
                               "rendering": a["rendering"], "note": "informational (archive baselines are CPU runs)"}
    # Section 16: informational run with model calls serialised (never decisive).
    idir = v.root / "ci_info" / "verification"
    if idir.is_dir():
        info_runs = {}
        for s in STATES:
            sub = Verifier.__new__(Verifier)
            sub.__dict__.update(v.__dict__)
            sub.vdir = idir
            info_runs[s] = ci_run(sub, s, decisive=False)   # informational: not subject to a round's plugin rule
        ia = {p: idir / f"ci_A_router_{p}_benchmark.json" for p in CI_PATHS}
        out["info"] = {"note": "informational: same command plus -p mps_serial (section 16); not a decision",
                       "runs": info_runs}
        for s in ("B", "C"):
            out["info"][f"compare_{s}"] = ci_compare(v, s, ia, info_runs["A"]["status"],
                                                   idir / f"ci_{s}_compare_A.md", cur_dir=idir)
    return out


# ── Section 15 numbers and criteria ─────────────────────────────────

_QIDS: dict = {}


def suite_qids(suite: str) -> frozenset:
    if suite not in _QIDS:
        _QIDS[suite] = frozenset(q["qid"] for q in derive_queries(suite))
    return _QIDS[suite]


def nonadv_qids(suite: str) -> frozenset:
    return frozenset(q["qid"] for q in derive_queries(suite) if q["category"] != "adversarial")


def complete_run(v: Verifier, layer, state, suite, path, role="main"):
    """The run when it has a per-query record for every query of the suite on this path, else None."""
    r = v.main(layer, state, suite, role)
    if r is None or path not in r.pq or set(r.pq[path]) != suite_qids(suite):
        return None
    return r


def _series(v: Verifier, layer, state, suites, path, key, role="main", only=None):
    """{"suite|qid": value} over suites for one state, or None unless every run covers all of its queries."""
    out = {}
    for s in suites:
        r = complete_run(v, layer, state, s, path, role)
        if r is None:
            return None
        keep = only(s) if only else None
        for qid, rec in r.pq[path].items():
            if keep is not None and qid not in keep:
                continue
            val = rec.get(key)
            if val is not None:
                out[f"{s}|{qid}"] = val
    return out


def _paired(ref: dict, cand: dict):
    keys = [k for k in ref if k in cand]
    return [ref[k] for k in keys], [cand[k] for k in keys]


def _boot(ref, cand):
    if ref is None or cand is None:
        return None
    a, b = _paired(ref, cand)
    return paired_bootstrap([y - x for x, y in zip(a, b)])


def _mcn(ref, cand):
    if ref is None or cand is None:
        return None
    a, b = _paired(ref, cand)
    return mcnemar(list(zip(a, b)))


def l1_cell(v: Verifier, suites, path) -> dict:
    cell = {"values": {}, "delta_BA": {}, "delta_BA_nonadv": {}, "mcnemar_BA": {}, "latency_ratio_BA": None,
            "ranking_CB": None}
    series = {}
    for st in STATES:
        ser = {m: _series(v, "L1", st, suites, path, pk) for m, pk in L1_PQ.items()}
        leak = _series(v, "L1", st, suites, path, "leak")
        lat = _series(v, "L1", st, suites, path, "latency_ms")
        if leak is None:
            cell["values"][st] = None
            continue
        series[st] = ser
        vals = {m: mean(s.values()) for m, s in ser.items()}
        vals.update({"n": len(ser["mrr_5"]), "adv_n": len(leak), "adv_leak": int(sum(leak.values())),
                     "latency_p50_ms": pct(lat.values(), 50)})
        cell["values"][st] = vals
    if "A" in series and "B" in series:
        for m in L1_PQ:
            cell["delta_BA"][m] = _boot(series["A"][m], series["B"][m]) if series["A"][m] else None
        for m, pk in (("mrr_5", "rr"), ("ndcg_5", "ndcg5")):      # secondary: answerable queries only
            cell["delta_BA_nonadv"][m] = _boot(_series(v, "L1", "A", suites, path, pk, only=nonadv_qids),
                                               _series(v, "L1", "B", suites, path, pk, only=nonadv_qids))
        for m in ("hit_1", "hit_5"):
            cell["mcnemar_BA"][m] = _mcn(series["A"][m], series["B"][m])
        la, lb = cell["values"]["A"]["latency_p50_ms"], cell["values"]["B"]["latency_p50_ms"]
        cell["latency_ratio_BA"] = (lb / la) if la else None
    rb = [complete_run(v, "L1", "B", s, path) for s in suites]
    rc = [complete_run(v, "L1", "C", s, path) for s in suites]
    if all(rb) and all(rc) and all(set(r.rank.get(path, {})) == suite_qids(s)
                                   for s, b_run, c_run in zip(suites, rb, rc) for r in (b_run, c_run)):
        n = same = 0
        diff = []
        for s, b, c in zip(suites, rb, rc):
            for qid, rk in b.rank[path].items():
                n += 1
                if c.rank[path].get(qid) == rk:
                    same += 1
                else:
                    diff.append(f"{s}|{qid}")
        cell["ranking_CB"] = {"identical": same, "n": n, "differing": diff[:50]}
    return cell


def l2_cell(v: Verifier, suites, path) -> dict:
    prim = primary_of(suites[0])
    cell = {"primary": prim, "values": {}, "mcnemar_CB": None, "delta_CB_primary": None, "delta_CB_gpc": None,
            "delta_CB_goldtext": None, "chars_ratio_CB": None, "adv_chars_ratio_CB": None, "adv_chars_diff_CB": None,
            "latency_diff_CB": None, "multi_match_C": None}
    series = {}
    for st in STATES:
        ser = {k: _series(v, "L2", st, suites, path, k) for k in
               dict.fromkeys((prim, "goldtext", "gpc", "goldshare", "chars", "leak", "latency_ms"))}
        if ser["chars"] is None:
            cell["values"][st] = None
            continue
        series[st] = ser
        adv_chars = [ser["chars"][k] for k in ser["leak"]]
        cell["values"][st] = {
            "primary": mean(ser[prim].values()), "primary_n": len(ser[prim]),
            "goldtext": mean(ser["goldtext"].values()),
            "gpc": mean(ser["gpc"].values()) if prim == "gpv" else None,
            "goldshare": mean(ser["goldshare"].values()),
            "chars_mean": mean(ser["chars"].values()), "chars_p95": pct(ser["chars"].values(), 95),
            "adv_chars_mean": mean(adv_chars), "adv_n": len(adv_chars),
            "adv_leak": int(sum(ser["leak"].values())),
            "latency_p50_ms": pct(ser["latency_ms"].values(), 50), "n": len(ser["chars"])}
    if "B" in series and "C" in series:
        b, c = series["B"], series["C"]
        cell["delta_CB_primary"] = _boot(b[prim], c[prim])
        cell["delta_CB_goldtext"] = _boot(b["goldtext"], c["goldtext"])
        if prim in ("gpv", "support_visible"):
            cell["mcnemar_CB"] = _mcn(b[prim], c[prim])
        if prim == "gpv":
            cell["delta_CB_gpc"] = _boot(b["gpc"], c["gpc"])
        vb, vc = cell["values"]["B"], cell["values"]["C"]
        cell["chars_ratio_CB"] = (vc["chars_mean"] / vb["chars_mean"]) if vb["chars_mean"] else None
        if vb["adv_chars_mean"] is not None and vc["adv_chars_mean"] is not None:
            cell["adv_chars_ratio_CB"] = (vc["adv_chars_mean"] / vb["adv_chars_mean"]) if vb["adv_chars_mean"] else None
            cell["adv_chars_diff_CB"] = vc["adv_chars_mean"] - vb["adv_chars_mean"]
        if vb["latency_p50_ms"] is not None and vc["latency_p50_ms"] is not None:
            cell["latency_diff_CB"] = vc["latency_p50_ms"] - vb["latency_p50_ms"]
    runs = [complete_run(v, "L1", "C", s, path) for s in suites]
    if all(runs):
        k = sum(r.mm.get(path, (0, 0))[0] for r in runs)
        t = sum(r.mm.get(path, (0, 0))[1] for r in runs)
        cell["multi_match_C"] = {"share": (k / t) if t else None, "multi": k, "results": t}
    return cell


def info_cell(v: Verifier, stem: str, refs: tuple, suite: str, path: str) -> dict:
    """Informational row: its values, the reference states' primary values, and the paired change vs refs[0]."""
    prim = primary_of(suite)
    r = v.runs.get(("L2", stem))
    cell = {"primary": prim, "value": None, "refs": {}, "delta_ref": refs[0], "delta": None, "mcnemar": None}
    if r is None or not r.ok or path not in r.pq or set(r.pq[path]) != suite_qids(suite):
        return cell
    ser = {k: {q: rec[k] for q, rec in r.pq[path].items() if rec.get(k) is not None}
           for k in (prim, "goldshare", "chars", "leak", "latency_ms")}
    adv_chars = [ser["chars"][q] for q in ser["leak"]]
    cell["value"] = {"primary": mean(ser[prim].values()), "primary_n": len(ser[prim]),
                     "goldshare": mean(ser["goldshare"].values()), "chars_mean": mean(ser["chars"].values()),
                     "chars_p95": pct(ser["chars"].values(), 95), "adv_chars_mean": mean(adv_chars),
                     "latency_p50_ms": pct(ser["latency_ms"].values(), 50), "n": len(ser["chars"])}
    for i, st in enumerate(refs):
        ref = complete_run(v, "L2", st, suite, path)
        if ref is None:
            cell["refs"][st] = None
            continue
        rser = {q: rec[prim] for q, rec in ref.pq[path].items() if rec.get(prim) is not None}
        cell["refs"][st] = mean(rser.values())
        if i == 0:
            cell["delta"] = _boot(rser, ser[prim])
            if prim != "goldtext":
                cell["mcnemar"] = _mcn(rser, ser[prim])
    return cell


def _st(ok: bool) -> str:
    return "pass" if ok else "fail"


def _num(x, nd=3, sign=False):
    if x is None:
        return "n/a"
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    if float(s) == 0:
        s = s.replace("-", "+" if sign else "")
    return s


def _ci(d, nd=3):
    if not d:
        return "n/a"
    return f"{_num(d['diff'], nd, True)} [{_num(d['lo'], nd, True)}, {_num(d['hi'], nd, True)}]"


RQ1_IDS = ["C-01", "C-02", "C-03", "C-04", "C-05", "C-06"]
RQ2_IDS = ["C-07", "C-08", "C-09", "C-10", "C-11", "C-12", "C-13", "C-14", "C-15"]


def build_summary(v: Verifier, judges: Judges, ci: dict, vstatus: dict | None = None) -> dict:
    s = {"l1": {}, "l2": {}, "l2_info": {}, "l3": {}, "criteria": {}, "decisions": {}, "rq3": {}}
    for suite in SUITES:
        s["l1"][suite] = {p: l1_cell(v, (suite,), p) for p in PATHS}
        s["l2"][suite] = {p: l2_cell(v, (suite,), p) for p in PATHS}
    s["l1"]["CD-pooled"] = {p: l1_cell(v, CD_SUITES, p) for p in PATHS}
    s["l2"]["CD-pooled"] = {p: l2_cell(v, CD_SUITES, p) for p in PATHS}
    # A empty graph vs A (the graph fix); B at 500 chars vs A (stitching and anchoring at A's budget), B shown too.
    for stem, refs in (("info_A_emptygraph_CEN", ("A",)), ("info_A_emptygraph_MH", ("A",)),
                       ("info_B_500_CEN", ("A", "B")), ("info_B_500_MH", ("A", "B"))):
        suite = stem.rsplit("_", 1)[1]
        s["l2_info"][stem] = {p: info_cell(v, stem, refs, suite, p) for p in PATHS}
    for r in INFO_RUNS:     # a round file's extra informational runs, compared with its refs (paired: refs[0])
        for suite in r["suites"]:
            stem = f"info_{r['state']}_{r['result_chars']}_{suite}"
            s["l2_info"][stem] = {p: info_cell(v, stem, tuple(r["refs"]), suite, p) for p in PATHS}
    # Layer 3.
    for pack, res in judges.packs.items():
        entry = {"status": res["status"], "complete": res.get("complete", False), "counts": res.get("counts"),
                 "kappa": res.get("kappa"), "kappa_by_state": res.get("kappa_by_state"), "vs_B": {}}
        by = res.get("by_state")
        if by and "B" in by:
            for st in JUDGE_PACKS[pack]["states"]:
                if st == "B":
                    continue
                common = [q for q in by["B"] if q in by[st]]
                pairs = [(by["B"][q] == "full", by[st][q] == "full") for q in common]
                m = mcnemar(pairs) if pairs else None
                entry["vs_B"][st] = {"net": (sum(1 for q in by[st] if by[st][q] == "full") -
                                             sum(1 for q in by["B"] if by["B"][q] == "full")),
                                     "b_full_to_not": m["b"] if m else None, "mcnemar": m, "n_pairs": len(pairs)}
        s["l3"][pack] = entry
    s["verification_status"] = dict(vstatus or {})
    s["criteria"] = criteria(v, s, ci)
    if judges.j1d is not None:      # R2-3, informational: C-11 with the discordant queries re-judged
        j = {k: val for k, val in judges.j1d.items()}
        p = (j.get("mcnemar") or {}).get("p")
        fam = {cid: ((s["criteria"][cid].get("mcnemar") or {}).get("p") if cid != "C-11" else p)
               for cid in ("C-08", "C-09", "C-11")}
        j["holm_p"] = holm({k: (1.0 if x is None else x) for k, x in fam.items()})["C-11"] if p is not None else None
        s["l3_sensitivity"] = {"J1D": j}
    outcome = {"RQ1": worst_crit(s["criteria"], RQ1_IDS, extra=[s["criteria"]["C-14"]["parts"]["B"]]),
               "RQ2": worst_crit(s["criteria"], RQ2_IDS)}
    unverified = [k for k in VERIFY_GATE if s["verification_status"].get(k) != "pass"]
    s["decisions"] = {rq: ("pending" if unverified else st) for rq, st in outcome.items()}
    s["decisions"]["criteria_outcome"] = outcome
    s["decisions"]["not_verified"] = unverified
    s["rq3"] = rq3(s)
    return s


def worst_crit(crit: dict, ids: list, extra=()) -> str:
    return worst([crit[i]["status"] for i in ids] + list(extra))


def _need(*cells) -> bool:
    return all(c is not None for c in cells)


def criteria(v: Verifier, s: dict, ci: dict) -> dict:
    C = {}

    def put(cid, parts, result, extra=None):
        st = worst(p for p in parts) if parts else "missing"
        C[cid] = {"status": st, "result": result, **(extra or {})}

    # C-01 non-inferiority of MRR@5 and nDCG@5 on CEN.
    parts, txt = [], []
    for m in ("mrr_5", "ndcg_5"):
        seg = []
        for p in PATHS:
            d = s["l1"]["CEN"][p]["delta_BA"].get(m)
            parts.append("missing" if d is None else _st(d["lo"] > -DELTA))
            seg.append(f"{p} {_ci(d)}")
        txt.append(f"{'MRR@5' if m == 'mrr_5' else 'nDCG@5'} Δ(B−A): " + ", ".join(seg))

    def secondary(suite, metrics):
        # Not a decision input: the same margin applied to answerable (non-adversarial) queries only.
        out = {}
        for m in metrics:
            for p in PATHS:
                d = s["l1"][suite][p]["delta_BA_nonadv"].get(m)
                out[f"{m} {p}"] = None if d is None else dict(d, lower_bound_above_minus_delta=d["lo"] > -DELTA)
        return out

    put("C-01", parts, "; ".join(txt) + f"; pass if lower bound > -{DELTA}",
        {"secondary_nonadversarial": secondary("CEN", ("mrr_5", "ndcg_5"))})
    # C-02 pooled CD MRR@5 plus per-suite drop.
    parts, seg, drops = [], [], []
    for p in PATHS:
        d = s["l1"]["CD-pooled"][p]["delta_BA"].get("mrr_5")
        parts.append("missing" if d is None else _st(d["lo"] > -DELTA))
        seg.append(f"{p} {_ci(d)}")
        for su in CD_SUITES:
            ds = s["l1"][su][p]["delta_BA"].get("mrr_5")
            if ds is None:
                parts.append("missing")
                continue
            parts.append(_st(ds["diff"] >= -0.03))
            drops.append((ds["diff"], su, p))
    wd = min(drops) if drops else None
    put("C-02", parts, "pooled MRR@5 Δ(B−A): " + ", ".join(seg) +
        (f"; largest per-suite drop {_num(wd[0], 3, True)} ({wd[1]} {wd[2]}), limit -0.03" if wd else "; per-suite: n/a"),
        {"secondary_nonadversarial": secondary("CD-pooled", ("mrr_5",))})
    # C-03 BEIR nDCG@10.
    parts, seg = [], []
    for su in BEIR_SUITES:
        for p in ("hybrid", "precise"):
            d = s["l1"][su][p]["delta_BA"].get("ndcg_10")
            parts.append("missing" if d is None else _st(d["lo"] > -DELTA))
            seg.append(f"{su} {p} {_ci(d)}")
    put("C-03", parts, "nDCG@10 Δ(B−A): " + ", ".join(seg))
    # C-04 graded nDCG@5 on CEN-G.
    parts, seg = [], []
    for p in PATHS:
        d = s["l1"]["CEN-G"][p]["delta_BA"].get("graded_ndcg_5")
        parts.append("missing" if d is None else _st(d["lo"] > -DELTA))
        seg.append(f"{p} {_ci(d)}")
    put("C-04", parts, "graded nDCG@5 Δ(B−A): " + ", ".join(seg))
    # C-05 adversarial leaks.
    parts, seg, cases = [], [], []
    for su in ("CEN",) + CD_SUITES:
        for p in PATHS:
            va, vb = s["l1"][su][p]["values"].get("A"), s["l1"][su][p]["values"].get("B")
            if not _need(va, vb):
                parts.append("missing")
                continue
            ok = vb["adv_leak"] <= va["adv_leak"] + 2
            parts.append(_st(ok))
            cases.append({"suite": su, "path": p, "A": va["adv_leak"], "B": vb["adv_leak"], "status": _st(ok)})
            if not ok:
                seg.append(f"{su} {p}: A {va['adv_leak']}, B {vb['adv_leak']}")
    worst_c = max(cases, key=lambda c: c["B"] - c["A"]) if cases else None
    put("C-05", parts, ("violations: " + "; ".join(seg)) if seg else
        (f"B ≤ A + 2 in every CEN/CD suite and path; largest B − A {worst_c['B'] - worst_c['A']:+d} "
         f"({worst_c['suite']} {worst_c['path']})" if "missing" not in parts and worst_c else "incomplete"),
        {"cases": cases})
    # C-06 CEN latency ratio.
    parts, seg = [], []
    for p in PATHS:
        r = s["l1"]["CEN"][p]["latency_ratio_BA"]
        parts.append("missing" if r is None else _st(r <= 1.10))
        seg.append(f"{p} {_num(r)}")
    put("C-06", parts, "L1 p50 B/A: " + ", ".join(seg) + "; limit 1.10")
    # C-07 ranking identity.
    parts, bad, tot, miss = [], [], 0, []
    for su in SUITES:
        for p in PATHS:
            rk = s["l1"][su][p]["ranking_CB"]
            if rk is None:
                parts.append("missing")
                miss.append(f"{su} {p}")
                continue
            tot += rk["n"]
            parts.append(_st(rk["identical"] == rk["n"]))
            if rk["identical"] != rk["n"]:
                bad.append(f"{su} {p}: {rk['n'] - rk['identical']}")
    txt = ("differing queries: " + "; ".join(bad)) if bad else f"0 differing of {tot} query-path pairs compared"
    if miss:
        txt += f"; not computable (B or C run missing or incomplete): {', '.join(miss[:6])}" + (" …" if len(miss) > 6 else "")
    put("C-07", parts, txt)
    # C-08, C-09, C-11 superiority endpoints with Holm.
    pvals, endpoint = {}, {}
    for cid, su in (("C-08", "CEN-G"), ("C-09", "MH")):
        m = s["l2"][su]["hybrid"]["mcnemar_CB"]
        endpoint[cid] = m
        if m is not None:
            pvals[cid] = m["p"]
    l3 = s["l3"].get("J1", {})
    j_complete = bool(l3.get("complete"))
    j_cb = (l3.get("vs_B") or {}).get("C") if j_complete else None
    endpoint["C-11"] = j_cb["mcnemar"] if j_cb else None
    if endpoint["C-11"] is not None:
        pvals["C-11"] = endpoint["C-11"]["p"]
    # A missing endpoint enters Holm as p = 1 (conservative); superiority is claimed only with all three present.
    holm_complete = all(k in pvals for k in ("C-08", "C-09", "C-11"))
    full_p = {k: pvals.get(k, 1.0) for k in ("C-08", "C-09", "C-11")}
    adj = holm(full_p)
    for cid, name in (("C-08", "GPV CEN-G hybrid"), ("C-09", "SupportVisible MH hybrid")):
        m = endpoint[cid]
        if m is None:
            put(cid, ["missing"], f"{name}: missing")
            continue
        sup = holm_complete and adj[cid] < 0.05 and m["c"] > m["b"]
        put(cid, [_st(m["c"] - m["b"] >= 0)],
            f"{name}: b={m['b']}, c={m['c']}, net {m['c'] - m['b']:+d}, n={m['n']}, p={_num(m['p'], 4)}, "
            f"Holm p={_num(adj[cid], 4)}{'' if holm_complete else ' (Holm family incomplete)'}; "
            f"superiority {'claimed' if sup else 'not claimed'}",
            {"holm_p": adj[cid], "holm_complete": holm_complete, "superiority": sup, "mcnemar": m})
    # C-10 per suite and path.
    parts, bad, cases = [], [], []
    for su in SUITES:
        for p in PATHS:
            cell = s["l2"][su][p]
            if cell["primary"] == "goldtext":
                d = cell["delta_CB_primary"]
                if d is None:
                    parts.append("missing")
                    continue
                ok = not (d["hi"] < 0)
                cases.append({"suite": su, "path": p, "metric": "GoldText", "diff": d["diff"], "lo": d["lo"],
                              "hi": d["hi"], "status": _st(ok)})
                if not ok:
                    bad.append(f"{su} {p} GoldText {_ci(d, 2)}")
            else:
                m = cell["mcnemar_CB"]
                if m is None:
                    parts.append("missing")
                    continue
                ok = (m["b"] - m["c"]) <= 1
                cases.append({"suite": su, "path": p, "metric": PRIMARY_LABEL[cell["primary"]], "b": m["b"],
                              "c": m["c"], "p": m["p"], "status": _st(ok)})
                if not ok:
                    bad.append(f"{su} {p} {PRIMARY_LABEL[cell['primary']]} b={m['b']} c={m['c']}")
            parts.append(_st(ok))
    gt = [c for c in cases if c["metric"] == "GoldText"]
    bn = [c for c in cases if c["metric"] != "GoldText"]
    if bad:
        txt = "failing: " + "; ".join(bad)
    elif "missing" in parts or not cases:
        txt = "incomplete"
    else:
        txt = "no suite/path fails"
        if bn:
            w = max(bn, key=lambda c: c["b"] - c["c"])
            txt += f"; largest binary net loss b−c {w['b'] - w['c']:+d} ({w['suite']} {w['path']})"
        if gt:
            w = min(gt, key=lambda c: c["hi"])
            txt += f"; smallest GoldText upper bound {_num(w['hi'], 2, True)} ({w['suite']} {w['path']})"
    put("C-10", parts, txt, {"cases": cases})
    # C-11 judges.
    kap_rec = (l3.get("kappa") or {}) if l3 else {}
    kap = kap_rec.get("kappa")
    if not j_cb:
        put("C-11", ["missing"], f"J1 judgements missing or incomplete (each of the {CEN_A_N} CEN-A queries, "
                                 f"{', '.join(CEN_A_EXCLUDED)} excluded, must be judged once for each state)")
    else:
        m = j_cb["mcnemar"] or {"b": 0, "c": 0, "p": 1.0, "n": 0}
        ok_net, ok_b = j_cb["net"] >= 0, (j_cb["b_full_to_not"] or 0) <= 1
        ok_k = kap is not None and kap >= 0.6
        sup = holm_complete and adj["C-11"] < 0.05 and m["c"] > m["b"] and ok_k
        kstat = "missing" if not kap_rec.get("complete") else _st(ok_k)   # re-judge incomplete -> missing
        put("C-11", [_st(ok_net and ok_b), kstat],
            f"net C−B full {j_cb['net']:+d}; B-full→C-not-full {j_cb['b_full_to_not']}; b={m['b']}, c={m['c']}, "
            f"p={_num(m['p'], 4)}, Holm p={_num(adj['C-11'], 4)}; κ={_num(kap)} (n={kap_rec.get('n')})"
            + ("" if ok_k else " (below 0.6: judge criteria unconfirmed)")
            + f"; superiority {'claimed' if sup else 'not claimed'}",
            {"holm_p": adj["C-11"], "holm_complete": holm_complete, "superiority": sup, "kappa": kap})
    # C-12 output size.
    parts, bad, cases = [], [], []
    for su in SUITES:
        for p in PATHS:
            cell = s["l2"][su][p]
            r = cell["chars_ratio_CB"]
            if r is None:
                parts.append("missing")
                continue
            parts.append(_st(r <= 1.5))
            case = {"suite": su, "path": p, "ratio": r, "status": _st(r <= 1.5)}
            if r > 1.5:
                bad.append(f"{su} {p} C/B {_num(r)}")
            if su in ADV_SUITES:
                ar, ad = cell["adv_chars_ratio_CB"], cell["adv_chars_diff_CB"]
                if ad is None:
                    parts.append("missing")
                    cases.append(case)
                    continue
                ok = (ar is not None and ar <= 1.5) or ad <= 100
                parts.append(_st(ok))
                case.update(adv_ratio=ar, adv_diff=ad, adv_status=_st(ok))
                if not ok:
                    bad.append(f"{su} {p} adversarial C/B {_num(ar)}, C−B {_num(ad, 1)}")
            cases.append(case)
    if bad:
        txt = "failing: " + "; ".join(bad)
    elif "missing" in parts or not cases:
        txt = "incomplete"
    else:
        w = max(cases, key=lambda c: c["ratio"])
        txt = f"max mean-chars ratio C/B {_num(w['ratio'])} ({w['suite']} {w['path']})"
        adv = [c for c in cases if "adv_diff" in c]
        if adv:
            wa = max(adv, key=lambda c: c["adv_diff"])
            txt += (f"; adversarial rule holds everywhere, largest C−B {_num(wa['adv_diff'], 0, True)} chars "
                    f"(C/B {_num(wa['adv_ratio'])}, {wa['suite']} {wa['path']})")
    put("C-12", parts, txt, {"cases": cases})
    # C-13 latency.
    parts, bad, cases = [], [], []
    for su in SUITES:
        for p in PATHS:
            cell = s["l2"][su][p]
            vb = cell["values"].get("B")
            d = cell["latency_diff_CB"]
            if vb is None or d is None:
                parts.append("missing")
                continue
            tol = max(0.05 * vb["latency_p50_ms"], 15.0)
            ok = abs(d) <= tol
            parts.append(_st(ok))
            cases.append({"suite": su, "path": p, "diff_ms": d, "limit_ms": tol, "status": _st(ok)})
            if not ok:
                bad.append(f"{su} {p} C−B {_num(d, 1, True)} ms (limit ±{_num(tol, 1)})")
    if bad:
        txt = "failing: " + "; ".join(bad)
    elif "missing" in parts or not cases:
        txt = "incomplete"
    else:
        w = max(cases, key=lambda c: abs(c["diff_ms"]) / c["limit_ms"])
        txt = (f"abs(C−B) ≤ max(5% of B, 15 ms) everywhere; closest {_num(w['diff_ms'], 1, True)} ms "
               f"of ±{_num(w['limit_ms'], 1)} ({w['suite']} {w['path']})")
    put("C-13", parts, txt, {"cases": cases})
    # C-14 CI gates.
    pb = worst([ci["tests_B"]["status"], ci["compare_B"]["status"]])
    pc = worst([ci["tests_C"]["status"], ci["compare_C"]["status"]])
    C["C-14"] = {"status": worst([pb, pc]), "parts": {"B": pb, "C": pc},
                 "result": f"pytest -m \"{CI_MARK}\" on MPS: B {ci['tests_B']['status']}, C {ci['tests_C']['status']}; "
                           f"compare_benchmarks.py rule vs A's MPS run ({', '.join(CI_PATHS)}): "
                           f"B {_cmp_txt(ci['compare_B'])}, C {_cmp_txt(ci['compare_C'])} "
                           f"(A's baseline run: {ci['baseline_A']['status']}, exit {ci['baseline_A'].get('exit_code')}); "
                           + _info_txt(ci) +
                           f"vs archive (information): B {(ci.get('archive_B') or {}).get('red')} red, "
                           f"C {(ci.get('archive_C') or {}).get('red')} red",
                 "evidence": ci}
    # C-15 kill switch.
    v04 = getattr(v, "v04", None)
    if v04 is None:
        put("C-15", ["missing"], "L2-C0 or L2-B-CEN missing")
    else:
        put("C-15", [_st(v04["differing"] == 0 and v04["compared"] == EXPECTED_N["CEN"] * len(PATHS))],
            f"{v04['compared'] - v04['differing']} of {v04['compared']} outputs byte-identical")
    return C


def rq3(s: dict) -> dict:
    """Spearman correlation of C's multi-match share with the C - B change, per path.

    "registered": the primary visibility metric of each suite (section 9: GPV for CEN-G, SupportVisible for MH,
    GoldText elsewhere). "goldtext": GoldText for every suite, one unit throughout (secondary, not pre-registered).
    """
    out = {"path": "hybrid", "rows": [], "spearman": None, "spearman_by_path": {},
           "goldtext": {"rows": [], "spearman": None, "spearman_by_path": {}}}
    for path in PATHS:
        reg, gt = ([], [], []), ([], [], [])
        for su in SUITES:
            cell = s["l2"][su][path]
            mm = cell["multi_match_C"]
            x = mm["share"] if mm else None
            d, g = cell["delta_CB_primary"], cell["delta_CB_goldtext"]
            for (xs, ys, rows), dd, metric in ((reg, d, PRIMARY_LABEL[cell["primary"]]), (gt, g, "GoldText")):
                y = dd["diff"] if dd else None
                rows.append({"suite": su, "multi_match": x, "delta": y, "metric": metric})
                if x is not None and y is not None:
                    xs.append(x)
                    ys.append(y)
        for key, (xs, ys, rows) in (("registered", reg), ("goldtext", gt)):
            rho, pv = spearman(xs, ys)
            sp = {"rho": rho, "p": pv, "n": len(xs)}
            target = out if key == "registered" else out["goldtext"]
            target["spearman_by_path"][path] = sp
            if path == "hybrid":
                target["rows"], target["spearman"] = rows, sp
    return out


# ── Rendering section 15 ────────────────────────────────────────────

SEC15_HEAD = "## 15. Results (filled from `summary.json` after V-ALL passes)"
H151 = "### 15.1 Layer 1 — retrieval (values: A / B / C; Δ(B−A) with 95% CI)"
H152 = "### 15.2 Layer 2 — agent-visible (values: A / B / C; McNemar b, c, p for C vs B)"
H153 = "### 15.3 Layer 3 — judges"
H154 = "### 15.4 Criteria outcome"
H155 = "### 15.5 RQ3 — generality"

CRIT_EVIDENCE = {"C-01": "L1-A-CEN, L1-B-CEN", "C-02": "L1-A/B-CD-*", "C-03": "L1-A/B-BEIR-*", "C-04": "L1-A/B-CEN-G",
                 "C-05": "L1-A/B-CEN, CD-*", "C-06": "L1-A/B-CEN", "C-07": "L1-B/C-*", "C-08": "L2-B/C-CEN-G",
                 "C-09": "L2-B/C-MH", "C-10": "L2-B/C-*", "C-11": "J1, J1-R", "C-12": "L2-B/C-*", "C-13": "L2-B/C-*",
                 "C-14": "CI-B, CI-C", "C-15": "L2-C0, L2-B-CEN"}
CRIT_VIDS = {"C-01": ("V-01", "V-02", "V-03", "V-05"), "C-02": ("V-02", "V-03", "V-05"),
             "C-03": ("V-02", "V-03", "V-05"), "C-04": ("V-02", "V-03", "V-05"), "C-05": ("V-02", "V-03", "V-05"),
             "C-06": ("V-01", "V-02", "V-03", "V-05"), "C-07": ("V-02", "V-03", "V-05"),
             "C-08": ("V-02", "V-03", "V-05", "V-07"), "C-09": ("V-02", "V-03", "V-05", "V-07"),
             "C-10": ("V-02", "V-03", "V-05", "V-07"), "C-11": ("V-06",), "C-12": ("V-02", "V-03", "V-05"),
             "C-13": ("V-02", "V-03", "V-05"), "C-14": (), "C-15": ("V-02", "V-04")}
STATUS_WORD = {"pass": "Pass", "fail": "Fail", "missing": "Missing", "pending": "Pending", "not_run": "Not run"}


def _abc(values: dict, key: str, nd=3, states=STATES) -> str:
    out = []
    for st in states:
        val = values.get(st)
        out.append("missing" if val is None else _num(val.get(key), nd))
    return " / ".join(out)


def _l1_metric(cell: dict, key: str, label: str = "") -> str:
    base = _abc(cell["values"], key)
    d = cell["delta_BA"].get(key)
    return f"{label}{base}" + (f"; Δ {_ci(d)}" if d else "")


def render_section15(s: dict) -> str:
    L = [SEC15_HEAD, "", H151, "",
         "| Suite | Path | MRR@5 | nDCG@5 | Hit@1 | Hit@5 | P@5 | Graded nDCG@5 | Adv. leak | Latency p50 (ms) | Ranking identical C=B | Source JSON |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def rk(cell):
        r = cell["ranking_CB"]
        return "missing" if r is None else f"{r['identical']}/{r['n']}"

    def leak(cell):
        vals = cell["values"]
        out = []
        for st in STATES:
            val = vals.get(st)
            out.append("missing" if val is None else str(val["adv_leak"]))
        n = next((vals[st]["adv_n"] for st in STATES if vals.get(st)), None)
        return " / ".join(out) + (f" (of {n})" if n is not None else "")

    def lat(cell):
        base = _abc(cell["values"], "latency_p50_ms", 1)
        r = cell.get("latency_ratio_BA")
        return base + (f"; B/A {_num(r)}" if r is not None else "")

    def src(i, text):
        return f"`{text}`" if i == 0 else "″"

    l1 = s["l1"]
    for i, p in enumerate(PATHS):
        c = l1["CEN"][p]
        L.append(f"| CEN | {p} | {_l1_metric(c, 'mrr_5')} | {_l1_metric(c, 'ndcg_5')} | {_l1_metric(c, 'hit_1')} | "
                 f"{_l1_metric(c, 'hit_5')} | {_l1_metric(c, 'p_5')} | — | {leak(c)} | {lat(c)} | {rk(c)} | "
                 f"{src(i, 'L1/{A,B,C}_CEN.json')} |")
    for i, p in enumerate(PATHS):
        c = l1["CEN-G"][p]
        L.append(f"| CEN-G | {p} | — | — | — | — | — | {_l1_metric(c, 'graded_ndcg_5')} | — | — | {rk(c)} | "
                 f"{src(i, 'L1/{A,B,C}_CEN-G.json')} |")
    for i, p in enumerate(PATHS):
        c = l1["MH"][p]
        L.append(f"| MH | {p} | {_l1_metric(c, 'support_all_5', 'SupportAll@5: ')} | {_l1_metric(c, 'ndcg_5')} | "
                 f"{_l1_metric(c, 'hit_1')} | {_l1_metric(c, 'hit_5')} | {_l1_metric(c, 'p_5')} | — | — | {lat(c)} | "
                 f"{rk(c)} | {src(i, 'L1/{A,B,C}_MH.json')} |")
    for su in CD_SUITES + ("CD-pooled",):
        for i, p in enumerate(PATHS):
            c = l1[su][p]
            name = "CD pooled" if su == "CD-pooled" else su
            js = "L1/{A,B,C}_CD-*.json" if su == "CD-pooled" else f"L1/{{A,B,C}}_{su}.json"
            L.append(f"| {name} | {p} | {_l1_metric(c, 'mrr_5')} | {_l1_metric(c, 'ndcg_5')} | {_l1_metric(c, 'hit_1')} | "
                     f"{_l1_metric(c, 'hit_5')} | {_l1_metric(c, 'p_5')} | — | {leak(c)} | {lat(c)} | {rk(c)} | {src(i, js)} |")
    for su in BEIR_SUITES:
        for i, p in enumerate(("hybrid", "precise")):
            c = l1[su][p]
            L.append(f"| {su} | {p} | {_l1_metric(c, 'ndcg_10', 'nDCG@10: ')} | {_l1_metric(c, 'recall_10', 'Recall@10: ')} | "
                     f"{_l1_metric(c, 'hit_1')} | {_l1_metric(c, 'hit_5')} | {_l1_metric(c, 'p_5')} | — | — | {lat(c)} | "
                     f"{rk(c)} | {src(i, f'L1/{{A,B,C}}_{su}.json')} |")

    L += ["", H152, "",
          "| Suite | Path | Primary visibility (GPV / SupportVisible / GoldText) | GPC | GoldShare | Chars/q mean (p95) | Adv. chars/q | Latency p50 | Multi-match freq. | Source JSON |",
          "|---|---|---|---|---|---|---|---|---|---|"]

    def prim(cell):
        label = PRIMARY_LABEL[cell["primary"]]
        nd = 2 if cell["primary"] == "goldtext" else 3
        base = f"{label} {_abc(cell['values'], 'primary', nd)}"
        n = next((cell["values"][st]["primary_n"] for st in STATES if cell["values"].get(st)), None)
        if cell["primary"] != "goldtext" and n is not None:
            base += f" (n={n})"
        m = cell["mcnemar_CB"]
        if m is not None:
            base += f"; b={m['b']}, c={m['c']}, p={_num(m['p'], 4)}"
        elif cell["primary"] == "goldtext" and cell["delta_CB_primary"]:
            base += f"; Δ(C−B) {_ci(cell['delta_CB_primary'], 2)}"
        return base

    def gpc(cell):
        if cell["primary"] != "gpv":
            return "—"
        base = _abc(cell["values"], "gpc")
        return base + (f"; Δ(C−B) {_ci(cell['delta_CB_gpc'])}" if cell["delta_CB_gpc"] else "")

    def chars(cell):
        out = []
        for st in STATES:
            val = cell["values"].get(st)
            out.append("missing" if val is None else f"{_num(val['chars_mean'], 0)} ({_num(val['chars_p95'], 0)})")
        r = cell["chars_ratio_CB"]
        return " / ".join(out) + (f"; C/B {_num(r)}" if r is not None else "")

    def adv(cell, show):
        if not show:
            return "—"
        base = _abc(cell["values"], "adv_chars_mean", 0)
        r, d = cell["adv_chars_ratio_CB"], cell["adv_chars_diff_CB"]
        if d is not None:
            base += f"; C/B {_num(r)}, C−B {_num(d, 0, True)}"
        return base

    def lat2(cell):
        base = _abc(cell["values"], "latency_p50_ms", 1)
        d = cell["latency_diff_CB"]
        return base + (f"; C−B {_num(d, 1, True)}" if d is not None else "")

    def mm(cell):
        m = cell["multi_match_C"]
        return "missing" if m is None else f"{_num(m['share'])} ({m['multi']}/{m['results']})"

    l2 = s["l2"]
    order = [("CEN-G", PATHS, True, True), ("MH", PATHS, False, False), ("CEN", PATHS, False, True)]
    order += [(su, PATHS, False, True) for su in CD_SUITES + ("CD-pooled",)]
    order += [(su, ("hybrid", "precise"), False, False) for su in BEIR_SUITES]
    for su, paths, _g, show_adv in order:
        for i, p in enumerate(paths):
            c = l2[su][p]
            name = "CD pooled" if su == "CD-pooled" else su
            js = "L2/{A,B,C}_CD-*.json" if su == "CD-pooled" else f"L2/{{A,B,C}}_{su}.json"
            L.append(f"| {name} | {p} | {prim(c)} | {gpc(c)} | {_abc(c['values'], 'goldshare')} | {chars(c)} | "
                     f"{adv(c, show_adv)} | {lat2(c)} | {mm(c)} | {src(i, js)} |")
    first = True
    info_rows = [("info_A_emptygraph_CEN", "A empty graph, CEN"), ("info_A_emptygraph_MH", "A empty graph, MH"),
                 ("info_B_500_CEN", "B at 500 chars, CEN"), ("info_B_500_MH", "B at 500 chars, MH")]
    info_rows += [(f"info_{r['state']}_{r['result_chars']}_{su}", f"{r['state']} at {r['result_chars']:,} chars, {su}")
                  for r in INFO_RUNS for su in r["suites"]]
    for stem, label in info_rows:
        for p in PATHS:
            c = s["l2_info"][stem][p]
            val = c["value"]
            plabel = PRIMARY_LABEL[c["primary"]]
            nd = 2 if c["primary"] == "goldtext" else 3
            if val is None:
                cells = [f"{plabel} missing", "—", "missing", "missing", "—", "missing"]
            else:
                pr = f"{plabel} {_num(val['primary'], nd)}"
                if c["refs"]:
                    pr += " (" + ", ".join(f"{st}: {'missing' if x is None else _num(x, nd)}" for st, x in c["refs"].items()) + ")"
                if c["mcnemar"]:
                    m = c["mcnemar"]
                    pr += f"; vs {c['delta_ref']}: b={m['b']}, c={m['c']}, p={_num(m['p'], 4)}"
                elif c["delta"]:
                    pr += f"; Δ vs {c['delta_ref']} {_ci(c['delta'], 2)}"
                cells = [pr, "—", _num(val["goldshare"]), f"{_num(val['chars_mean'], 0)} ({_num(val['chars_p95'], 0)})",
                         _num(val["adv_chars_mean"], 0) if c["primary"] == "goldtext" else "—", _num(val["latency_p50_ms"], 1)]
            L.append(f"| Informational | {label}, {p} | " + " | ".join(cells) + f" | — | {src(0 if first else 1, 'L2/info_*.json')} |")
            first = False

    L += ["", H153, "", "| Pack | State | full | partial | none | Net vs B | B-full items that are not full in this state | κ (double-judged) | Source JSON |",
          "|---|---|---|---|---|---|---|---|---|"]
    j1 = s["l3"].get("J1") or {}
    for i, st in enumerate(("A", "B", "C")):
        cnt = (j1.get("counts") or {}).get(st)
        vb = (j1.get("vs_B") or {}).get(st)
        kb = ((j1.get("kappa_by_state") or {}).get(st) or {})
        ko = j1.get("kappa") or {}
        cells = ["missing"] * 3 if cnt is None else [str(cnt["full"]), str(cnt["partial"]), str(cnt["none"])]
        if cnt is not None and not j1.get("complete"):
            cells[2] += " (incomplete)"
        net = "—" if st == "B" else ("missing" if vb is None else f"{vb['net']:+d}")
        down = "—" if st == "B" else ("missing" if vb is None else str(vb["b_full_to_not"]))
        if not ko:
            kap = "missing"
        elif not ko.get("complete"):
            kap = f"incomplete (n={ko.get('n')} of {ko.get('expected')})"
        else:
            kap = (f"pack {_num(ko.get('kappa'))} (n={ko.get('n')}, agreement {_num(ko.get('agreement'))}); "
                   f"this state {_num(kb.get('kappa'))} (n={kb.get('n')})")
        L.append(f"| J1 (hybrid) | {st} | " + " | ".join(cells) + f" | {net} | {down} | {kap} | "
                 f"{src(i, 'judges/out_J1_*.json')} |")
    j2 = s["l3"].get("J2") or {}
    if j2.get("status") == "not_run" or not j2.get("counts"):
        word = "not run" if j2.get("status") == "not_run" else "missing"
        L.append(f"| J2 (precise, opt.) | B / C | {word} | {word} | {word} | {word} | {word} | {word} | `judges/out_J2_*.json` |")
    else:
        cb, cc = j2["counts"]["B"], j2["counts"]["C"]
        vb = (j2.get("vs_B") or {}).get("C") or {}
        k = j2.get("kappa")
        ktxt = "not double-judged" if not k else (_num(k.get("kappa")) if k.get("complete") else "incomplete")
        if not j2.get("complete"):
            ktxt += "; pack incomplete"
        L.append(f"| J2 (precise, opt.) | B / C | {cb['full']} / {cc['full']} | {cb['partial']} / {cc['partial']} | "
                 f"{cb['none']} / {cc['none']} | {vb.get('net', 0):+d} | {vb.get('b_full_to_not')} | {ktxt} | `judges/out_J2_*.json` |")

    L += ["", H154, "", "| ID | Result (value, CI or p) | Pass / Fail | Evidence (run IDs → JSON) | Verified (V-ids) |",
          "|---|---|---|---|---|"]
    vstat = s.get("verification_status", {})
    for cid in sorted(s["criteria"]):
        c = s["criteria"][cid]
        vids = ", ".join(f"{x} {vstat.get(x, 'missing')}" for x in CRIT_VIDS[cid]) or "—"
        result = str(c["result"]).replace("|", "\\|")
        L.append(f"| {cid} | {result} | {STATUS_WORD.get(c['status'], c['status'])} | {CRIT_EVIDENCE[cid]} | {vids} |")
    sens = (s.get("l3_sensitivity") or {}).get("J1D")
    if sens is not None:
        L += ["", "R2-3 sensitivity (informational; C-11 is decided on the J1 verdicts): "
              + (f"the {len(sens['queries'] or [])} CEN-A queries whose J1 verdicts for B and C differ on full, each "
                 f"B and C item with two more judges, full when 2 of 3 verdicts say full: b={sens['b']}, c={sens['c']}, "
                 f"net {sens['c'] - sens['b']:+d}, p={_num(sens['mcnemar']['p'], 4)}, Holm p={_num(sens['holm_p'], 4)} "
                 f"(`judges/out_J1D_*.json`)." if sens["status"] == "ok" else f"{sens['status']} (V-06).")]
    dec = s["decisions"]
    out_c = dec.get("criteria_outcome") or {}
    nv = dec.get("not_verified") or []

    def word(x):
        return STATUS_WORD.get(x, x)

    L += ["", f"Decisions: RQ1 {word(dec['RQ1'])} (C-01 to C-06 and C-14 for B; criteria {word(out_c.get('RQ1'))}); "
              f"RQ2 {word(dec['RQ2'])} (C-07 to C-15; criteria {word(out_c.get('RQ2'))})."
          + (f" Not reportable until {', '.join(nv)} pass." if nv else "")]

    L += ["", H155, "", "| Suite | Multi-match frequency (C) | Δ primary visibility (C − B) | Notes |", "|---|---|---|---|"]
    gt_rows = {r["suite"]: r for r in (s["rq3"].get("goldtext") or {}).get("rows", [])}
    for row in s["rq3"]["rows"]:
        nd = 2 if row["metric"] == "GoldText" else 3
        note = f"hybrid; {row['metric']}"
        g = gt_rows.get(row["suite"])
        if row["metric"] != "GoldText" and g is not None:
            note += f"; GoldText Δ {_num(g['delta'], 2, True) if g['delta'] is not None else 'missing'}"
        L.append(f"| {row['suite']} | {_num(row['multi_match']) if row['multi_match'] is not None else 'missing'} | "
                 f"{_num(row['delta'], nd, True) if row['delta'] is not None else 'missing'} | {note} |")

    def rho_txt(sp):
        sp = sp or {}
        return "n/a" if sp.get("rho") is None else f"{_num(sp['rho'])} (p={_num(sp['p'], 4)}, n={sp['n']})"

    L.append(f"| **Spearman ρ (p)** | {rho_txt(s['rq3']['spearman'])} | | descriptive only; registered metrics |")
    L.append(f"| Spearman ρ (p), GoldText for every suite | {rho_txt((s['rq3'].get('goldtext') or {}).get('spearman'))} | | "
             "secondary, not pre-registered: one unit across suites |")
    L += ["", "**Caveats carried with this round's outcome** (protocol §16, round 2 addendum):", "",
          "- C-11 fails on its \"at most one B-full → not-full\" clause. Both losses are single-judge variance on identical evidence: C′'s output contains all of B′'s text on every query. The R2-3 majority of three gives b = 0. C-11's outcome is the registered one; do not describe the two losses as lost content.",
          "- C-12 passes by 76.7 characters under the registered ratio-of-means (1.457 on CD-API hybrid). The non-adversarial ratio is 1.59, and per-query averaging would fail it.",
          "- C-08 sensitivity: 44 of 222 grade-2 chunks are under 150 characters. Without them, b = 0, c = 8, p = 0.0078, Holm p = 0.023; the criterion still passes.",
          "- R2-4 extends B′'s view forward only. Nine of the ten C-08 wins show text from before B′'s view start, and on CEN GoldText the longer B′ view beats C′ at equal size. It does not show that passage choice beats an equal-length view.",
          "- C-14 has no V-id: verify.py does not check the one-attempt rule or B′'s tests/ and pyproject.toml. Those were checked by hand (§16), and the hand checks pass.",
          "- J2 (informational) has two `full` verdicts that break the rubric (K0150, K0121); they are kept as recorded and decide nothing (§16).",
          "- C-05 cannot fail on hybrid or explore: A already leaks on every adversarial query there. The ranking identity (4,212 of 4,212) is the substantive evidence."]
    return "\n".join(L) + "\n"


def _trim(lines):
    lines = [l.rstrip() for l in lines]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def check_doc(doc_path: Path, rendered: str):
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"cannot read {doc_path}: {e}"
    sec = extract_section(text, "## 15.")
    if sec is None:
        return False, "section 15 not found in the protocol"
    a, b = _trim(sec.split("\n")), _trim(rendered.split("\n"))
    if a == b:
        return True, "section 15 equals the rendering of summary.json"
    diff = "\n".join(difflib.unified_diff(a, b, "protocol §15", "rendered from summary.json", lineterm="", n=0))
    return False, diff


# ── Spot-check sample (V-08) ────────────────────────────────────────

def spot_sample(v: Verifier) -> dict:
    population = [(su, q["qid"]) for su in SUITES for q in derive_queries(su)]
    rng = random.Random(SEED)
    out = {"seed": SEED, "method": "random.Random(20261018).sample over every (suite, qid) in suite order, "
                                   "10 per state, states A, B, C in turn", "states": {}}
    qmap = {(su, q["qid"]): q for su in SUITES for q in derive_queries(su)}
    for st in STATES:
        picks = rng.sample(population, 10)
        entries = []
        for su, qid in picks:
            q = qmap[(su, qid)]
            e = {"suite": su, "qid": qid, "query": q["query"], "category": q["category"],
                 "gold_sources": q["gold_sources"], "paths": {}, "notes": ""}
            for p in PATHS:
                l1, l2 = v.main("L1", st, su), v.main("L2", st, su)
                e["paths"][p] = {
                    "l1_ranking": list(l1.rank.get(p, {}).get(qid, ())) if l1 else "missing",
                    "l1_metrics": l1.pq.get(p, {}).get(qid) if l1 else "missing",
                    "l2_metrics": l2.pq.get(p, {}).get(qid) if l2 else "missing",
                    "l2_raw_output": l2.raw.get(p, {}).get(qid) if l2 else "missing"}
            entries.append(e)
        out["states"][st] = entries
    return out


# ── Rounds (--round) ────────────────────────────────────────────────

ROUND_KEYS = ("name", "results_root", "eval_home", "doc", "ports", "states", "corpus_documents", "ci_plugins",
              "info_runs")
ROUND_OPTIONAL = ("corpus_documents", "ci_plugins", "info_runs")
INFO_RUN_FIELDS = ("state", "result_chars", "suites", "refs")
SHA_RE = re.compile(r"[0-9a-fA-F]{7,40}")


def round_file(value) -> Path:
    """The file --round names: as given (relative to the working directory), else relative to
    this script's directory (rounds/r2.json). An empty value, or one that names no regular
    file, is refused: it must never mean round 1."""
    if not str(value).strip():
        raise SystemExit("--round was given an empty value; name a round file, e.g. --round rounds/r2.json")
    p = Path(value).expanduser()
    if not p.is_absolute() and not p.is_file() and (SCRIPT.parent / p).is_file():
        p = SCRIPT.parent / p
    p = p.resolve()
    if not p.is_file():
        raise SystemExit(f"--round {value}: {p} is not a file")
    return p


def round_location(value: str) -> Path:
    """A path in a round file: "~" is expanded, a relative path is relative to the repository root."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else REPO / p


def load_round(value) -> dict:
    """A round file, read as data. Exits when it has a key this verifier does not know (an
    unread value could be an expectation that differs from round 1's) or lacks or
    malforms one it uses, or when B's checkout is not this repository (B is checked
    against --repo); its ports and the venvs of A and C are not used here."""
    path = round_file(value)
    raw, err = load_json_safe(path)
    if not isinstance(raw, dict):
        raise SystemExit(f"--round {path}: {err or 'not a JSON object'}")
    probs = [f"unknown key {k!r}" for k in raw if k not in ROUND_KEYS]
    probs += [f"missing {k!r}" for k in ROUND_KEYS if k not in raw and k not in ROUND_OPTIONAL]
    probs += [f"{k} must be a non-empty string" for k in ("name", "results_root", "eval_home", "doc")
              if k in raw and not (isinstance(raw[k], str) and raw[k])]
    states = raw.get("states")
    if not (isinstance(states, dict) and set(states) == set(STATES)
            and all(isinstance(s, dict) for s in states.values())):
        probs.append(f"states must give each of {', '.join(STATES)}")
        states = {}
    for st, spec in states.items():
        probs += [f"states.{st}.{k} must be a non-empty string" for k in ("checkout", "venv", "fastmcp")
                  if not (isinstance(spec.get(k), str) and spec[k])]
        ref = spec.get("ref")
        if not (isinstance(ref, str) and SHA_RE.fullmatch(ref)):
            probs.append(f"states.{st}.ref must be a commit SHA")
    b_checkout = states.get("B", {}).get("checkout")
    if isinstance(b_checkout, str) and b_checkout and not same_dir(round_location(b_checkout), REPO):
        probs.append(f"states.B.checkout must be this repository ({REPO})")
    docs, plugins = raw.get("corpus_documents", {}), raw.get("ci_plugins", {})
    if not (isinstance(docs, dict) and all(c in INGEST_DOCS and isinstance(n, int) and not isinstance(n, bool) and n > 0
                                           for c, n in docs.items())):
        probs.append(f"corpus_documents must map ingest ids ({', '.join(INGEST_DOCS)}) to document counts")
    if not (isinstance(plugins, dict) and all(st in STATES and isinstance(names, list)
                                              and all(isinstance(n, str) and n for n in names)
                                              for st, names in plugins.items())):
        probs.append("ci_plugins must map states to lists of pytest plugin names")
    info = raw.get("info_runs", [])

    def named(x, names):
        return isinstance(x, str) and x in names

    if not (isinstance(info, list) and all(
            isinstance(r, dict) and set(r) == set(INFO_RUN_FIELDS) and named(r["state"], STATES)
            and isinstance(r["result_chars"], int) and not isinstance(r["result_chars"], bool) and r["result_chars"] > 0
            and isinstance(r["suites"], list) and r["suites"] and all(named(s, SUITES) for s in r["suites"])
            and isinstance(r["refs"], list) and r["refs"] and all(named(s, STATES) for s in r["refs"])
            for r in info)):
        probs.append(f"info_runs must be a list of {{{', '.join(INFO_RUN_FIELDS)}}}: a state, a positive "
                     "CANDLEKEEP_RESULT_CHARS, a non-empty list of suites and a non-empty list of states to compare with")
    if probs:
        raise SystemExit(f"--round {path}: " + "; ".join(probs))
    return {"file": path, "name": raw["name"], "results_root": round_location(raw["results_root"]),
            "eval_home": round_location(raw["eval_home"]), "doc": round_location(raw["doc"]),
            "states": {st: {"checkout": round_location(s["checkout"]), "venv": round_location(s["venv"]),
                            "ref": s["ref"], "fastmcp": s["fastmcp"]} for st, s in states.items()},
            "corpus_documents": dict(docs), "ci_plugins": {st: sorted(names) for st, names in plugins.items()},
            "info_runs": [dict(r, suites=list(r["suites"]), refs=list(r["refs"])) for r in info]}


def apply_round(rnd: dict) -> None:
    """Make a round file's values this verifier's expectations and defaults (module docstring).
    ROUND1_ROOT and ROUND1_EVAL_HOME keep round 1's, for round_isolation_problems."""
    global DEFAULT_ROOT, DEFAULT_DOC, DEFAULT_EVAL_HOME, DEFAULT_B_PYTHON, C_REF, CI_PLUGINS, ROUND
    DEFAULT_ROOT, DEFAULT_DOC, DEFAULT_EVAL_HOME = rnd["results_root"], rnd["doc"], rnd["eval_home"]
    states = rnd["states"]
    DEFAULT_B_PYTHON = states["B"]["venv"] / "bin" / "python"
    STATE_REF.update({st: states[st]["ref"] for st in ("A", "B")})
    C_REF = states["C"]["ref"]
    FASTMCP_VERSION.update({st: s["fastmcp"] for st, s in states.items()})
    STATE_CHECKOUT.update({st: states[st]["checkout"] for st in ("A", "C")})
    INGEST_DOCS.update(rnd["corpus_documents"])
    CI_PLUGINS = {st: rnd["ci_plugins"].get(st, []) for st in STATES}
    INFO_RUNS[:] = rnd["info_runs"]
    ROUND = rnd


def _same_file(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:      # either one does not exist (or cannot be read)
        return False


def within(path: Path, root: Path) -> bool:
    """path is root or lies under it: by name, or by identity (os.path.samefile) of root and an
    existing ancestor of path, so that another spelling of a directory (its case, on macOS, or
    a symlink) still counts."""
    path, root = Path(path).expanduser().resolve(), Path(root).expanduser().resolve()
    return path.is_relative_to(root) or any(_same_file(p, root) for p in (path, *path.parents))


def same_dir(a: Path, b: Path) -> bool:
    return within(a, b) and within(b, a)


def round_isolation_problems(args) -> list:
    """With --round: where --root (read and written) or the data/ and staging/ directories
    under --eval-home (read) meet what a round must neither read nor write: round 1's results
    root and the data, staging, scratch, run, worktrees and venvs directories of its EVAL_HOME
    (the defaults of a run without --round), round 1's B′ results (tests/results/agent_view_bprime,
    section 16), every other existing results tree (tests/results/agent_view_*), and the round's
    A and C checkouts. Directories are compared both ways (one inside the other) with within()."""
    results = REPO / "tests" / "results"
    off = [("round 1's results root", ROUND1_ROOT), ("round 1's B′ results", results / "agent_view_bprime")]
    off += [(f"round 1's {d}/", ROUND1_EVAL_HOME / d)
            for d in ("data", "staging", "scratch", "run", "worktrees", "venvs")]
    listed = [ROUND["results_root"], *(q for _w, q in off)]      # the round's own tree, and those named above
    off += [(f"the results tree {p.name}", p) for p in sorted(results.glob("agent_view_*"))
            if p.is_dir() and not any(same_dir(p, q) for q in listed)]
    off += [(f"the checkout of {st}", p) for st, p in sorted(STATE_CHECKOUT.items())]
    mine = [("--root", Path(args.root))]
    mine += [(f"--eval-home's {d}/", Path(args.eval_home) / d) for d in ("data", "staging")]
    return [f"{opt} {p} overlaps {what} {q}" for opt, p in mine for what, q in off if within(p, q) or within(q, p)]


# ── Main ────────────────────────────────────────────────────────────

def cmd_metrics_of(path: Path, args) -> int:
    doc, err = load_json_safe(path)
    if not isinstance(doc, dict):
        print(json.dumps({"error": err or "not a JSON object"}))
        return 1
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    st, su, _tg = parse_stem(path.stem)
    layer = meta.get("layer") or ("L2" if "L2" in path.parts or path.parent.name == "L2" else "L1")
    state = meta.get("state") or st
    suite = meta.get("suite") or su
    queries = [q for q in doc.get("queries") or [] if isinstance(q, dict)]
    if layer == "L1":
        m = l1_metrics(doc, queries, suite, state)
    else:
        gold = GoldChunks(Path(args.b_python), args.gold_body) if suite == "CEN-G" else None
        cid = SUITE_CORPUS.get(suite)
        corpus = Corpus(cid, Path(args.eval_home)) if cid else None
        m = l2_metrics(doc, queries, suite, state, L2Context(corpus, gold))
        if gold is not None and gold.error:
            print(f"warning: {gold.error}", file=sys.stderr)
    print(json.dumps({"metrics": m}, ensure_ascii=False, default=_json_default))
    return 0


def cmd_all(args) -> tuple:
    root = Path(args.root)
    v = Verifier(root, Path(args.doc), Path(args.repo), Path(args.eval_home), Path(args.b_python), args.gold_body)
    v.vdir.mkdir(parents=True, exist_ok=True)
    v.load_runs()
    v.collect_file_checks()
    for run in v.runs.values():
        if getattr(run, "payload", None) is not None:
            write_json(v.vdir / f"recomputed_{run.layer}_{run.stem}.json", run.payload)
    v.check_v03_global()
    v.check_v01()
    v.check_v04()
    v.check_v07()
    judges = Judges(v)
    judges.run()
    v.data_notes()
    ci = ci_gates(v)
    sample = spot_sample(v)
    write_json(v.vdir / "spot_check_sample.json", sample)
    notes_md = v.vdir / "spot_checks.md"
    v.checks["V-08"] = {"title": "Spot check (manual)", "items": [
        item("verification/spot_check_sample.json written", "pass", "30 queries"),
        item("verification/spot_checks.md (hand notes)", "pass" if notes_md.exists() else "pending",
             "present" if notes_md.exists() else "write notes after inspecting the sample")]}
    v.checks["V-09"] = {"title": "Table vs JSON", "items": [item("verify.py --check-doc", "pending", "not run")]}
    status = {k: check_status(c["items"]) for k, c in sorted(v.checks.items())}
    summary = build_summary(v, judges, ci, {k: status[k] for k in status if k != "V-09"})
    summary["meta"] = {"generated_by": "scripts/eval_agent_view/verify.py", "generated_at": now_iso(),
                       "root": str(root), "seed": SEED, "n_boot": N_BOOT, "delta": DELTA,
                       "bootstrap": "numpy default_rng(20261018).integers(0, n, (10000, n)); percentile 2.5/97.5 of resampled mean differences",
                       "mcnemar": "scipy.stats.binomtest(c, b + c, 0.5), two-sided",
                       "inputs": {r.label: r.sha256 for r in list(v.runs.values()) + v.extra_runs if r.present},
                       "cen_g_gold_body": args.gold_body, "ci_paths": list(CI_PATHS),
                       "cen_g_exclusion": getattr(v, "cen_g_exclusion", None),
                       **({"round": {"name": ROUND["name"], "file": str(ROUND["file"])}} if ROUND else {})}
    write_json(root / "summary.json", summary)
    checks = {"generated_at": now_iso(), "root": str(root),
              **({"round": {"name": ROUND["name"], "file": str(ROUND["file"])}} if ROUND else {}), "status": status,
              "checks": {k: {"title": c["title"], "status": status[k], "items": c["items"]} for k, c in sorted(v.checks.items())},
              "missing_inputs": [r.label for r in v.runs.values() if not r.present],
              "extra_inputs": [r.label for r in v.extra_runs],
              "notes": v.notes}
    write_json(v.vdir / "checks.json", checks)
    return v, summary, checks


def main(argv=None) -> int:
    global CI_PATHS
    pre = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    pre.add_argument("--round")
    known, _rest = pre.parse_known_args(argv)
    if known.round is not None:                  # an empty value is refused, never taken as round 1
        apply_round(load_round(known.round))     # before the defaults below are read
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--round", metavar="FILE",
                    help="round file of a later round, e.g. scripts/eval_agent_view/rounds/r2.json: refs, FastMCP "
                         "versions and checkouts of the states, the defaults of --root, --doc, --eval-home and "
                         "--b-python, document counts and the CI plugin rule (default: round 1)")
    ap.add_argument("--metrics-of", type=Path, help="recompute and print the metrics of one L1/L2 file")
    ap.add_argument("--all", action="store_true", help="run every check and write summary.json")
    ap.add_argument("--render", action="store_true", help="write verification/section15.md from summary.json")
    ap.add_argument("--check-doc", action="store_true", help="diff section 15 of the protocol against the rendering")
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="results root (default: %(default)s)")
    ap.add_argument("--doc", default=str(DEFAULT_DOC), help="protocol document (default: %(default)s)")
    ap.add_argument("--repo", default=str(REPO), help="git repository (default: %(default)s)")
    ap.add_argument("--eval-home", default=str(DEFAULT_EVAL_HOME), help="EVAL_HOME (BEIR staging) (default: %(default)s)")
    ap.add_argument("--b-python", default=os.environ.get("VERIFY_B_PYTHON", str(DEFAULT_B_PYTHON)),
                    help="state B interpreter used to rebuild CEN-G gold chunks (default: %(default)s)")
    ap.add_argument("--gold-body", choices=("product", "contract"), default="product",
                    help="body rule for CEN-G gold chunks: the body DocumentProcessor keeps, i.e. the indexed chunks "
                         "the graded labels refer to (default), or the data contract's regex-stripped body")
    ap.add_argument("--ci-paths", default=",".join(CI_PATHS),
                    help="router benchmark paths C-14 compares against A's run (default: %(default)s, the paths the "
                         "project's CI compares; narrowing it needs a Deviations Log entry)")
    args = ap.parse_args(argv)
    if args.round != known.round:    # an abbreviated --round that only this parser understood
        ap.error("spell out --round (it must be read before the other options' defaults)")
    if ROUND is not None:
        problems = round_isolation_problems(args)
        if problems:
            ap.error(f"refusing round {ROUND['name']!r} ({ROUND['file']}): " + "; ".join(problems))
    CI_PATHS = tuple(p.strip() for p in args.ci_paths.split(",") if p.strip())
    if args.metrics_of:
        return cmd_metrics_of(args.metrics_of, args)
    if not (args.all or args.render or args.check_doc):
        ap.print_help()
        return 2
    root = Path(args.root)
    rc = 0
    checks = None
    if args.all:
        _v, summary, checks = cmd_all(args)
        st = checks["status"]
        auto = {k: s for k, s in st.items() if k not in ("V-08", "V-09")}
        rc = 1 if "fail" in auto.values() else (0 if all(s == "pass" for s in auto.values()) else 2)
        for k, s in st.items():
            print(f"{k:5} {s:8} {checks['checks'][k]['title']}", file=sys.stderr)
    else:
        summary, err = load_json_safe(root / "summary.json")
        if summary is None:
            print(f"summary.json {err}; run --all first", file=sys.stderr)
            return 2
    rendered = render_section15(summary)
    if args.render:
        out = root / "verification" / "section15.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    if args.check_doc:
        ok, msg = check_doc(Path(args.doc), rendered)
        print(msg if not ok else f"V-09 pass: {msg}", file=sys.stderr if ok else sys.stdout)
        cpath = root / "verification" / "checks.json"
        if checks is None:
            checks, _e = load_json_safe(cpath)
        if isinstance(checks, dict) and "checks" in checks:
            checks["checks"]["V-09"] = {"title": "Table vs JSON", "status": "pass" if ok else "fail",
                                        "items": [item("protocol section 15 equals the rendering of summary.json",
                                                       "pass" if ok else "fail", "" if ok else msg[:4000])]}
            checks["status"]["V-09"] = "pass" if ok else "fail"
            write_json(cpath, checks)
        if not ok:
            rc = 1
        elif not args.all:
            rc = max(rc, 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
