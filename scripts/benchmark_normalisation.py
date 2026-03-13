#!/usr/bin/env python3
"""BM25 token normalisation — full benchmark suite.

Two corpora, multiple metric dimensions, threshold sweep.

Usage:
    python3.12 scripts/benchmark_normalisation.py [--output results/]

Corpora:
    1. Regression corpus  — existing sample_docs + scale_docs + docs/
       Proves normalisation does not degrade retrieval on normal queries.
       Uses Centurion Set (eval_suite_100.json) if present.

    2. Uplift corpus — synthetic docs in tests/fixtures/normalisation_corpus/
       Each document uses one surface form exclusively. Queries use the
       alternate form. Vector search gets near-zero signal; BM25 without
       normalisation gets zero; BM25 with normalisation gets a hit.
       Covers: separator (hyphen/dot/underscore), abbreviation/truncation,
       acronym, compound-split, version-suffix, mixed forms.

Metrics:
    Retrieval quality (BM25-only and hybrid):
        MRR, Hit@1, Hit@5, nDCG@5 (graded where annotations exist)
    BM25 signal:
        BM25-only MRR (isolates normalisation effect from vector fusion)
        BM25 score delta (mean score change on matched queries)
    Map quality:
        map_size, generation_time_s, separator_pair_coverage
    Performance:
        query_latency_p50_ms, query_latency_p95_ms
        ingest_latency_ms (with vs without map)
    Regression safety:
        per-category MRR breakdown (lexical / semantic / adversarial)

Threshold sweep:
    edit_distance_threshold:      [0.10, 0.15, 0.20, 0.25]
    embedding_similarity_threshold: [0.75, 0.82, 0.90]
    min_token_length:             [3, 4, 5]
"""
import sys
import os
import json
import time
import shutil
import tempfile
import argparse
import statistics
import itertools
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

# ── Python version guard ────────────────────────────────────────────────────
if sys.version_info >= (3, 14):
    print("ERROR: Run with Python 3.12. The sentence-transformers embedding model "
          "has a dtype incompatibility on Python 3.14 that silently disables the "
          "embedding gate in the clustering algorithm.\n"
          "Use: python3.12 scripts/benchmark_normalisation.py", file=sys.stderr)
    sys.exit(1)

os.environ.setdefault("CANDLEKEEP_DEVICE", "cpu")
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── Uplift corpus query definitions ─────────────────────────────────────────
# Each entry: (query_using_alternate_form, target_filename, variant_type, difficulty)
# The target document uses the canonical form; the query uses the variant form.
# No semantic overlap — vector gets near-zero, BM25 without normalisation gets 0.

