#!/usr/bin/env python3
"""Shared code for the agent-view evaluation harness.

The protocol is docs/AGENT_VIEW_EVALUATION.md (frozen). This module holds:

* the state, corpus and suite registries (protocol sections 3-5),
* query loading into the harness's query records,
* text normalisation, shingles, frontmatter stripping and gold-text loading,
* reconstruction of the CEN-G gold chunks with the product chunker,
* parsing of the raw `search` tool output,
* the Layer 1 and Layer 2 metric code,
* ingest identity, code provenance and the Chroma process identity guards,
* a pre-flight check, and small process, port and MCP helpers.

Importing this module never imports candlekeep, numpy, chromadb or fastmcp;
functions that need them import them lazily. Candlekeep is only imported after
prepare_candlekeep_env() has pointed the import-time background thread of
candlekeep.mcp.server at a dead Chroma port and a scratch data directory.

CLI (run with venv B's python):
    common.py preflight [--out FILE]
    common.py wait-ready --url URL [--timeout SECONDS]
    common.py fingerprint --port PORT
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.util
import json
import math
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

# ── Fixed locations and constants ────────────────────────────────────────────

HARNESS_DIR = Path(__file__).resolve().parent
REPO = HARNESS_DIR.parents[1]                      # the main checkout (state B)
FIXTURES = REPO / "tests" / "fixtures"
EVAL_HOME = Path(os.environ.get("CK_EVAL_HOME") or (Path.home() / ".cache" / "candlekeep-eval"))
UV = Path.home() / ".local" / "bin" / "uv"
MODELS_DIR = Path.home() / ".cache" / "candlekeep" / "models"

PATHS = ("hybrid", "precise", "explore")           # protocol path order
DEVICE = "mps"
SEED = 20261018                                    # protocol section 4
HASH_SEED = "20261018"                             # PYTHONHASHSEED for every candlekeep process
DEAD_PORT = 65530
DEAD_CHROMA_URL = f"http://127.0.0.1:{DEAD_PORT}"
SHINGLE_LEN = 150
SHINGLE_STEP = 25
GOLD_CHUNK_GRADE = 2                               # CEN-G gold chunks: grade >= 2
# DocumentProcessor.SUPPORTED_EXTENSIONS: what an ingest of a directory picks up.
SUPPORTED_EXTENSIONS = (".txt", ".md", ".pdf", ".rst", ".json", ".yaml", ".yml")
# DocumentProcessor.FRONTMATTER_PATTERN
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Which document body the CEN-G gold chunks are cut from (see GoldText.chunk_body).
#   product:  the body DocumentProcessor._parse_frontmatter keeps (what ingest chunks;
#             the graded labels' chunk indices come from DocumentProcessor.process()).
#   contract: the body left by FRONTMATTER_RE (the data contract's literal wording).
# They differ only for documents whose frontmatter is not valid YAML. The harness
# default is "product", pending the lead's sign-off (README, "CEN-G gold chunks");
# the mode is recorded in every L2 file's meta (cen_g_gold_body), --recompute uses
# the recorded mode, and drive.py verify passes the same mode to verify.py.
GOLD_BODIES = ("product", "contract")
CEN_G_GOLD_BODY = "product"
GOLD_BODY_DESCRIPTIONS = {
    "product": "DocumentProcessor._parse_frontmatter body, chunk_size 512, overlap 50",
    "contract": r"body after the frontmatter regex ^---\s*\n(.*?)\n---\s*\n, chunk_size 512, overlap 50",
}


@dataclass
class Config:
    """Mutable run configuration. Hidden test options may override it."""
    data_root: Path = EVAL_HOME / "data"          # <data_root>/<I0x>/{chroma,ck_data}
    staging_root: Path = EVAL_HOME / "staging"    # <staging_root>/<I0x>/: BEIR <doc_id>.md files, I01/I02 symlinks
    scratch_root: Path = EVAL_HOME / "scratch"    # throwaway candlekeep data dirs
    run_root: Path = EVAL_HOME / "run"            # pid files of detached Chroma servers
    results_root: Path = REPO / "tests" / "results" / "agent_view_eval"
    ingest_port: int = 8130
    l2_port: int = 8131


CONFIG = Config()


# ── Registries ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StateDef:
    name: str
    checkout: Path
    venv: Path
    ref: str | None        # A: commit to be checked out; B: commit whose src/ must match
    fastmcp: str           # FastMCP version the state pins

    @property
    def python(self) -> Path:
        return self.venv / "bin" / "python"

    @property
    def bin(self) -> Path:
        return self.venv / "bin"


STATES = {
    "A": StateDef("A", EVAL_HOME / "worktrees" / "A", EVAL_HOME / "venvs" / "A", "6519cc7", "2.14.5"),
    "B": StateDef("B", REPO, REPO / ".venv", "d524652", "3.4.9"),
    "C": StateDef("C", EVAL_HOME / "worktrees" / "C", EVAL_HOME / "venvs" / "C", None, "3.4.9"),
}
VENV_B = STATES["B"].venv


@dataclass(frozen=True)
class CorpusDef:
    id: str
    name: str                     # used in ingest/<id>_<name>.json
    # How the one ingest call of the corpus (protocol section 16) gets its documents:
    #   "dirs":  the corpus is one directory, ingested as it is;
    #   "links": several directories, staged as one directory of symlinks (one per file);
    #   "beir":  documents staged as files from corpus.jsonl.
    kind: str
    chunk_overlap: int
    chroma_port: int
    n_docs: int | None
    source_dirs: tuple = ()
    beir_dir: Path | None = None

    def ingest_dirs(self) -> list[Path]:
        """Directories that hold the corpus's documents as files (gold text, pre-flight):
        the source directories, or for BEIR the staging directory."""
        if self.kind == "beir":
            return [CONFIG.staging_root / self.id]
        return [Path(d) for d in self.source_dirs]

    def ingest_path(self) -> Path:
        """The one directory given to the MCP ingest call: the staging directory for
        "links" and "beir" corpora, else the corpus's only source directory."""
        if self.kind in ("links", "beir"):
            return CONFIG.staging_root / self.id
        if len(self.source_dirs) != 1:
            raise ValueError(f"corpus {self.id}: kind 'dirs' needs exactly one source directory "
                             f"(use kind 'links' for several), has {len(self.source_dirs)}")
        return Path(self.source_dirs[0])


_CEN_DIRS = (FIXTURES / "sample_docs", FIXTURES / "scale_docs")
_CD = FIXTURES / "cross_domain"
CORPORA = {c.id: c for c in [
    CorpusDef("I01", "CEN", "links", 100, 8121, 89, _CEN_DIRS),
    CorpusDef("I02", "CEN-G", "links", 50, 8122, 89, _CEN_DIRS),
    CorpusDef("I03", "CD-LEG", "dirs", 100, 8123, 90, (_CD / "legal_docs",)),
    CorpusDef("I04", "CD-MED", "dirs", 100, 8124, 91, (_CD / "medical_docs",)),
    CorpusDef("I05", "CD-NAR", "dirs", 100, 8125, 89, (_CD / "narrative_docs",)),
    CorpusDef("I06", "CD-API", "dirs", 100, 8126, 95, (_CD / "api_ref_docs",)),
    CorpusDef("I07", "CD-ALT", "dirs", 100, 8127, 88, (_CD / "alternating_docs",)),
    CorpusDef("I08", "BEIR-SF", "beir", 100, 8128, 5183, beir_dir=FIXTURES / "beir" / "scifact"),
    CorpusDef("I09", "BEIR-NF", "beir", 100, 8129, 3633, beir_dir=FIXTURES / "beir" / "nfcorpus"),
]}


@dataclass(frozen=True)
class SuiteDef:
    name: str
    corpus: str
    loader: str                   # centurion | centurion_graded | multihop | cross_domain | beir | records
    prefix: str                   # qid prefix
    n_results: int = 5
    file: Path | None = None
    expected_n: int | None = None
    width: int = 3                # zero padding of the qid number


SUITES = {s.name: s for s in [
    SuiteDef("CEN", "I01", "centurion", "CEN", file=FIXTURES / "eval_suite_100.json", expected_n=108),
    SuiteDef("MH", "I01", "multihop", "MH", file=FIXTURES / "track2_multi_hop_queries.json",
             expected_n=30, width=2),
    SuiteDef("CEN-G", "I02", "centurion_graded", "CENG", file=FIXTURES / "eval_suite_100.json",
             expected_n=108),
    SuiteDef("CD-LEG", "I03", "cross_domain", "LEG", file=_CD / "eval_suite_legal.json", expected_n=107),
    SuiteDef("CD-MED", "I04", "cross_domain", "MED", file=_CD / "eval_suite_medical.json", expected_n=108),
    SuiteDef("CD-NAR", "I05", "cross_domain", "NAR", file=_CD / "eval_suite_narrative.json", expected_n=108),
    SuiteDef("CD-API", "I06", "cross_domain", "API", file=_CD / "eval_suite_api_ref.json", expected_n=108),
    SuiteDef("CD-ALT", "I07", "cross_domain", "ALT", file=_CD / "eval_suite_alternating.json",
             expected_n=104),
    SuiteDef("BEIR-SF", "I08", "beir", "SF", n_results=10, expected_n=300),
    SuiteDef("BEIR-NF", "I09", "beir", "NF", n_results=10, expected_n=323),
]}
CEN_ANSWERS = FIXTURES / "eval_suite_with_answers.json"


def suites_of_corpus(corpus_id: str) -> list[str]:
    return [s.name for s in SUITES.values() if s.corpus == corpus_id]