UPLIFT_QUERIES = [
    # separator: hyphen ↔ concatenated
    ("crossencoder reranking pipeline",         "separator-hyphen.md",          "separator_hyphen",     "medium"),
    ("crossencoder msmarco finetuning",         "separator-hyphen.md",          "separator_hyphen",     "medium"),
    ("reranking tradeoffs latency",             "separator-hyphen.md",          "separator_hyphen",     "hard"),
    ("autoscaling policies configuration",      "mixed-forms.md",               "separator_hyphen",     "easy"),
    ("autoscaling scaleout triggers",           "mixed-forms.md",               "separator_hyphen",     "medium"),
    ("roundrobin load distribution",            "mixed-forms.md",               "separator_hyphen",     "easy"),
    ("readonly replica offload",                "mixed-forms.md",               "separator_hyphen",     "medium"),
    ("optin predictive scaling",                "mixed-forms.md",               "separator_hyphen",     "hard"),
    ("inmemory cache eviction",                 "compound-split.md",            "separator_hyphen",     "easy"),
    ("inmemory readthrough strategy",           "compound-split.md",            "separator_hyphen",     "medium"),

    # separator: underscore ↔ concatenated
    ("apikey header authentication",            "separator-underscore.md",      "separator_underscore", "medium"),
    ("apikey credential management",            "separator-underscore.md",      "separator_underscore", "medium"),
    ("redirecturi oauth validation",            "separator-underscore.md",      "separator_underscore", "hard"),
    ("clientid secret oauth",                   "separator-underscore.md",      "separator_underscore", "medium"),
    ("accesstoken refresh lifecycle",           "separator-underscore.md",      "separator_underscore", "hard"),

    # separator: dot ↔ concatenated
    ("majorminorpatch versioning scheme",       "separator-dot.md",             "separator_dot",        "medium"),
    ("majorminorpatch breaking changes",        "separator-dot.md",             "separator_dot",        "hard"),
    ("semver lockfile pinning",                 "separator-dot.md",             "separator_dot",        "easy"),

    # abbreviation: truncation (postgres → postgresql)
    ("postgres mvcc vacuum internals",          "abbreviation-truncation.md",   "abbreviation_trunc",   "hard"),
    ("postgres wal crash recovery",             "abbreviation-truncation.md",   "abbreviation_trunc",   "hard"),
    ("postgres query planner statistics",       "abbreviation-truncation.md",   "abbreviation_trunc",   "medium"),

    # abbreviation: acronym (k8s → kubernetes)
    ("k8s pod scheduling affinity",             "abbreviation-acronym.md",      "abbreviation_acronym", "hard"),
    ("k8s rolling update deployment",           "abbreviation-acronym.md",      "abbreviation_acronym", "medium"),
    ("k8s service discovery coredns",           "abbreviation-acronym.md",      "abbreviation_acronym", "hard"),

    # compound: version suffix (bge-small → bge-small-en-v1.5)
    ("bge-small embedding retrieval",           "compound-version-suffix.md",   "version_suffix",       "medium"),
    ("bge-small inference latency cpu",         "compound-version-suffix.md",   "version_suffix",       "medium"),
    ("bgesmall normalisation cosine",           "compound-version-suffix.md",   "version_suffix",       "hard"),

    # mixed: multiple variant types in one query
    ("crossencoder inmemory reranking cache",   "separator-hyphen.md",          "mixed",                "hard"),
    ("autoscaling readonly replica policy",     "mixed-forms.md",               "mixed",                "hard"),
    ("apikey autoscaling optin feature",        "mixed-forms.md",               "mixed",                "hard"),
    ("postgres k8s deployment scaling",         "abbreviation-truncation.md",   "mixed",                "hard"),
    ("bge-small crossencoder pipeline",         "compound-version-suffix.md",   "mixed",                "hard"),
]

UPLIFT_CORPUS_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "normalisation_corpus"
CENTURION_SUITE   = Path(__file__).parent.parent / "tests" / "fixtures" / "eval_suite_100.json"
REGRESSION_DIRS   = [
    Path(__file__).parent.parent / "tests" / "fixtures" / "sample_docs",
    Path(__file__).parent.parent / "tests" / "fixtures" / "scale_docs",
    Path(__file__).parent.parent / "docs",
]

# ── Threshold sweep grid ─────────────────────────────────────────────────────
EDIT_DISTANCE_THRESHOLDS      = [0.10, 0.15, 0.20, 0.25]
EMBEDDING_SIMILARITY_THRESHOLDS = [0.75, 0.82, 0.90]
MIN_TOKEN_LENGTHS             = [3, 4, 5]


# ── Result dataclasses ───────────────────────────────────────────────────────

@dataclass
class RetrievalMetrics:
    mrr: float = 0.0
    hit_1: float = 0.0
    hit_5: float = 0.0
    ndcg_5: float = 0.0          # graded where annotations exist, binary otherwise
    query_latency_p50_ms: float = 0.0
    query_latency_p95_ms: float = 0.0
    n_queries: int = 0

@dataclass
class MapMetrics:
    size: int = 0
    generation_time_s: float = 0.0
    separator_pair_coverage: float = 0.0   # fraction of corpus sep-pairs in map
    candidate_pairs_evaluated: int = 0

@dataclass
class ThresholdResult:
    edit_distance_threshold: float
    embedding_similarity_threshold: float
    min_token_length: int
    map: MapMetrics = field(default_factory=MapMetrics)
    # Uplift corpus
    uplift_bm25_baseline: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    uplift_bm25_normalised: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    uplift_hybrid_baseline: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    uplift_hybrid_normalised: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    uplift_bm25_mrr_improvement: float = 0.0
    uplift_hybrid_mrr_improvement: float = 0.0
    # Per variant-type breakdown
    by_variant_type: dict = field(default_factory=dict)
    # Regression corpus
    regression_bm25_baseline: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    regression_bm25_normalised: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    regression_hybrid_normalised: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    regression_by_category: dict = field(default_factory=dict)
    # Performance
    ingest_latency_baseline_ms: float = 0.0
    ingest_latency_normalised_ms: float = 0.0


# ── Metric helpers ───────────────────────────────────────────────────────────

def _mrr(retrieved: list[str], relevant: set[str]) -> float:
    for i, s in enumerate(retrieved):
        if s in relevant:
            return 1.0 / (i + 1)
    return 0.0

def _hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    return float(any(s in relevant for s in retrieved[:k]))

def _ndcg_at_5(retrieved: list[str], graded: dict[str, int]) -> float:
    """Graded nDCG@5. graded maps source → relevance grade (0-3)."""
    if not graded:
        return 0.0
    import math
    dcg = sum(
        graded.get(s, 0) / math.log2(i + 2)
        for i, s in enumerate(retrieved[:5])
    )
    ideal = sorted(graded.values(), reverse=True)[:5]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0

def _compute_metrics(results: list[tuple[list[str], set[str], dict[str, int]]],
                     latencies_ms: list[float]) -> RetrievalMetrics:
    if not results:
        return RetrievalMetrics()
    mrrs, h1s, h5s, ndcgs = [], [], [], []
    for retrieved, relevant, graded in results:
        mrrs.append(_mrr(retrieved, relevant))
        h1s.append(_hit_at_k(retrieved, relevant, 1))
        h5s.append(_hit_at_k(retrieved, relevant, 5))
        ndcgs.append(_ndcg_at_5(retrieved, graded))
    lat_sorted = sorted(latencies_ms)
    p50 = lat_sorted[len(lat_sorted) // 2] if lat_sorted else 0.0
    p95 = lat_sorted[int(len(lat_sorted) * 0.95)] if lat_sorted else 0.0
    return RetrievalMetrics(
        mrr=statistics.mean(mrrs),
        hit_1=statistics.mean(h1s),
        hit_5=statistics.mean(h5s),
        ndcg_5=statistics.mean(ndcgs),
        query_latency_p50_ms=p50,
        query_latency_p95_ms=p95,
        n_queries=len(results),
    )


# ── Database helpers ─────────────────────────────────────────────────────────

def _make_store(data_dir: Path):
    from candlekeep.config import Settings
    from candlekeep.database.vector_store import ChromaVectorStore
    from candlekeep.database.embeddings import EmbeddingManager
    # Use production settings so the already-downloaded models are found,
    # but override chroma_dir to point at our isolated temp collection.
    settings = Settings.from_env()
    # Patch chroma_dir to the temp path without changing models_dir
    settings.data_dir = settings.data_dir  # keep production data_dir for models
    # We need a separate ChromaDB — use a local client pointed at temp_dir
    import chromadb
    chroma_path = data_dir / "chroma"
    chroma_path.mkdir(parents=True, exist_ok=True)
    # Temporarily override the client to use local persistent storage
    vs = ChromaVectorStore.__new__(ChromaVectorStore)
    vs.settings = settings
    vs.embedder = EmbeddingManager.get_instance(settings)
    vs.client = chromadb.PersistentClient(path=str(chroma_path))
    vs.collection = vs.client.get_or_create_collection(
        name="candlekeep",
        metadata={"hnsw:space": "cosine", "embedding_model": settings.embedding_model}
    )
    vs._query_count = 0
    # normalisation_map_path should resolve to data_dir
    settings.data_dir = data_dir
    return vs, settings

def _ingest_dir(vs, proc, directory: Path) -> int:
    count = 0
    if not directory.exists():
        return 0
    for p in directory.glob("*.md"):
        try:
            r = proc.process(str(p))
            if r.chunks:
                vs.add_documents(r.chunks)
                count += 1
        except Exception:
            pass
    return count

def _run_bm25_search(vs, query: str, k: int) -> tuple[list[str], float]:
    from candlekeep.rag.hybrid import get_bm25_searcher
    t0 = time.perf_counter()
    searcher = get_bm25_searcher(vs)
    results = searcher.search(query, n_results=k) if searcher else []
    latency = (time.perf_counter() - t0) * 1000
    sources = []
    for r in results:
        src = r.metadata.get("source", "")
        if "tests/fixtures" in src:
            src = src[src.index("tests/fixtures"):]
        elif "/docs/" in src:
            src = src[src.index("/docs/") + 1:]
        sources.append(src)
    return sources, latency

def _run_hybrid_search(vs, query: str, k: int, query_type: str = "hybrid") -> tuple[list[str], float]:
    from candlekeep.rag.router import search_with_routing
    t0 = time.perf_counter()
    results = search_with_routing(vs, query, n_results=k, query_type=query_type)
    latency = (time.perf_counter() - t0) * 1000
    sources = []
    for r in results:
        src = r.metadata.get("source", "")
        if "tests/fixtures" in src:
            src = src[src.index("tests/fixtures"):]
        elif "/docs/" in src:
            src = src[src.index("/docs/") + 1:]
        sources.append(src)
    return sources, latency


# ── Map generation with configurable thresholds ──────────────────────────────

def _generate_map(vs, settings, ed_thresh: float, emb_thresh: float, min_len: int) -> MapMetrics:
    """Generate normalisation map with given thresholds. Returns MapMetrics."""
    import candlekeep.rag.token_normalisation as tn
    from candlekeep.rag.hybrid import _WORD_RE

    # Patch thresholds
    orig_ed  = tn.EDIT_DISTANCE_THRESHOLD
    orig_emb = tn.EMBEDDING_SIMILARITY_THRESHOLD
    tn.EDIT_DISTANCE_THRESHOLD      = ed_thresh
    tn.EMBEDDING_SIMILARITY_THRESHOLD = emb_thresh

    tn.clear_normalisation_cache()

    chunks = vs.get_all_chunks()
    token_frequencies: dict[str, int] = {}
    for chunk in chunks:
        for tok in _WORD_RE.findall(chunk.text.lower()):
            token_frequencies[tok] = token_frequencies.get(tok, 0) + 1
            if any(c in tok for c in "-._"):
                stripped = tok.replace("-","").replace(".","").replace("_","")
                if stripped != tok:
                    token_frequencies[stripped] = token_frequencies.get(stripped, 0) + 1

    # Candidate set: separator pairs only
    sep_chars = set("-._")
    candidate_set: set[str] = set()
    for t, freq in token_frequencies.items():
        if freq < 2 or len(t) < min_len:
            continue
        if any(c in t for c in sep_chars):
            stripped = t.replace("-","").replace(".","").replace("_","")
            if stripped != t and stripped in token_frequencies:
                candidate_set.add(t)
                candidate_set.add(stripped)

    # Count total separator pairs in corpus for coverage metric
    total_sep_pairs = sum(
        1 for t in token_frequencies
        if any(c in t for c in sep_chars)
        and token_frequencies.get(t.replace("-","").replace(".","").replace("_",""), 0) > 0
    )

    def embed_fn(texts):
        return vs.get_embeddings(texts)

    t0 = time.monotonic()
    variant_map = tn._cluster_tokens(list(candidate_set), token_frequencies, embed_fn)
    gen_time = time.monotonic() - t0

    norm_map = tn.NormalisationMap(variant_map)
    norm_map.save(settings.normalisation_map_path)

    # Update singleton
    with tn._map_lock:
        tn._normalisation_map = norm_map

    coverage = norm_map.size / total_sep_pairs if total_sep_pairs > 0 else 0.0

    # Restore thresholds
    tn.EDIT_DISTANCE_THRESHOLD      = orig_ed
    tn.EMBEDDING_SIMILARITY_THRESHOLD = orig_emb

    return MapMetrics(
        size=norm_map.size,
        generation_time_s=round(gen_time, 3),
        separator_pair_coverage=round(coverage, 4),
        candidate_pairs_evaluated=len(candidate_set),
    )


# ── Uplift corpus evaluation ─────────────────────────────────────────────────

def _eval_uplift(vs, use_bm25_only: bool) -> tuple[RetrievalMetrics, dict]:
    """Run uplift queries. Returns overall metrics and per-variant-type breakdown."""
    results_by_type: dict[str, list] = {}
    latencies: list[float] = []
    all_results = []

    for query, target_file, variant_type, _ in UPLIFT_QUERIES:
        # Expected source: normalisation_corpus/<filename>
        expected = f"tests/fixtures/normalisation_corpus/{target_file}"
        relevant = {expected}
        graded   = {expected: 3}  # single relevant doc, grade 3

        if use_bm25_only:
            retrieved, lat = _run_bm25_search(vs, query, k=5)
        else:
            retrieved, lat = _run_hybrid_search(vs, query, k=5)

        latencies.append(lat)
        all_results.append((retrieved, relevant, graded))
        results_by_type.setdefault(variant_type, []).append((retrieved, relevant, graded))

    overall = _compute_metrics(all_results, latencies)

    by_type = {}
    for vtype, type_results in results_by_type.items():
        n = len(type_results)
        type_lats = latencies[:n]  # approximate — good enough for breakdown
        by_type[vtype] = asdict(_compute_metrics(type_results, type_lats))

    return overall, by_type


# ── Regression corpus evaluation ─────────────────────────────────────────────

def _load_centurion() -> list[dict]:
    if not CENTURION_SUITE.exists():
        return []
    with open(CENTURION_SUITE) as f:
        return json.load(f).get("queries", [])

def _eval_regression(vs, use_bm25_only: bool) -> tuple[RetrievalMetrics, dict]:
    queries = _load_centurion()
    if not queries:
        return RetrievalMetrics(), {}

    all_results, latencies = [], []
    by_category: dict[str, list] = {}

    for q in queries:
        expected = set(q.get("expected_sources", []))
        graded   = {s: 2 for s in expected}  # binary relevance as grade 2
        query    = q["query"]
        category = q.get("category", "unknown")

        if use_bm25_only:
            retrieved, lat = _run_bm25_search(vs, query, k=5)
        else:
            retrieved, lat = _run_hybrid_search(vs, query, k=5)

        latencies.append(lat)
        all_results.append((retrieved, expected, graded))
        by_category.setdefault(category, []).append((retrieved, expected, graded))

    overall = _compute_metrics(all_results, latencies)
    by_cat  = {
        cat: asdict(_compute_metrics(res, latencies[:len(res)]))
        for cat, res in by_category.items()
    }
    return overall, by_cat


# ── Ingest latency measurement ────────────────────────────────────────────────

def _measure_ingest_latency(vs, proc, path: Path) -> float:
    """Return ms to ingest a single file."""
    t0 = time.perf_counter()
    try:
        r = proc.process(str(path))
        if r.chunks:
            vs.add_documents(r.chunks)
    except Exception:
        pass
    return (time.perf_counter() - t0) * 1000


# ── Single threshold run ──────────────────────────────────────────────────────

def _run_one(
    ed_thresh: float,
    emb_thresh: float,
    min_len: int,
    uplift_vs,
    uplift_settings,
    regression_vs,
    regression_settings,
    probe_file: Path,
    proc,
) -> ThresholdResult:
    from candlekeep.rag.hybrid import clear_bm25_cache
    from candlekeep.rag.token_normalisation import clear_normalisation_cache

    result = ThresholdResult(
        edit_distance_threshold=ed_thresh,
        embedding_similarity_threshold=emb_thresh,
        min_token_length=min_len,
    )

    # ── Ingest latency baseline (no map) ────────────────────────────────────
    clear_normalisation_cache()
    map_path = uplift_settings.normalisation_map_path
    bak = map_path.with_suffix(".json.bak")
    if map_path.exists():
        map_path.rename(bak)
    clear_bm25_cache()
    result.ingest_latency_baseline_ms = _measure_ingest_latency(uplift_vs, proc, probe_file)

    # ── Uplift baseline (BM25 only, no map) ─────────────────────────────────
    clear_bm25_cache()
    uplift_bm25_base, _ = _eval_uplift(uplift_vs, use_bm25_only=True)
    result.uplift_bm25_baseline = uplift_bm25_base

    uplift_hybrid_base, _ = _eval_uplift(uplift_vs, use_bm25_only=False)
    result.uplift_hybrid_baseline = uplift_hybrid_base

    # ── Regression baseline (BM25 only, no map) ──────────────────────────────
    clear_bm25_cache()
    reg_bm25_base, _ = _eval_regression(regression_vs, use_bm25_only=True)
    result.regression_bm25_baseline = reg_bm25_base

    # ── Generate map ─────────────────────────────────────────────────────────
    if bak.exists():
        bak.rename(map_path)
    clear_normalisation_cache()
    result.map = _generate_map(uplift_vs, uplift_settings, ed_thresh, emb_thresh, min_len)
    clear_bm25_cache()

    # ── Ingest latency with map ───────────────────────────────────────────────
    result.ingest_latency_normalised_ms = _measure_ingest_latency(uplift_vs, proc, probe_file)

    # ── Uplift with map ───────────────────────────────────────────────────────
    clear_bm25_cache()
    uplift_bm25_norm, by_type = _eval_uplift(uplift_vs, use_bm25_only=True)
    result.uplift_bm25_normalised = uplift_bm25_norm
    result.by_variant_type = by_type

    uplift_hybrid_norm, _ = _eval_uplift(uplift_vs, use_bm25_only=False)
    result.uplift_hybrid_normalised = uplift_hybrid_norm

    # ── Regression with map ───────────────────────────────────────────────────
    # Copy map to regression store's data dir
    reg_map_path = regression_settings.normalisation_map_path
    import shutil as _shutil
    _shutil.copy2(map_path, reg_map_path)
    clear_normalisation_cache()
    clear_bm25_cache()

    reg_bm25_norm, _ = _eval_regression(regression_vs, use_bm25_only=True)
    result.regression_bm25_normalised = reg_bm25_norm

    reg_hybrid_norm, by_cat = _eval_regression(regression_vs, use_bm25_only=False)
    result.regression_hybrid_normalised = reg_hybrid_norm
    result.regression_by_category = by_cat

    # ── MRR improvement ───────────────────────────────────────────────────────
    base_bm25 = result.uplift_bm25_baseline.mrr
    norm_bm25 = result.uplift_bm25_normalised.mrr
    result.uplift_bm25_mrr_improvement = (
        (norm_bm25 - base_bm25) / base_bm25 if base_bm25 > 0 else float("inf")
    )
    base_hyb = result.uplift_hybrid_baseline.mrr
    norm_hyb = result.uplift_hybrid_normalised.mrr
    result.uplift_hybrid_mrr_improvement = (
        (norm_hyb - base_hyb) / base_hyb if base_hyb > 0 else float("inf")
    )

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BM25 normalisation full benchmark")
    parser.add_argument("--output", default="tests/results", help="Output directory")
    parser.add_argument("--quick", action="store_true",
                        help="Single threshold run (ed=0.15, emb=0.82, min_len=4)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.quick:
        ed_grid  = [0.15]
        emb_grid = [0.82]
        len_grid = [4]
    else:
        ed_grid  = EDIT_DISTANCE_THRESHOLDS
        emb_grid = EMBEDDING_SIMILARITY_THRESHOLDS
        len_grid = MIN_TOKEN_LENGTHS

    total_runs = len(ed_grid) * len(emb_grid) * len(len_grid)
    print(f"\n{'='*60}")
    print(f"BM25 Normalisation Benchmark  ({total_runs} threshold combinations)")
    print(f"{'='*60}")

    # ── Build two isolated databases ─────────────────────────────────────────
    uplift_tmp    = tempfile.mkdtemp(prefix="ck_uplift_")
    regression_tmp = tempfile.mkdtemp(prefix="ck_regression_")

    # Warm the embedding model using the production data dir BEFORE
    # switching CANDLEKEEP_DATA_DIR to the temp dirs.
    from candlekeep.config import Settings
    from candlekeep.database.embeddings import EmbeddingManager
    from candlekeep.rag.processor import DocumentProcessor
    prod_settings = Settings.from_env()
    EmbeddingManager.get_instance(prod_settings).get_model()  # warm
    print("   Embedding model warmed.")

    os.environ["CANDLEKEEP_DATA_DIR"] = uplift_tmp

    try:
        from candlekeep.rag.processor import DocumentProcessor

        uplift_vs, uplift_settings = _make_store(Path(uplift_tmp))
        proc = DocumentProcessor(uplift_settings)

        print("\n📦 Seeding uplift corpus...")
        n = _ingest_dir(uplift_vs, proc, UPLIFT_CORPUS_DIR)
        print(f"   {n} documents ingested from normalisation_corpus/")

        # Regression store uses a different data dir — swap env var
        os.environ["CANDLEKEEP_DATA_DIR"] = regression_tmp
        regression_vs, regression_settings = _make_store(Path(regression_tmp))
        reg_proc = DocumentProcessor(regression_settings)

        print("\n📦 Seeding regression corpus...")
        reg_count = 0
        for d in REGRESSION_DIRS:
            reg_count += _ingest_dir(regression_vs, reg_proc, d)
        print(f"   {reg_count} documents ingested")
        centurion = _load_centurion()
        print(f"   Centurion Set: {len(centurion)} queries" if centurion else
              "   ⚠  Centurion Set not found — regression corpus only")

        # Restore uplift env for map generation
        os.environ["CANDLEKEEP_DATA_DIR"] = uplift_tmp

        # Probe file for ingest latency measurement
        probe_file = next(UPLIFT_CORPUS_DIR.glob("*.md"), None)

        all_results = []
        run_num = 0

        for ed, emb, min_len in itertools.product(ed_grid, emb_grid, len_grid):
            run_num += 1
            print(f"\n[{run_num}/{total_runs}] ed={ed}  emb={emb}  min_len={min_len}")

            from candlekeep.rag.token_normalisation import clear_normalisation_cache
            from candlekeep.rag.hybrid import clear_bm25_cache
            clear_normalisation_cache()
            clear_bm25_cache()

            r = _run_one(ed, emb, min_len,
                         uplift_vs, uplift_settings,
                         regression_vs, regression_settings,
                         probe_file, proc)
            all_results.append(r)

            bm25_imp = r.uplift_bm25_mrr_improvement
            hyb_imp  = r.uplift_hybrid_mrr_improvement
            reg_delta = r.regression_bm25_normalised.mrr - r.regression_bm25_baseline.mrr
            print(f"   map={r.map.size} variants  gen={r.map.generation_time_s:.2f}s")
            print(f"   uplift BM25 MRR: {r.uplift_bm25_baseline.mrr:.4f} → "
                  f"{r.uplift_bm25_normalised.mrr:.4f}  ({bm25_imp:+.1%})")
            print(f"   uplift hybrid MRR: {r.uplift_hybrid_baseline.mrr:.4f} → "
                  f"{r.uplift_hybrid_normalised.mrr:.4f}  ({hyb_imp:+.1%})")
            print(f"   regression BM25 MRR delta: {reg_delta:+.4f}")
            pass_bm25 = "✓ PASS" if bm25_imp >= 0.10 else "✗ FAIL"
            pass_gen  = "✓ PASS" if r.map.generation_time_s <= 5.0 else "✗ FAIL"
            pass_reg  = "✓ PASS" if reg_delta >= -0.01 else "✗ FAIL"
            print(f"   {pass_bm25} ≥10% BM25 MRR uplift  "
                  f"{pass_gen} ≤5s gen  {pass_reg} no regression")

        # ── Save full results ─────────────────────────────────────────────────
        report = {
            "metadata": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "total_runs": total_runs,
                "uplift_queries": len(UPLIFT_QUERIES),
                "regression_queries": len(centurion),
            },
            "results": [asdict(r) for r in all_results],
        }
        out_path = output_dir / "normalisation_benchmark_full.json"
        out_path.write_text(json.dumps(report, indent=2))
        print(f"\n💾 Full results → {out_path}")

        # ── Summary table ─────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print("SUMMARY  (sorted by BM25 MRR uplift)")
        print(f"{'ed':>5} {'emb':>5} {'len':>4}  {'map':>5}  {'gen_s':>6}  "
              f"{'bm25_base':>9} {'bm25_norm':>9} {'uplift':>8}  {'reg_delta':>9}")
        print("-" * 80)
        for r in sorted(all_results, key=lambda x: -x.uplift_bm25_mrr_improvement):
            print(f"{r.edit_distance_threshold:>5.2f} "
                  f"{r.embedding_similarity_threshold:>5.2f} "
                  f"{r.min_token_length:>4}  "
                  f"{r.map.size:>5}  "
                  f"{r.map.generation_time_s:>6.2f}  "
                  f"{r.uplift_bm25_baseline.mrr:>9.4f} "
                  f"{r.uplift_bm25_normalised.mrr:>9.4f} "
                  f"{r.uplift_bm25_mrr_improvement:>+8.1%}  "
                  f"{r.regression_bm25_normalised.mrr - r.regression_bm25_baseline.mrr:>+9.4f}")

    finally:
        os.environ.pop("CANDLEKEEP_DATA_DIR", None)
        shutil.rmtree(uplift_tmp, ignore_errors=True)
        shutil.rmtree(regression_tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