# ── Output locations ─────────────────────────────────────────────────────────

def corpus_root(corpus: CorpusDef) -> Path:
    return CONFIG.data_root / corpus.id


def chroma_dir(corpus: CorpusDef) -> Path:
    return corpus_root(corpus) / "chroma"


def ck_data_dir(corpus: CorpusDef) -> Path:
    return corpus_root(corpus) / "ck_data"


def chroma_url(corpus: CorpusDef) -> str:
    return f"http://127.0.0.1:{corpus.chroma_port}"


def ingest_record_path(corpus: CorpusDef) -> Path:
    return CONFIG.results_root / "ingest" / f"{corpus.id}_{corpus.name}.json"


def layer_path(layer: str, state: str, suite: str, tag: str | None = None) -> Path:
    return CONFIG.results_root / layer / f"{state}_{suite}{'_' + tag if tag else ''}.json"


def logs_dir() -> Path:
    d = CONFIG.results_root / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Hidden test overrides ────────────────────────────────────────────────────

HIDDEN_FLAGS = ("--test-config", "--data-root", "--results-root", "--ports")


def add_hidden_args(ap: argparse.ArgumentParser) -> None:
    """Smoke-test options. Not part of the protocol, so hidden from --help."""
    for flag in HIDDEN_FLAGS:
        ap.add_argument(flag, default=None, help=argparse.SUPPRESS)


def hidden_argv(args: argparse.Namespace) -> list[str]:
    """The hidden options of args, ready to forward to another harness script."""
    out = []
    for flag in HIDDEN_FLAGS:
        value = getattr(args, flag[2:].replace("-", "_"), None)
        if value is not None:
            out += [flag, str(value)]
    return out


def apply_overrides(args: argparse.Namespace) -> None:
    """Apply hidden overrides.

    --test-config FILE   JSON with optional keys data_root, staging_root,
                         scratch_root, run_root, results_root, ports,
                         "corpora"/"suites" that add registry entries, and
                         "states" that repoint a state's checkout/venv.
    --data-root DIR      DIR/{data,staging,scratch,run} replace the EVAL_HOME ones.
    --results-root DIR   replaces tests/results/agent_view_eval.
    --ports SPEC         e.g. "chroma=8141,ingest=8142,l2=8143";
                         chroma applies to every corpus.
    """
    cfg_file = getattr(args, "test_config", None)
    if cfg_file:
        cfg = json.loads(Path(cfg_file).read_text(encoding="utf-8"))
        for key in ("data_root", "staging_root", "scratch_root", "run_root", "results_root"):
            if cfg.get(key):
                setattr(CONFIG, key, Path(cfg[key]))
        for cid, c in (cfg.get("corpora") or {}).items():
            CORPORA[cid] = CorpusDef(
                id=cid, name=c.get("name", cid),
                kind=c.get("kind") or ("links" if len(c.get("dirs", [])) > 1 else "dirs"),
                chunk_overlap=int(c.get("chunk_overlap", 100)), chroma_port=int(c["chroma_port"]),
                n_docs=c.get("n_docs"), source_dirs=tuple(Path(d) for d in c.get("dirs", [])),
                beir_dir=Path(c["beir_dir"]) if c.get("beir_dir") else None)
        for name, s in (cfg.get("suites") or {}).items():
            SUITES[name] = SuiteDef(
                name=name, corpus=s["corpus"], loader=s.get("loader", "records"),
                prefix=s.get("prefix", name), n_results=int(s.get("n_results", 5)),
                file=Path(s["file"]) if s.get("file") else None, expected_n=s.get("expected_n"),
                width=int(s.get("width", 3)))
        for name, s in (cfg.get("states") or {}).items():
            base = STATES[name]
            STATES[name] = replace(base, checkout=Path(s.get("checkout", base.checkout)),
                                   venv=Path(s.get("venv", base.venv)))
        if cfg.get("ports"):
            _apply_ports(cfg["ports"])
    if getattr(args, "data_root", None):
        root = Path(args.data_root)
        CONFIG.data_root, CONFIG.staging_root = root / "data", root / "staging"
        CONFIG.scratch_root, CONFIG.run_root = root / "scratch", root / "run"
    if getattr(args, "results_root", None):
        CONFIG.results_root = Path(args.results_root)
    if getattr(args, "ports", None):
        _apply_ports(dict(part.split("=", 1) for part in args.ports.split(",") if part))


def _apply_ports(ports: dict) -> None:
    if "chroma" in ports:
        for cid in list(CORPORA):
            CORPORA[cid] = replace(CORPORA[cid], chroma_port=int(ports["chroma"]))
    if "ingest" in ports:
        CONFIG.ingest_port = int(ports["ingest"])
    if "l2" in ports:
        CONFIG.l2_port = int(ports["l2"])


# ── Query records ────────────────────────────────────────────────────────────

RECORD_KEYS = ("qid", "query", "category", "gold_sources", "graded_chunks", "graded_docs", "supporting")


def basename(path: str) -> str:
    return PurePosixPath(str(path)).name


def make_record(qid, query, category, gold_sources, graded_chunks=None, graded_docs=None,
                supporting=None) -> dict:
    return {
        "qid": qid,
        "query": query,
        "category": category,
        "gold_sources": list(gold_sources),
        "graded_chunks": graded_chunks,
        "graded_docs": graded_docs,
        "supporting": list(supporting) if supporting is not None else None,
    }


def is_adversarial(record: dict) -> bool:
    return record.get("category") == "adversarial"


def _query_list(obj):
    """A suite file may be a list of queries or a dict with a "queries" list."""
    if isinstance(obj, dict) and "queries" in obj:
        return obj["queries"]
    if isinstance(obj, list):
        return obj
    raise ValueError("suite file is neither a list nor a dict with 'queries'")


def convert_graded(graded: dict) -> dict:
    """'tests/fixtures/<dir>/<name>:<idx>' -> '<name>:<idx>' (key order kept)."""
    out = {}
    for key, grade in graded.items():
        path, idx = key.rsplit(":", 1)
        new = f"{basename(path)}:{int(idx)}"
        if new in out:
            raise ValueError(f"graded_relevance key collides after basename conversion: {key}")
        out[new] = int(grade)
    return out


def load_beir_queries(beir_dir: Path) -> dict:
    """{query_id: text} in queries.jsonl order."""
    queries = {}
    with open(beir_dir / "queries.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                queries[str(d["_id"])] = d["text"]
    return queries


def load_beir_qrels(beir_dir: Path, split: str = "test") -> dict:
    """{query_id: {doc_id: grade}} in qrels file order (first appearance)."""
    qrels: dict = {}
    with open(beir_dir / "qrels" / f"{split}.tsv", encoding="utf-8") as f:
        for n, line in enumerate(f):
            parts = line.rstrip("\n").split("\t")
            if n == 0 and parts[0] == "query-id":
                continue
            if len(parts) < 3:
                continue
            qid, did, grade = parts[0], parts[1], int(parts[2])
            rels = qrels.setdefault(qid, {})
            if did in rels:
                raise ValueError(f"duplicate qrel {qid} {did}")
            rels[did] = grade
    return qrels


def iter_beir_corpus(beir_dir: Path):
    with open(beir_dir / "corpus.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                yield str(d["_id"]), d.get("title", "") or "", d.get("text", "") or ""


def beir_staged_content(title: str, text: str) -> str:
    """Protocol section 5: <_id>.md with frontmatter title and empty description."""
    return f"---\ntitle: {json.dumps(title)}\ndescription: \"\"\n---\n{text}\n"


def load_queries(suite: SuiteDef | str) -> list[dict]:
    """Query records of a suite, in file order. Raises on any count or shape problem."""
    suite = SUITES[suite] if isinstance(suite, str) else suite
    loader = suite.loader
    recs: list[dict] = []
    if loader in ("centurion", "centurion_graded", "cross_domain"):
        raw = _query_list(json.loads(Path(suite.file).read_text(encoding="utf-8")))
        for i, q in enumerate(raw):
            graded = convert_graded(q.get("graded_relevance") or {}) if loader == "centurion_graded" else None
            recs.append(make_record(f"{suite.prefix}-{i + 1:0{suite.width}d}", q["query"], q["category"],
                                    [basename(s) for s in q.get("expected_sources", [])],
                                    graded_chunks=graded))
    elif loader == "multihop":
        raw = _query_list(json.loads(Path(suite.file).read_text(encoding="utf-8")))
        for i, q in enumerate(raw):
            docs = [basename(s) for s in q["supporting_docs"]]
            recs.append(make_record(f"{suite.prefix}-{i + 1:0{suite.width}d}", q["query"], "multihop",
                                    docs, supporting=docs))
    elif loader == "beir":
        beir_dir = CORPORA[suite.corpus].beir_dir
        queries = load_beir_queries(beir_dir)
        for qid, rels in load_beir_qrels(beir_dir).items():
            if qid not in queries:
                continue
            recs.append(make_record(f"{suite.prefix}-{qid}", queries[qid], "beir",
                                    [f"{d}.md" for d, g in rels.items() if g > 0],
                                    graded_docs={f"{d}.md": g for d, g in rels.items()}))
    elif loader == "records":
        recs = [dict(r) for r in _query_list(json.loads(Path(suite.file).read_text(encoding="utf-8")))]
    else:
        raise ValueError(f"unknown loader {loader}")
    problems = validate_records(recs)
    if suite.expected_n is not None and len(recs) != suite.expected_n:
        problems.append(f"{suite.name}: {len(recs)} queries, protocol expects {suite.expected_n}")
    if problems:
        raise ValueError("; ".join(problems))
    return recs


def validate_records(recs: list[dict]) -> list[str]:
    problems, seen = [], set()
    for r in recs:
        if set(r) != set(RECORD_KEYS):
            problems.append(f"{r.get('qid')}: keys {sorted(r)}")
            continue
        if r["qid"] in seen:
            problems.append(f"duplicate qid {r['qid']}")
        seen.add(r["qid"])
        if not isinstance(r["query"], str) or not r["query"]:
            problems.append(f"{r['qid']}: empty query")
        if not isinstance(r["gold_sources"], list):
            problems.append(f"{r['qid']}: gold_sources is not a list")
    return problems


# ── Text: normalisation, shingles, frontmatter ───────────────────────────────

_BACKSLASH_RE = re.compile(r"\\([_*\[\]()#.\-`|<>])")
_WS_RE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Remove a backslash before _ * [ ] ( ) # . - ` | < >, collapse whitespace runs
    to one space, lowercase, strip (in that order)."""
    text = _BACKSLASH_RE.sub(r"\1", text)
    text = _WS_RE.sub(" ", text)
    return text.lower().strip()


def shingles(text: str) -> list[str]:
    """Shingles of a text: s[i:i+150] for i = 0, 25, 50, ... while i + 150 <= len(s),
    or [s] when len(s) < 150. An empty normalised text has no shingles (degenerate
    case, reported by the pre-flight check; it never occurs in the protocol data)."""
    s = normalise(text)
    if not s:
        return []
    if len(s) < SHINGLE_LEN:
        return [s]
    return [s[i:i + SHINGLE_LEN] for i in range(0, len(s) - SHINGLE_LEN + 1, SHINGLE_STEP)]


def read_doc(path: Path) -> str:
    """As DocumentProcessor._extract_text reads a text file."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def strip_frontmatter(text: str) -> str:
    """Remove the YAML frontmatter matched by DocumentProcessor.FRONTMATTER_PATTERN."""
    m = FRONTMATTER_RE.match(text)
    return text[m.end():] if m else text


# ── Raw tool-output parsing ──────────────────────────────────────────────────

HEADER_RE = re.compile(r"^\*\*Score: (-?[0-9.]+)\*\* \| Source: (.+)$")
FENCE = "```"


def parse_output(raw: str) -> list[dict]:
    """Result blocks of a `search` tool output: [{"score", "source", "body"}].

    A block starts at a header line; its visible body is the text between the
    first line that is exactly ``` after the header and the last such line
    before the next header (or the end). "No results found." has no header
    lines and therefore zero blocks.
    """
    if not raw:
        return []
    lines = raw.split("\n")
    heads = [i for i, line in enumerate(lines) if HEADER_RE.match(line)]
    blocks = []
    for n, h in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        m = HEADER_RE.match(lines[h])
        fences = [i for i in range(h + 1, end) if lines[i] == FENCE]
        body = "\n".join(lines[fences[0] + 1:fences[-1]]) if len(fences) >= 2 else ""
        blocks.append({"score": m.group(1), "source": m.group(2), "body": body})
    return blocks


# ── Gold text ────────────────────────────────────────────────────────────────

def corpus_file_index(dirs) -> tuple[dict, dict]:
    """({basename: path}, {basename: [paths]} collisions) over the files an ingest
    of these directories picks up (DocumentProcessor.SUPPORTED_EXTENSIONS)."""
    index, collisions = {}, {}
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                if p.name in index and index[p.name] != p:
                    collisions.setdefault(p.name, [str(index[p.name])]).append(str(p))
                    continue
                index[p.name] = p
    return index, collisions


class GoldText:
    """Gold-document bodies and shingle sets for one corpus.

    A document's text is its file content minus the frontmatter. BEIR documents
    are the staged .md files; when the staging directory is absent the identical
    content is regenerated from corpus.jsonl with beir_staged_content().
    gold_body selects the body the CEN-G gold chunks are cut from (GOLD_BODIES).
    """

    def __init__(self, dirs, beir_dir: Path | None = None, gold_body: str = CEN_G_GOLD_BODY):
        if gold_body not in GOLD_BODIES:
            raise ValueError(f"gold_body must be one of {GOLD_BODIES}, not {gold_body!r}")
        self.gold_body = gold_body
        self.dirs = [Path(d) for d in dirs]
        self.index, self.collisions = corpus_file_index(self.dirs)
        self.beir_dir = Path(beir_dir) if beir_dir else None
        self._beir_fallback = self.beir_dir is not None and not any(d.is_dir() for d in self.dirs)
        self._beir_docs: dict | None = None
        self._doc_shingles: dict = {}
        self._chunk_cache: dict = {}
        self._chunk_shingles: dict = {}

    @classmethod
    def for_meta(cls, meta: dict, gold_body: str | None = None) -> "GoldText":
        """GoldText for a stored file: its corpus, and the gold body recorded in its
        meta (files without the key were computed with the default) unless overridden."""
        corpus = CORPORA.get(meta.get("corpus", ""))
        dirs = meta.get("corpus_dirs") or (corpus.ingest_dirs() if corpus else [])
        return cls(dirs, corpus.beir_dir if corpus else None,
                   gold_body or meta.get("cen_g_gold_body") or CEN_G_GOLD_BODY)

    @property
    def source(self) -> str:
        return "regenerated from corpus.jsonl" if self._beir_fallback else "corpus files"

    def body(self, name: str) -> str | None:
        if self._beir_fallback:
            if self._beir_docs is None:
                self._beir_docs = {f"{i}.md": (t, x) for i, t, x in iter_beir_corpus(self.beir_dir)}
            doc = self._beir_docs.get(name)
            return strip_frontmatter(beir_staged_content(*doc)) if doc else None
        path = self.index.get(name)
        if path is None or path.suffix.lower() == ".pdf":
            return None
        return strip_frontmatter(read_doc(path))

    def doc_shingles(self, name: str) -> frozenset:
        if name not in self._doc_shingles:
            body = self.body(name)
            self._doc_shingles[name] = frozenset(shingles(body)) if body is not None else frozenset()
        return self._doc_shingles[name]

    def raw_text(self, name: str) -> str | None:
        """Whole file content (frontmatter included), as the product reads it."""
        if self._beir_fallback:
            if self._beir_docs is None:
                self._beir_docs = {f"{i}.md": (t, x) for i, t, x in iter_beir_corpus(self.beir_dir)}
            doc = self._beir_docs.get(name)
            return beir_staged_content(*doc) if doc else None
        path = self.index.get(name)
        if path is None or path.suffix.lower() == ".pdf":
            return None
        return read_doc(path)

    def chunk_body(self, text: str) -> str:
        """The body a document's CEN-G gold chunks are cut from.

        product:  the body DocumentProcessor itself derives (_parse_frontmatter). It
                  equals the regex-stripped text unless the frontmatter is not valid
                  YAML, in which case the product keeps the frontmatter in the body;
                  chunk i is then still the product's chunk_index i, which is what
                  the graded labels refer to.
        contract: the text after the frontmatter regex (strip_frontmatter)."""
        if self.gold_body == "contract":
            return strip_frontmatter(text)
        return product_processor(512, 50)._parse_frontmatter(text)[1]

    def overlap50_chunks(self, name: str) -> list[str] | None:
        """Chunks of a document at chunk_size 512 / overlap 50, without the Bardic
        Knowledge prefix: DocumentProcessor._chunk_text applied to chunk_body()."""
        if name not in self._chunk_cache:
            text = self.raw_text(name)
            if text is None:
                self._chunk_cache[name] = None
            else:
                self._chunk_cache[name] = product_processor(512, 50)._chunk_text(self.chunk_body(text))
        return self._chunk_cache[name]

    def gold_chunk_shingle_sets(self, graded_chunks: dict) -> list[frozenset]:
        """Shingle sets of the gold chunks (grade >= 2) that exist, in key order."""
        sets = []
        for key, grade in graded_chunks.items():
            if grade < GOLD_CHUNK_GRADE:
                continue
            if key not in self._chunk_shingles:
                name, idx = key.rsplit(":", 1)
                chunks = self.overlap50_chunks(name)
                idx = int(idx)
                text = chunks[idx] if chunks is not None and 0 <= idx < len(chunks) else None
                self._chunk_shingles[key] = frozenset(shingles(text)) if text is not None else frozenset()
            if self._chunk_shingles[key]:
                sets.append(self._chunk_shingles[key])
        return sets


# ── Candlekeep import (product code) ─────────────────────────────────────────

def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def make_scratch_dir() -> Path:
    CONFIG.scratch_root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="ck_scratch_", dir=CONFIG.scratch_root))


def prepare_candlekeep_env(device: str = DEVICE) -> Path:
    """Make importing candlekeep harmless: drop CANDLEKEEP_*/CHROMA_* variables,
    point CHROMA_URL at a dead port and CANDLEKEEP_DATA_DIR at a scratch dir."""
    if port_in_use(DEAD_PORT):
        raise RuntimeError(f"port {DEAD_PORT} must be unused (it serves as the dead Chroma port)")
    for key in list(os.environ):
        if key.startswith("CANDLEKEEP_") or key.startswith("CHROMA_"):
            del os.environ[key]
    scratch = make_scratch_dir()
    import atexit
    atexit.register(shutil.rmtree, scratch, True)
    os.environ.update({
        "CHROMA_URL": DEAD_CHROMA_URL,
        "CANDLEKEEP_DATA_DIR": str(scratch),
        "CANDLEKEEP_DEVICE": device,
        "ANONYMIZED_TELEMETRY": "False",
    })
    return scratch


def dotenv_files_for_import() -> list[Path]:
    """The .env files candlekeep's config.load_dotenv would read if candlekeep were
    imported now: ./.env and <checkout of the importable candlekeep>/.env."""
    found = []
    spec = importlib.util.find_spec("candlekeep")
    candidates = [Path(".env").resolve()]
    if spec and spec.origin:
        candidates.append(Path(spec.origin).resolve().parents[2] / ".env")
    for p in candidates:
        if p.exists() and p not in found:
            found.append(p)
    return found


def import_candlekeep(timeout: float = 300.0):
    """Import candlekeep (its server module first, as the package does) and wait
    until the server's background init has given up on the dead port. Refuses
    when a .env file would be loaded into the process."""
    if "candlekeep" not in sys.modules:
        dotenv = dotenv_files_for_import()
        if dotenv:
            raise RuntimeError(f"refusing to import candlekeep: config.load_dotenv would load {dotenv}")
        prepare_candlekeep_env()
    # `import candlekeep.mcp.server` cannot be used: the package rebinds
    # candlekeep.mcp to the FastMCP instance. import_module reads sys.modules.
    server = importlib.import_module("candlekeep.mcp.server")
    deadline = time.monotonic() + timeout
    while getattr(server, "_loading", False):
        if time.monotonic() > deadline:
            raise TimeoutError("candlekeep's background init did not finish")
        time.sleep(0.05)
    return server


_PROCESSORS: dict = {}


def product_processor(chunk_size: int, chunk_overlap: int):
    """DocumentProcessor(Settings(chunk_size=..., chunk_overlap=...)) from the
    candlekeep installed in the running venv (venv B for Layer 2)."""
    key = (chunk_size, chunk_overlap)
    if key not in _PROCESSORS:
        import_candlekeep()
        from candlekeep.config import Settings
        from candlekeep.rag.processor import DocumentProcessor
        settings = Settings(chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                            data_dir=scratch_data_dir(), device="cpu")
        _PROCESSORS[key] = DocumentProcessor(settings)
    return _PROCESSORS[key]


def candlekeep_file() -> str | None:
    mod = sys.modules.get("candlekeep")
    return getattr(mod, "__file__", None)


def scratch_data_dir() -> Path:
    """The scratch CANDLEKEEP_DATA_DIR set by prepare_candlekeep_env (or a new one)."""
    value = os.environ.get("CANDLEKEEP_DATA_DIR")
    return Path(value) if value and Path(value).is_relative_to(CONFIG.scratch_root) else make_scratch_dir()


# ── Metrics ──────────────────────────────────────────────────────────────────

PROJECT_METRICS_FILE = REPO / "src" / "candlekeep" / "eval" / "metrics.py"
_PROJECT_METRICS = None


def project_metrics():
    """src/candlekeep/eval/metrics.py of the main checkout, loaded as a plain module
    (the file is identical in states A and B; loading it this way avoids the
    import-time side effects of the candlekeep package)."""
    global _PROJECT_METRICS
    if _PROJECT_METRICS is None:
        spec = importlib.util.spec_from_file_location("_candlekeep_eval_metrics", PROJECT_METRICS_FILE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PROJECT_METRICS = mod
    return _PROJECT_METRICS


def metrics_module_info() -> dict:
    return {"path": str(PROJECT_METRICS_FILE), "sha256": sha256_file(PROJECT_METRICS_FILE)}


def _mean(values: list):
    """Mean of a list; None for an empty list (means over empty sets are null)."""
    return sum(values) / len(values) if values else None


def _percentile(values: list, q: float):
    if not values:
        return None
    import numpy as np
    return float(np.percentile(np.asarray(values, dtype=float), q))


def rows_by_path(rows: list, queries: list) -> dict:
    """{path: {qid: row}} for the paths present, in protocol order; checks coverage."""
    qids = [q["qid"] for q in queries]
    by: dict = {}
    for row in rows:
        slot = by.setdefault(row["path"], {})
        if row["qid"] in slot:
            raise ValueError(f"duplicate row {row['qid']} {row['path']}")
        slot[row["qid"]] = row
    unknown = set(by) - set(PATHS)
    if unknown:
        raise ValueError(f"unknown paths {sorted(unknown)}")
    for path, slot in by.items():
        missing = [q for q in qids if q not in slot]
        extra = set(slot) - set(qids)
        if missing or extra:
            raise ValueError(f"path {path}: missing {missing[:5]} extra {sorted(extra)[:5]}")
    return {p: by[p] for p in PATHS if p in by}


def beir_ndcg_recall(sources: list, graded_docs: dict, k: int = 10) -> tuple[float, float]:
    """nDCG@k (linear gain, 1/log2(rank+1), ideal from the sorted grades of all
    relevant docs) and Recall@k over sources de-duplicated keeping first occurrence."""
    top = list(dict.fromkeys(sources))[:k]
    relevant = {d: g for d, g in graded_docs.items() if g > 0}
    dcg = sum(relevant[d] / math.log2(rank + 1) for rank, d in enumerate(top, start=1) if d in relevant)
    ideal = sorted(relevant.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(rank + 1) for rank, g in enumerate(ideal, start=1))
    ndcg = dcg / idcg if idcg > 0 else 0.0
    recall = sum(1 for d in top if d in relevant) / len(relevant) if relevant else 0.0
    return ndcg, recall


def l1_metrics(doc: dict) -> dict:
    """Layer 1 metrics per path from an L1 document's queries and rows."""
    M = project_metrics()
    queries = doc["queries"]
    state = (doc.get("meta") or {}).get("state")
    out = {}
    for path, by_qid in rows_by_path(doc["rows"], queries).items():
        per_query = {}
        acc = {k: [] for k in ("rr", "ndcg5", "hit1", "hit5", "p5", "rr_na", "ndcg5_na", "hit5_na",
                               "graded", "support", "ndcg10", "recall10", "latency", "tokens")}
        adv_n = leaks = n_results = n_multi = 0
        for q in queries:
            row = by_qid[q["qid"]]
            results = row["results"]
            sources = [r["source"] for r in results]
            gold = set(q["gold_sources"])
            adv = is_adversarial(q)
            rr = float(M.calculate_reciprocal_rank(sources[:5], gold))
            ndcg5 = float(M.calculate_ndcg(sources, gold, 5))
            hit1 = float(M.calculate_hit_rate(sources, gold, 1))
            hit5 = float(M.calculate_hit_rate(sources, gold, 5))
            p5 = float(M.calculate_precision_at_k(sources, gold, 5))
            graded = None
            if q.get("graded_chunks"):
                chunk_ids = [f"{r['source']}:{r['chunk_index']}" for r in results]
                graded = float(M.calculate_ndcg_graded(chunk_ids, q["graded_chunks"], 5))
            support = None
            if q.get("supporting") is not None:
                support = 1.0 if set(q["supporting"]) <= set(sources[:5]) else 0.0
            ndcg10 = recall10 = None
            if q.get("graded_docs") is not None:
                ndcg10, recall10 = beir_ndcg_recall(sources, q["graded_docs"], 10)
            leak = None
            if adv:
                adv_n += 1
                leak = 1 if results else 0
                leaks += leak
            latency = float(row["latency_ms"])
            tokens = sum(len(r["text"]) for r in results) // 4
            n_results += len(results)
            n_multi += sum(1 for r in results if (r.get("n_matches") or 0) >= 2)
            for key, value in (("rr", rr), ("ndcg5", ndcg5), ("hit1", hit1), ("hit5", hit5), ("p5", p5),
                               ("latency", latency), ("tokens", tokens)):
                acc[key].append(value)
            if not adv:
                acc["rr_na"].append(rr)
                acc["ndcg5_na"].append(ndcg5)
                acc["hit5_na"].append(hit5)
            for key, value in (("graded", graded), ("support", support), ("ndcg10", ndcg10),
                               ("recall10", recall10)):
                if value is not None:
                    acc[key].append(value)
            per_query[q["qid"]] = {
                "rr": rr, "ndcg5": ndcg5, "hit1": hit1, "hit5": hit5, "p5": p5,
                "graded_ndcg5": graded, "support_all5": support, "ndcg10": ndcg10,
                "recall10": recall10, "leak": leak, "latency_ms": latency,
            }
        out[path] = {
            "n": len(queries),
            "mrr_5": _mean(acc["rr"]),
            "ndcg_5": _mean(acc["ndcg5"]),
            "hit_1": _mean(acc["hit1"]),
            "hit_5": _mean(acc["hit5"]),
            "p_5": _mean(acc["p5"]),
            "mrr_5_nonadv": _mean(acc["rr_na"]),
            "ndcg_5_nonadv": _mean(acc["ndcg5_na"]),
            "hit_5_nonadv": _mean(acc["hit5_na"]),
            "graded_ndcg_5": _mean(acc["graded"]),
            "support_all_5": _mean(acc["support"]),
            "ndcg_10": _mean(acc["ndcg10"]),
            "recall_10": _mean(acc["recall10"]),
            "adv_n": adv_n,
            "adv_leak_count": leaks,
            "latency_p50_ms": _percentile(acc["latency"], 50),
            "latency_p95_ms": _percentile(acc["latency"], 95),
            "fulltext_tokens_mean": _mean(acc["tokens"]),
            "multi_match_freq": (n_multi / n_results) if state == "C" and n_results else None,
            "per_query": per_query,
        }
    return out


def l2_metrics(doc: dict, gold: GoldText | None = None, gold_body: str | None = None) -> dict:
    """Layer 2 metrics per path, computed from each row's raw tool output alone.
    gold_body overrides the CEN-G gold body recorded in the file's meta."""
    M = project_metrics()
    queries = doc["queries"]
    gold = gold or GoldText.for_meta(doc.get("meta") or {}, gold_body)
    out = {}
    for path, by_qid in rows_by_path(doc["rows"], queries).items():
        per_query = {}
        acc = {k: [] for k in ("srcvis", "gpv", "gpc", "sv", "goldtext", "goldshare", "chars",
                               "adv_chars", "latency")}
        errors = leaks = 0
        for q in queries:
            row = by_qid[q["qid"]]
            raw = row.get("raw_output") or ""
            errors += 1 if row.get("error") is not None else 0
            blocks = parse_output(raw)
            sources = [b["source"] for b in blocks]
            gold_set = set(q["gold_sources"])
            adv = is_adversarial(q)
            norm = normalise(raw)
            srcvis = float(M.calculate_hit_rate(sources, gold_set, 5))
            gpv = gpc = None
            if q.get("graded_chunks") is not None and not adv:
                sets = gold.gold_chunk_shingle_sets(q["graded_chunks"])
                if sets:
                    gpv = 1.0 if any(s in norm for chunk in sets for s in chunk) else 0.0
                    gpc = sum(sum(1 for s in chunk if s in norm) / len(chunk) for chunk in sets) / len(sets)
            support = None
            if q.get("supporting") is not None:
                support = 1.0 if all(any(s in norm for s in gold.doc_shingles(d))
                                     for d in q["supporting"]) else 0.0
            goldtext = goldshare = None
            if not adv:
                union: set = set()
                for d in q["gold_sources"]:
                    union |= gold.doc_shingles(d)
                goldtext = sum(1 for s in union if s in norm)
                if blocks:
                    total = sum(len(b["body"]) for b in blocks)
                    inside = sum(len(b["body"]) for b in blocks if b["source"] in gold_set)
                    goldshare = inside / total if total else 0.0
            leak = None
            if adv:
                leak = 1 if blocks else 0
                leaks += leak
                acc["adv_chars"].append(len(raw))
            latency = float(row["latency_ms"])
            acc["srcvis"].append(srcvis)
            acc["chars"].append(len(raw))
            acc["latency"].append(latency)
            for key, value in (("gpv", gpv), ("gpc", gpc), ("sv", support), ("goldtext", goldtext),
                               ("goldshare", goldshare)):
                if value is not None:
                    acc[key].append(value)
            per_query[q["qid"]] = {
                "srcvis": srcvis, "gpv": gpv, "gpc": gpc, "support_visible": support,
                "goldtext": goldtext, "goldshare": goldshare, "chars": len(raw), "leak": leak,
                "latency_ms": latency,
            }
        out[path] = {
            "n": len(queries),
            "errors": errors,
            "srcvis_5": _mean(acc["srcvis"]),
            "gpv": _mean(acc["gpv"]),
            "gpv_n": len(acc["gpv"]),
            "gpc": _mean(acc["gpc"]),
            "support_visible": _mean(acc["sv"]),
            "goldtext_mean": _mean(acc["goldtext"]),
            "goldshare_mean": _mean(acc["goldshare"]),
            "chars_mean": _mean(acc["chars"]),
            "chars_p95": _percentile(acc["chars"], 95),
            "adv_chars_mean": _mean(acc["adv_chars"]),
            "adv_leak_count": leaks,
            "latency_p50_ms": _percentile(acc["latency"], 50),
            "latency_p95_ms": _percentile(acc["latency"], 95),
            "per_query": per_query,
        }
    return out


def compare_metrics(stored: dict, recomputed: dict, tol: float = 0.0) -> list[str]:
    """Differences between two metrics trees (exact by default)."""
    diffs = []

    def walk(a, b, where):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                if k not in a or k not in b:
                    diffs.append(f"{where}/{k}: present in only one")
                else:
                    walk(a[k], b[k], f"{where}/{k}")
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
            if abs(a - b) > tol or (tol == 0.0 and a != b):
                diffs.append(f"{where}: {a!r} != {b!r}")
        elif a != b:
            diffs.append(f"{where}: {a!r} != {b!r}")

    walk(stored, recomputed, "")
    return diffs


# ── Provenance and files ─────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def harness_hashes(*names: str) -> dict:
    return {n: sha256_file(HARNESS_DIR / n) for n in ("common.py", *names)}


def git(checkout: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(checkout), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


PROVENANCE_PATHS = ("src", "pyproject.toml")       # what decides the code a state runs
PROVENANCE_KEYS = ("git_sha", "src_tree_sha", "pyproject_sha", "status_porcelain", "dotenv_present")
CODE_KEYS = ("src_tree_sha", "pyproject_sha")      # outputs of one state must agree on these


def git_provenance(checkout: Path) -> dict:
    """Code provenance of a checkout: HEAD, HEAD:src, HEAD:pyproject.toml, the
    porcelain status of src/ and pyproject.toml, and whether <checkout>/.env exists
    (candlekeep's config.load_dotenv reads it into every process that imports
    candlekeep)."""
    checkout = Path(checkout)
    status = git(checkout, "status", "--porcelain", "--", *PROVENANCE_PATHS)
    try:
        pyproject_sha = git(checkout, "rev-parse", "HEAD:pyproject.toml")
    except subprocess.CalledProcessError:
        pyproject_sha = None
    return {
        "git_sha": git(checkout, "rev-parse", "HEAD"),
        "src_tree_sha": git(checkout, "rev-parse", "HEAD:src"),
        "pyproject_sha": pyproject_sha,
        "src_dirty": bool(git(checkout, "status", "--porcelain", "--", "src")),
        "status_porcelain": status.splitlines(),
        "dotenv_present": (checkout / ".env").exists(),
        "checkout": str(checkout),
        "captured_at": now_iso(),
    }


def provenance_problems(prov: dict) -> list[str]:
    """Reasons a checkout must not be used for a protocol step (empty when clean)."""
    problems = []
    if prov.get("status_porcelain"):
        problems.append(f"uncommitted changes under {' / '.join(PROVENANCE_PATHS)} in {prov.get('checkout')}: "
                        + "; ".join(prov["status_porcelain"][:10]))
    if prov.get("dotenv_present"):
        problems.append(f"{prov.get('checkout')}/.env exists (config.load_dotenv would load it)")
    return problems


def provenance_changes(before: dict, after: dict) -> list[str]:
    """Differences between two provenance captures of the same checkout."""
    return [f"{k}: {before.get(k)!r} -> {after.get(k)!r}" for k in PROVENANCE_KEYS if before.get(k) != after.get(k)]


def provenance_meta(prov: dict, prefix: str = "") -> dict:
    """The provenance fields that go into a result file's meta."""
    return {f"{prefix}{k}": prov.get(k) for k in ("git_sha", "src_tree_sha", "pyproject_sha", "src_dirty",
                                                   "status_porcelain", "dotenv_present", "captured_at")}


def code_mismatch(meta: dict, prov: dict) -> str | None:
    """Why an output's meta was not computed with the checkout's current code."""
    for key in CODE_KEYS:
        if (meta or {}).get(key) != prov.get(key):
            return f"{key} {(meta or {}).get(key)!r}, checkout now {prov.get(key)!r}"
    return None


def state_outputs(state: str) -> list[tuple[Path, dict | None, str | None]]:
    """[(path, meta, error)] of every L1/L2 file whose meta names this state;
    unreadable files are included with their error (fail closed)."""
    out = []
    for layer in ("L1", "L2"):
        d = CONFIG.results_root / layer
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                meta = read_meta(p)
            except Exception as e:
                out.append((p, None, f"unreadable: {type(e).__name__}: {e}"))
                continue
            if (meta or {}).get("state") == state:
                out.append((p, meta, None))
    return out


def installed_packages() -> dict:
    """{distribution: version} of the running interpreter."""
    import importlib.metadata as md
    out: dict = {}
    for dist in md.distributions():
        name = dist.metadata["Name"]
        if name and name not in out:
            out[name] = dist.version
    return dict(sorted(out.items(), key=lambda kv: kv[0].lower()))


_PACKAGES_SNIPPET = (
    "import importlib.metadata as md, json\n"
    "out = {}\n"
    "for dist in md.distributions():\n"
    "    name = dist.metadata['Name']\n"
    "    if name and name not in out:\n"
    "        out[name] = dist.version\n"
    "print(json.dumps(dict(sorted(out.items(), key=lambda kv: kv[0].lower()))))\n"
)


def packages_of(python: Path) -> dict:
    """{distribution: version} of another interpreter."""
    res = subprocess.run([str(python), "-I", "-c", _PACKAGES_SNIPPET], capture_output=True, text=True,
                         check=True, env=base_env())
    return json.loads(res.stdout)


def reexec_with_hash_seed() -> None:
    """Re-run the current script with PYTHONHASHSEED=HASH_SEED unless already set.

    String hashing decides set iteration order, and some product code iterates
    over sets of strings; a fixed seed makes repeated runs and the A/B/C states
    use the same order. Must be called before any heavy import."""
    if os.environ.get("PYTHONHASHSEED") != HASH_SEED:
        os.execve(sys.executable, [sys.executable, *sys.argv], {**os.environ, "PYTHONHASHSEED": HASH_SEED})


def same_prefix(venv: Path) -> bool:
    return Path(sys.prefix).resolve() == Path(venv).resolve()


def require_interpreter(state: StateDef) -> None:
    if not same_prefix(state.venv):
        raise SystemExit(f"run this with {state.python} (state {state.name}); running {sys.executable}")


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False)


def write_json_atomic(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dumps(obj))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


_META_HEAD_RE = re.compile(r'\A\s*\{\s*"meta"\s*:\s*')


def read_meta(path: Path, head_bytes: int = 1 << 20) -> dict | None:
    """The "meta" object of an L1/L2 file without parsing the whole file when the
    file starts with it (as write_json_atomic writes them); else a full parse."""
    with open(path, "rb") as f:
        head = f.read(head_bytes).decode("utf-8", errors="ignore")
    m = _META_HEAD_RE.match(head)
    if m:
        try:
            meta, _ = json.JSONDecoder().raw_decode(head, m.end())
            if isinstance(meta, dict):
                return meta
        except ValueError:
            pass
    doc = load_json(path)
    return doc.get("meta") if isinstance(doc, dict) else None


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def move_preserving(paths: list, dest_root: Path) -> list[str]:
    """Move files under results_root to dest_root/<same relative path>."""
    moved = []
    for p in paths:
        p = Path(p)
        rel = p.relative_to(CONFIG.results_root) if p.is_relative_to(CONFIG.results_root) else Path(p.name)
        dst = dest_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(p, dst)
        moved.append(str(rel))
    return moved


def invalid_path(out: Path) -> Path:
    """Where an output that must not be used is kept: <results_root>/invalid/<rel>.<stamp>.json."""
    out = Path(out)
    rel = out.relative_to(CONFIG.results_root) if out.is_relative_to(CONFIG.results_root) else Path(out.name)
    return CONFIG.results_root / "invalid" / rel.parent / f"{rel.stem}.{utc_stamp()}{rel.suffix}"


def quarantine(out: Path, reason: str) -> Path:
    """Move an output out of L1/ or L2/ (so no step uses or skips on it) into invalid/,
    with the reason next to it."""
    dst = invalid_path(out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.replace(out, dst)
    dst.with_suffix(".reason.txt").write_text(reason + "\n", encoding="utf-8")
    return dst


# ── Ingest identity ──────────────────────────────────────────────────────────
#
# Chunk ids are deterministic, so the collection fingerprint cannot tell two
# ingests of the same corpus apart, while their HNSW graphs differ. Every ingest
# therefore gets a uuid4 (ingest_uuid) that is written to the ingest record and
# to <data_root>/<I0x>/ingest_marker.json; every L1/L2 output records the uuid and
# the record's SHA-256, and no step mixes outputs of different ingests.

class IngestError(RuntimeError):
    pass


IDENTITY_KEYS = ("ingest_uuid", "ingest_record_sha256")


def ingest_marker_path(corpus: CorpusDef) -> Path:
    return corpus_root(corpus) / "ingest_marker.json"


def failed_record_path(corpus: CorpusDef) -> Path:
    path = ingest_record_path(corpus)
    return path.with_name(path.stem + ".failed.json")


def current_ingest(corpus: CorpusDef) -> tuple[dict, dict]:
    """(record, identity) of the corpus's current successful ingest. The identity is
    {ingest_id, ingest_uuid, ingest_record, ingest_record_sha256}. Raises IngestError
    if the record is missing, failed, has no uuid, or the data directory's marker
    names a different ingest."""
    path = ingest_record_path(corpus)
    if not path.is_file():
        raise IngestError(f"{corpus.id}: no ingest record at {path}")
    record = load_json(path)
    if not record.get("ok"):
        raise IngestError(f"{path} records a failed ingest")
    ingest_uuid = record.get("ingest_uuid")
    if not ingest_uuid:
        raise IngestError(f"{path} has no ingest_uuid (written by an older harness): re-ingest {corpus.id}")
    marker_path = ingest_marker_path(corpus)
    marker = load_json(marker_path) if marker_path.is_file() else None
    if not marker or marker.get("ingest_uuid") != ingest_uuid:
        raise IngestError(f"{corpus_root(corpus)} does not hold the ingest recorded in {path} "
                          f"(record {ingest_uuid}, data-directory marker "
                          f"{marker.get('ingest_uuid') if marker else 'missing'})")
    identity = {"ingest_id": record.get("ingest_id"), "ingest_uuid": ingest_uuid,
                "ingest_record": str(path), "ingest_record_sha256": sha256_file(path)}
    return record, identity


def identity_mismatch(meta: dict, identity: dict) -> str | None:
    """Why an output's meta does not belong to the given ingest (None if it does)."""
    for key in IDENTITY_KEYS:
        if (meta or {}).get(key) != identity.get(key):
            return f"{key} {(meta or {}).get(key)!r}, current ingest {identity.get(key)!r}"
    return None


def corpus_outputs(corpus_id: str) -> list[tuple[Path, dict | None, str | None]]:
    """[(path, meta, error)] of every L1/L2 file (tagged and informational included)
    whose meta names this corpus. Unreadable files are included with their error,
    whatever corpus they belong to (fail closed)."""
    out = []
    for layer in ("L1", "L2"):
        d = CONFIG.results_root / layer
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                meta = read_meta(p)
            except Exception as e:  # unreadable: cannot tell its corpus
                out.append((p, None, f"unreadable: {type(e).__name__}: {e}"))
                continue
            if (meta or {}).get("corpus") == corpus_id:
                out.append((p, meta, None))
    return out


def stale_outputs(corpus: CorpusDef, identity: dict, exclude: Path | None = None) -> list[str]:
    """Outputs of this corpus that were not computed on the given ingest."""
    stale = []
    for p, meta, error in corpus_outputs(corpus.id):
        if exclude is not None and Path(p).resolve() == Path(exclude).resolve():
            continue
        why = error or identity_mismatch(meta, identity)
        if why:
            stale.append(f"{p}: {why}")
    return stale


def corpus_dependents(corpus: CorpusDef) -> list[Path]:
    """Files computed on the corpus's current ingest: its L1/L2 outputs and, for the
    corpus that serves the CEN suite, the judge packs (built from L2/<S>_CEN.json).
    Raises IngestError if an L1/L2 file is unreadable (its corpus is unknown)."""
    outputs = corpus_outputs(corpus.id)
    unreadable = [f"{p}: {error}" for p, _, error in outputs if error]
    if unreadable:
        raise IngestError("cannot tell which corpus these outputs belong to: " + "; ".join(unreadable))
    deps = [p for p, _, _ in outputs]
    if "CEN" in suites_of_corpus(corpus.id):
        jd = CONFIG.results_root / "judges"
        if jd.is_dir():
            deps += sorted(p for p in jd.iterdir() if p.is_file())
    return deps


# ── Chroma servers started by drive.py (pid files) ───────────────────────────

def chroma_pidfile(corpus: CorpusDef) -> Path:
    return CONFIG.run_root / f"chroma_{corpus.id}.json"


def _live_chroma_record(corpus: CorpusDef) -> dict | None:
    """The pid-file record of the corpus's Chroma server if its process is alive and
    runs `chroma run` with the recorded path and port; None otherwise. Read-only."""
    pf = chroma_pidfile(corpus)
    if not pf.is_file():
        return None
    info = load_json(pf)
    cmd = pid_command(info["pid"]) if pid_alive(info["pid"]) else ""
    if "chroma" in cmd and info["path"] in cmd and f"--port {info['port']}" in cmd:
        return info
    return None


def our_chroma(corpus: CorpusDef) -> dict | None:
    """The pid-file record of a live Chroma server drive.py started for this corpus
    (a stale pid file is removed)."""
    info = _live_chroma_record(corpus)
    if info is None:
        chroma_pidfile(corpus).unlink(missing_ok=True)
    return info


# ── Chroma process identity (protocol section 16) ────────────────────────────
#
# One Chroma server process per corpus serves every L1/L2 run on that corpus
# (Chroma rebuilds part of the HNSW graph whenever it loads a collection, so runs
# against different processes are not comparable). Its identity is the pid, the
# process start time as `ps -o lstart=` prints it, and the port. drive.py captures
# it before a run starts and passes it to the run as JSON in CK_EVAL_CHROMA_PROCESS;
# the run stores it in meta.chroma_process, captures it again at its end
# (meta.chroma_process_end) and is invalid if the two differ. drive.py checks once
# more after the run (L2: after the server) has stopped.

CHROMA_PROCESS_ENV = "CK_EVAL_CHROMA_PROCESS"
CHROMA_PROCESS_KEYS = ("pid", "started", "port")
# ps runs with this fixed environment so that every capture of one process prints
# the same start-time string, whatever the caller's locale or time zone (C locale, UTC).
_PS_ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C", "LANG": "C", "TZ": "UTC"}


def process_started(pid: int) -> str | None:
    """Start time of a process from `ps -o lstart= -p <pid>`; None if it is not running."""
    res = subprocess.run(["ps", "-o", "lstart=", "-p", str(int(pid))], capture_output=True, text=True,
                         env=_PS_ENV)
    return res.stdout.strip() or None


def chroma_process(corpus: CorpusDef) -> dict | None:
    """Identity {pid, started, port} of the Chroma server drive.py started for this
    corpus (pid file, live `chroma run` process on the corpus's port, heartbeat
    answered); None when no such server is running. Never modifies the pid file."""
    info = _live_chroma_record(corpus)
    if info is None or int(info["port"]) != corpus.chroma_port:
        return None
    if not http_ok(chroma_heartbeat_url(corpus.chroma_port)):
        return None
    started = process_started(info["pid"])
    if started is None:
        return None
    return {"pid": int(info["pid"]), "started": started, "port": int(info["port"])}


def parse_chroma_process(value) -> dict:
    """A {pid, started, port} identity from JSON text or a dict; raises ValueError."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as e:
            raise ValueError(f"Chroma process identity is not JSON: {value!r}") from e
    if (not isinstance(value, dict) or set(value) != set(CHROMA_PROCESS_KEYS)
            or not isinstance(value["pid"], int) or isinstance(value["pid"], bool)
            or not isinstance(value["port"], int) or isinstance(value["port"], bool)
            or not isinstance(value["started"], str) or not value["started"]):
        raise ValueError(f"not a Chroma process identity {{pid: int, started: str, port: int}}: {value!r}")
    return {"pid": value["pid"], "started": value["started"], "port": value["port"]}


def chroma_process_for_run(corpus: CorpusDef, script: str) -> tuple[dict, str]:
    """(identity, source) at the start of an L1/L2 run: the identity drive.py passed in
    CK_EVAL_CHROMA_PROCESS, else the one running now. Raises SystemExit if no Chroma
    server of ours serves the corpus, or if it is not the process drive.py captured."""
    raw = os.environ.get(CHROMA_PROCESS_ENV)
    now = chroma_process(corpus)
    if raw:
        try:
            given = parse_chroma_process(raw)
        except ValueError as e:
            raise SystemExit(f"{CHROMA_PROCESS_ENV}: {e}")
        if now != given:
            raise SystemExit(f"the Chroma server of {corpus.id} is not the process drive.py captured before "
                             f"the run: {given} -> {now}")
        return given, "captured by drive.py before the run started"
    if now is None:
        raise SystemExit(f"no Chroma server of ours runs for {corpus.id} on port {corpus.chroma_port}: start it with "
                         f"`drive.py chroma-up --corpus {corpus.id}` (every run records the server's process identity)")
    return now, f"captured by {script} at its start (not passed by drive.py)"


def chroma_process_mismatch(meta: dict, process: dict) -> str | None:
    """Why an output's meta was not computed against this Chroma process (None if it was)."""
    recorded = (meta or {}).get("chroma_process")
    if recorded != process:
        return f"chroma_process {recorded!r}, running {process!r}"
    return None


def other_chroma_outputs(corpus: CorpusDef, process: dict, exclude: Path | None = None) -> list[str]:
    """Outputs of this corpus (tagged and informational included) that were not
    computed against this Chroma process, or that cannot be read (fail closed)."""
    bad = []
    for p, meta, error in corpus_outputs(corpus.id):
        if exclude is not None and Path(p).resolve() == Path(exclude).resolve():
            continue
        why = error or chroma_process_mismatch(meta, process)
        if why:
            bad.append(f"{p}: {why}")
    return bad


# ── Processes, ports, servers ────────────────────────────────────────────────

def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def wait_for(pred, timeout: float, interval: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return pred()


def base_env() -> dict:
    """Minimal environment for every child process: nothing from the caller's
    CANDLEKEEP_*, CHROMA_*, FASTMCP_* or PYTHON* variables leaks in."""
    env = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE")
           if k in os.environ}
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    env["ANONYMIZED_TELEMETRY"] = "False"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def candlekeep_server_env(corpus: CorpusDef, data_dir: Path, port: int, overrides: dict | None = None) -> dict:
    """Environment of a candlekeep HTTP server on a corpus (ingest and Layer 2)."""
    env = base_env()
    env.update({
        "CHROMA_URL": chroma_url(corpus),
        "CANDLEKEEP_DATA_DIR": str(data_dir),
        "CANDLEKEEP_TRANSPORT": "http",
        "CANDLEKEEP_HTTP_HOST": "127.0.0.1",
        "CANDLEKEEP_HTTP_PORT": str(port),
        "CANDLEKEEP_DEVICE": DEVICE,
        "CANDLEKEEP_RATE_LIMIT_SEARCH": "0",
        "CANDLEKEEP_RATE_LIMIT_WRITE": "0",
        "CANDLEKEEP_CHUNK_OVERLAP": str(corpus.chunk_overlap),
        "PYTHONHASHSEED": HASH_SEED,
    })
    env.update({k: str(v) for k, v in (overrides or {}).items()})
    return env


def spawn(cmd: list, env: dict, log_path: Path, cwd: Path) -> subprocess.Popen:
    """Start a detached process (own session) logging stdout+stderr to log_path."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    Path(cwd).mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as log:
        log.write(f"\n===== {now_iso()} start: {' '.join(map(str, cmd))}\n".encode())
        log.flush()
        return subprocess.Popen([str(c) for c in cmd], env=env, cwd=str(cwd), stdout=log,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # a zombie child counts as gone
        done, _ = os.waitpid(pid, os.WNOHANG)
        return done == 0
    except ChildProcessError:
        return True


def pid_command(pid: int) -> str:
    res = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True)
    return res.stdout.strip()


def _signal_group(pid: int, sig: int) -> None:
    """Signal the process group led by pid (we start servers as session leaders),
    or only pid if it does not lead its own group."""
    try:
        if os.getpgid(pid) == pid:
            os.killpg(pid, sig)
        else:
            os.kill(pid, sig)
    except ProcessLookupError:
        pass


def stop_pid(pid: int, timeout: float = 120.0) -> None:
    """Stop a process we started earlier (known only by pid): SIGTERM, then SIGKILL."""
    if not pid_alive(pid):
        return
    _signal_group(pid, signal.SIGTERM)
    if wait_for(lambda: not pid_alive(pid), timeout, 0.25):
        return
    _signal_group(pid, signal.SIGKILL)
    wait_for(lambda: not pid_alive(pid), 15, 0.25)


def stop_process(proc: subprocess.Popen, timeout: float = 120.0, sig: int = signal.SIGTERM) -> int | None:
    """Stop a child process started by spawn(): send sig to its group, then SIGKILL.

    Candlekeep servers are stopped with SIGINT: uvicorn shuts down gracefully and
    re-raises the signal with the original handler, which for SIGINT ends the
    interpreter normally, so non-daemon background threads (normalisation map,
    graph rebuild) finish. Re-raised SIGTERM would kill them mid-write."""
    if proc.poll() is None:
        _signal_group(proc.pid, sig)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _signal_group(proc.pid, signal.SIGKILL)
            proc.wait(timeout=15)
    return proc.returncode


def chroma_heartbeat_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/v2/heartbeat"


def chroma_cli() -> Path:
    return VENV_B / "bin" / "chroma"


def start_chroma(path: Path, port: int, log_path: Path, timeout: float = 180.0) -> subprocess.Popen:
    """Start venv B's Chroma server on 127.0.0.1:port with the given data path."""
    if port_in_use(port):
        raise RuntimeError(f"port {port} is already in use; refusing to start Chroma there")
    path.mkdir(parents=True, exist_ok=True)
    cmd = [chroma_cli(), "run", "--path", path, "--host", "127.0.0.1", "--port", str(port)]
    proc = spawn(cmd, base_env(), log_path, cwd=path.parent)
    if not wait_for(lambda: proc.poll() is not None or http_ok(chroma_heartbeat_url(port)), timeout) \
            or proc.poll() is not None:
        stop_process(proc)
        raise RuntimeError(f"Chroma did not come up on port {port}; see {log_path}")
    return proc


def wait_server_port(proc: subprocess.Popen, port: int, timeout: float = 300.0) -> None:
    """Wait until a server we started listens on port (or fail if it exited)."""
    if not wait_for(lambda: proc.poll() is not None or port_in_use(port), timeout) or proc.poll() is not None:
        raise RuntimeError(f"server on port {port} did not start (exit code {proc.poll()})")


def chroma_version() -> str:
    res = subprocess.run([str(VENV_B / "bin" / "python"), "-c",
                          "import importlib.metadata as m; print(m.version('chromadb'))"],
                         capture_output=True, text=True)
    return res.stdout.strip()


def mcp_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/mcp"


# ── MCP client helpers (fastmcp from venv B) ─────────────────────────────────

async def mcp_text(client, tool: str, args: dict | None = None, timeout: float | None = None):
    """(text content, is_error) of one tool call, exactly as the agent receives it."""
    res = await client.call_tool_mcp(tool, args or {}, timeout=timeout)
    texts = [c.text for c in (res.content or []) if getattr(c, "type", None) == "text"]
    return "".join(texts), bool(getattr(res, "isError", False))


class ServerNotUsable(RuntimeError):
    """get_stats answered, but with candlekeep's database-failure message."""


async def mcp_wait_ready(client, timeout: float = 900.0, interval: float = 2.0) -> str:
    """Poll get_stats until the server no longer reports loading; return its text."""
    deadline = time.monotonic() + timeout
    while True:
        text, is_error = await mcp_text(client, "get_stats", {}, timeout=600)
        if not is_error and not text.startswith("⏳"):
            if text.startswith("❌"):
                raise ServerNotUsable(f"server is not usable: {text}")
            return text
        if time.monotonic() > deadline:
            raise TimeoutError(f"server not ready after {timeout:.0f}s: {text[:200]}")
        await asyncio.sleep(interval)


async def _wait_ready_url(url: str, timeout: float) -> str:
    from urllib.parse import urlparse

    from fastmcp import Client
    deadline = time.monotonic() + timeout
    port = urlparse(url).port
    while port and not port_in_use(port):
        if time.monotonic() > deadline:
            raise TimeoutError(f"nothing listens on {url}")
        await asyncio.sleep(1.0)
    last = None
    while time.monotonic() < deadline:
        try:
            async with Client(url, timeout=600) as client:
                return await mcp_wait_ready(client, max(1.0, deadline - time.monotonic()))
        except (TimeoutError, ServerNotUsable):
            raise
        except Exception as e:  # session setup failed while the server starts
            last = e
            await asyncio.sleep(2.0)
    raise TimeoutError(f"no MCP session at {url}: {last}")


def wait_ready(url: str, timeout: float = 900.0) -> str:
    return asyncio.run(_wait_ready_url(url, timeout))


def collection_fingerprint(port: int) -> dict:
    """Count and sha256 of the sorted chunk ids of the 'candlekeep' collection."""
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    client = chromadb.HttpClient(host="127.0.0.1", port=port,
                                 settings=ChromaSettings(anonymized_telemetry=False))
    col = client.get_collection("candlekeep")
    ids: list = []
    offset, page_size = 0, 5000
    while True:
        page = col.get(include=[], limit=page_size, offset=offset)
        ids.extend(page["ids"])
        if len(page["ids"]) < page_size:
            break
        offset += len(page["ids"])
    return {"count": len(ids), "ids_sha256": hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()}


# ── Pre-flight check ─────────────────────────────────────────────────────────

def preflight() -> dict:
    """Counts and consistency checks over suites, corpora and CEN-G gold chunks.
    Never raises: every problem is reported under "errors"."""
    report: dict = {"generated_at": now_iso(), "suites": {}, "corpora": {}, "cen_g": {}, "errors": []}

    def guard(label, fn):
        try:
            fn()
        except Exception as e:
            report["errors"].append(f"{label}: {type(e).__name__}: {e}")

    def corpus_check(cid):
        corpus = CORPORA[cid]
        info: dict = {"kind": corpus.kind, "expected_docs": corpus.n_docs}
        if corpus.kind == "beir":
            ids = [i for i, _, _ in iter_beir_corpus(corpus.beir_dir)]
            info["corpus_jsonl_docs"] = len(ids)
            staged = corpus.ingest_dirs()[0]
            info["staged_dir"] = str(staged)
            info["staged_files"] = len(list(staged.glob("*.md"))) if staged.is_dir() else None
        else:
            index, collisions = corpus_file_index(corpus.ingest_dirs())
            info["files"] = len(index)
            info["basename_collisions"] = collisions
            info["ingest_path"] = str(corpus.ingest_path())
            if corpus.kind == "links":  # one symlink per file, staged by ingest.py
                staged = corpus.ingest_path()
                info["staged_links"] = (sum(1 for p in staged.iterdir() if p.is_symlink())
                                        if staged.is_dir() else None)
            mismatches = []

            def frontmatter_consistency():
                # Files whose frontmatter is not valid YAML: the product keeps the
                # frontmatter in the chunked body (no Bardic prefix), while the
                # gold-document text strips it with the regex.
                proc = product_processor(512, corpus.chunk_overlap)
                for name, path in index.items():
                    text = read_doc(path)
                    if proc._parse_frontmatter(text)[1] != strip_frontmatter(text):
                        mismatches.append(name)
                info["frontmatter_kept_by_product"] = mismatches

            guard(f"corpus {cid} frontmatter", frontmatter_consistency)
            empty = [n for n in index if not normalise(strip_frontmatter(read_doc(index[n])))]
            info["empty_normalised_docs"] = empty
        report["corpora"][cid] = info

    def suite_check(name):
        suite = SUITES[name]
        corpus = CORPORA[suite.corpus]
        info: dict = {"corpus": suite.corpus, "expected_n": suite.expected_n}
        try:
            recs = load_queries(suite)
        except ValueError as e:
            report["errors"].append(f"suite {name}: {e}")
            return
        info["n"] = len(recs)
        cats: dict = {}
        for r in recs:
            cats[r["category"]] = cats.get(r["category"], 0) + 1
        info["categories"] = cats
        if corpus.kind == "beir":
            present = {f"{i}.md" for i, _, _ in iter_beir_corpus(corpus.beir_dir)}
        else:
            present = set(corpus_file_index(corpus.ingest_dirs())[0])
        gold = [g for r in recs for g in r["gold_sources"]]
        missing = [(r["qid"], g) for r in recs for g in r["gold_sources"] if g not in present]
        info["gold_refs"] = len(gold)
        info["gold_refs_missing_from_corpus"] = len(missing)
        info["gold_missing_examples"] = missing[:10]
        if any(r["supporting"] is not None for r in recs):
            sup = [(r["qid"], d) for r in recs for d in (r["supporting"] or []) if d not in present]
            info["supporting_refs"] = sum(len(r["supporting"] or []) for r in recs)
            info["supporting_missing"] = sup
        report["suites"][name] = info

    def cen_g_check():
        recs = load_queries("CEN-G")
        corpus = CORPORA[SUITES["CEN-G"].corpus]
        index, _ = corpus_file_index(corpus.ingest_dirs())
        golds = {mode: GoldText(corpus.ingest_dirs(), gold_body=mode) for mode in GOLD_BODIES}
        by_mode = {}
        for mode, gold in golds.items():
            keys = missing_doc = out_of_range = g2 = g2_missing = empty_chunks = gpv_queries = 0
            examples = []
            for r in recs:
                has_gold = False
                for key, grade in (r["graded_chunks"] or {}).items():
                    keys += 1
                    name, idx = key.rsplit(":", 1)
                    idx = int(idx)
                    chunks = gold.overlap50_chunks(name)
                    ok = chunks is not None and idx < len(chunks)
                    if chunks is None:
                        missing_doc += 1
                    elif not ok:
                        out_of_range += 1
                        if len(examples) < 10:
                            examples.append(f"{r['qid']} {key} (doc has {len(chunks)} chunks)")
                    if grade >= GOLD_CHUNK_GRADE:
                        g2 += 1
                        if not ok:
                            g2_missing += 1
                        elif not shingles(chunks[idx]):
                            empty_chunks += 1
                        elif not is_adversarial(r):
                            has_gold = True
                gpv_queries += 1 if has_gold else 0
            by_mode[mode] = {
                "chunk_body": GOLD_BODY_DESCRIPTIONS[mode],
                "graded_keys": keys, "keys_doc_missing": missing_doc, "keys_index_out_of_range": out_of_range,
                "out_of_range_examples": examples, "gold_keys_grade_ge_2": g2,
                "gold_keys_missing": g2_missing, "gold_chunks_empty_after_normalisation": empty_chunks,
                "nonadv_queries_with_gold_chunk": gpv_queries,
                "nonadv_queries": sum(1 for r in recs if not is_adversarial(r)),
                "corpus_docs_rechunked": len(index),
                "corpus_chunks_total": sum(len(gold.overlap50_chunks(n) or []) for n in index),
            }
        # Where the two bodies give different gold-chunk text (grade >= 2).
        differ, affected = [], set()
        for r in recs:
            for key, grade in (r["graded_chunks"] or {}).items():
                if grade < GOLD_CHUNK_GRADE:
                    continue
                name, idx = key.rsplit(":", 1)
                texts = []
                for gold in golds.values():
                    chunks = gold.overlap50_chunks(name)
                    texts.append(chunks[int(idx)] if chunks is not None and int(idx) < len(chunks) else None)
                if len(set(texts)) > 1:
                    differ.append(f"{r['qid']} {key}")
                    if not is_adversarial(r):
                        affected.add(r["qid"])
        report["cen_g"] = {
            "active_gold_body": CEN_G_GOLD_BODY,
            **by_mode[CEN_G_GOLD_BODY],
            "by_gold_body": by_mode,
            "gold_body_differences": {
                "docs_whose_bodies_differ": sorted(
                    n for n in index if golds["product"].chunk_body(read_doc(index[n]))
                    != golds["contract"].chunk_body(read_doc(index[n]))),
                "gold_chunks_with_different_text": len(differ),
                "gold_chunk_examples": differ[:30],
                "nonadv_queries_affected": sorted(affected),
            },
        }

    for cid in CORPORA:
        guard(f"corpus {cid}", lambda cid=cid: corpus_check(cid))
    for name in SUITES:
        guard(f"suite {name}", lambda name=name: suite_check(name))
    guard("cen_g", cen_g_check)

    def answers_check():
        answers = _query_list(load_json(CEN_ANSWERS))
        cen = _query_list(load_json(SUITES["CEN"].file))
        report["cen_a"] = {
            "n": len(answers),
            "same_queries_as_cen": len(answers) == len(cen) and all(
                a["query"] == c["query"] for a, c in zip(answers, cen)),
            "nonadv_with_answer": sum(1 for a in answers if a.get("category") != "adversarial"
                                      and a.get("reference_answer")),
        }

    guard("cen_a", answers_check)
    return report


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight", help="suite/corpus/gold-chunk consistency report")
    p.add_argument("--out", help="also write the report to this JSON file")
    add_hidden_args(p)
    p = sub.add_parser("wait-ready", help="wait until a candlekeep MCP server is ready")
    p.add_argument("--url", required=True)
    p.add_argument("--timeout", type=float, default=900.0)
    p = sub.add_parser("fingerprint", help="count + id hash of the 'candlekeep' collection")
    p.add_argument("--port", type=int, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "preflight":
        apply_overrides(args)
        report = preflight()
        if args.out:
            write_json_atomic(Path(args.out), report)
        print(dumps(report))
        return 0
    if args.cmd == "wait-ready":
        try:
            print(wait_ready(args.url, args.timeout))
            return 0
        except Exception as e:
            print(f"not ready: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
    if args.cmd == "fingerprint":
        print(json.dumps(collection_fingerprint(args.port)))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
